#!/usr/bin/env bash
# Cardyssey web deployments without administrator privileges.
# Uses only directories owned by tv and restarts the already tv-owned
# systemd service by terminating its main process (Restart=always).
# The systemd unit, permissions, and other services remain untouched.
set -Eeuo pipefail

ROOT=/home/tv/cardshop
UNIT=cardyssey-web.service
RELEASES="$ROOT/releases"
STATE_DIR="$ROOT/.deploy-state"
LOCK="$STATE_DIR/web.lock"
PORT=31273
mkdir -p "$STATE_DIR"
exec 9>"$LOCK"
flock -n 9 || { echo "Another Cardyssey deployment is running"; exit 75; }

say() { printf '[Cardyssey deploy] %s\n' "$*"; }
fail() { say "ERROR: $*" >&2; exit 1; }

[[ "$(id -un)" == tv ]] || fail "Run as user tv"
command -v systemctl >/dev/null || fail "systemctl unavailable"
command -v git >/dev/null || fail "git unavailable"
command -v npm >/dev/null || fail "npm unavailable"

FIXED="$(systemctl show "$UNIT" -p WorkingDirectory --value)"
[[ "$FIXED" == "$RELEASES/"*"/web" ]] || fail "Unexpected systemd WorkingDirectory: $FIXED"
[[ "$(systemctl show "$UNIT" -p User --value)" == tv ]] || fail "Service is not owned by tv"
[[ "$(systemctl show "$UNIT" -p Restart --value)" == always ]] || fail "Service is not configured to restart automatically"
[[ "$(systemctl show "$UNIT" -p ActiveState --value)" == active ]] || fail "Web service is not active"
[[ "$FIXED" == "$RELEASES/web-"*"/web" ]] || fail "Unexpected web release path"
[[ -d "$(dirname "$FIXED")" ]] || fail "Current release parent is missing"
[[ "$(stat -c %U "$(dirname "$FIXED")")" == tv ]] || fail "Release directory is not owned by tv"

validate_target() {
  local target="$1" physical
  physical="$(realpath -e "$target" 2>/dev/null)" || return 1
  [[ "$physical" == "$RELEASES/"* ]] || return 1
  [[ -f "$physical/package.json" && -s "$physical/.next/BUILD_ID" ]] || return 1
  [[ -d "$physical/node_modules" ]] || return 1
}

current_target() {
  if [[ -L "$FIXED" ]]; then
    readlink -f "$FIXED"
  else
    realpath -e "$FIXED"
  fi
}

check_http() {
  curl -fsS --max-time 3 http://127.0.0.1:3000/login >/dev/null 2>&1
}

switch_target() {
  local target="$1" temp="$FIXED.switch-$$"
  validate_target "$target" || fail "Invalid release target $target"
  [[ -L "$FIXED" ]] || fail "Safe release pointer is not set up"
  ln -s "$target" "$temp"
  mv -Tf "$temp" "$FIXED"
}

service_pid() {
  systemctl show "$UNIT" -p MainPID --value
}

restart_tv_service() {
  local pid owner
  pid="$(service_pid)"
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || fail "Invalid service process ID"
  owner="$(ps -o user= -p "$pid" | tr -d ' ')"
  [[ "$owner" == tv ]] || fail "Not allowed to restart a process owned by $owner"
  # This is the service's user-owned main process, not systemctl or sudo.
  kill -TERM "$pid"
}

wait_for_target() {
  local target="$1" oldpid="$2" i pid actual
  for ((i=0; i<65; i++)); do
    pid="$(service_pid)"
    if [[ "$pid" =~ ^[1-9][0-9]*$ && "$pid" != "$oldpid" ]]; then
      actual="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
      if [[ "$actual" == "$target" ]] && check_http; then
        say "Service healthy on PID $pid; release $actual"
        return 0
      fi
    fi
    sleep 1
  done
  return 1
}

activate() {
  local target="$1" previous="$2" oldpid
  oldpid="$(service_pid)"
  switch_target "$target"
  restart_tv_service
  if wait_for_target "$target" "$oldpid"; then
    printf '%s\n' "$previous" > "$STATE_DIR/previous-web-target"
    printf '%s\n' "$target" > "$STATE_DIR/current-web-target"
    say "ACTIVE: $target"
    return 0
  fi

  say "Health check failed. Rolling back to $previous"
  switch_target "$previous"
  oldpid="$(service_pid)"
  if [[ "$oldpid" =~ ^[1-9][0-9]*$ ]]; then
    restart_tv_service
    wait_for_target "$previous" "$oldpid" || fail "Automatic rollback failed; manual recovery required"
  else
    fail "Automatic rollback could not locate the service process"
  fi
  fail "New release failed its health check; previous version restored"
}

setup() {
  if [[ -L "$FIXED" ]]; then
    validate_target "$(current_target)" || fail "Configured release link points to invalid directory"
    say "Safe release pointer already installed"
    return
  fi
  [[ -d "$FIXED" && ! -L "$FIXED" ]] || fail "Release directory is not a regular directory"
  validate_target "$FIXED" || fail "Existing deployment fails validation"
  local backup="$FIXED.seed-$(date +%Y%m%d-%H%M%S)" temp="$FIXED.setup-$$" oldpid
  oldpid="$(service_pid)"
  mv "$FIXED" "$backup"
  if ! ln -s "$backup" "$temp"; then
    mv "$backup" "$FIXED"
    fail "Could not create release link; original directory restored"
  fi
  mv -Tf "$temp" "$FIXED"
  say "Release pointer initialized, keeping original files in $backup"
  if ! check_http; then
    fail "Service is not responding; investigate before restart"
  fi
  restart_tv_service
  if ! wait_for_target "$backup" "$oldpid"; then
    fail "Initial restart failed. Original files remain at $backup"
  fi
  printf '%s\n' "$backup" > "$STATE_DIR/current-web-target"
  say "READY: future Cardyssey deployments need no sudo"
}

staging_smoke() {
  local target="$1" logfile="$2" pid ready=0 i
  (
    cd "$target"
    exec ./node_modules/.bin/next start -H 127.0.0.1 -p "$PORT"
  ) > "$logfile" 2>&1 &
  pid=$!
  for ((i=0;i<35;i++)); do
    if curl -fsS --max-time 2 "http://127.0.0.1:$PORT/login" >/dev/null 2>&1; then
      ready=1
      break
    fi
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 1
  done
  kill -TERM "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  [[ "$ready" == 1 ]] || fail "Staging smoke test failed; see $logfile"
  say "Staging smoke test passed on local port $PORT"
}

deploy() {
  [[ -L "$FIXED" ]] || fail "Run setup once before deploying"
  local previous candidate stamp rev target
  previous="$(current_target)"
  validate_target "$previous" || fail "Current live release is invalid"
  cd "$ROOT"
  rev="$(git rev-parse --short=10 HEAD)"
  stamp="$(date +%Y%m%d-%H%M%S)"
  candidate="$RELEASES/web-$stamp-$rev"
  git worktree add --detach "$candidate" HEAD
  for path in web/.env.production web/.env.local web/.env; do
    if [[ -f "$ROOT/$path" ]]; then cp -p "$ROOT/$path" "$candidate/$path"; fi
  done
  if [[ -f "$ROOT/web/private-downloads/cardyssey-version.json" && -f "$ROOT/web/private-downloads/cardyssey-latest.apk" ]]; then
    mkdir -p "$candidate/web/private-downloads"
    cp -p "$ROOT/web/private-downloads/cardyssey-version.json" "$candidate/web/private-downloads/"
    cp -p "$ROOT/web/private-downloads/cardyssey-latest.apk" "$candidate/web/private-downloads/"
  fi
  say "Installing and building $candidate"
  ( cd "$candidate/web" && npm ci --no-audit --no-fund && npm run build )
  target="$candidate/web"
  validate_target "$target" || fail "Build artifacts not complete"
  staging_smoke "$target" "$STATE_DIR/staging-$stamp.log"
  activate "$target" "$previous"
}

rollback() {
  [[ -L "$FIXED" ]] || fail "Safe release pointer is not installed"
  [[ -s "$STATE_DIR/previous-web-target" ]] || fail "No previous release available"
  local target previous
  target="$(cat "$STATE_DIR/previous-web-target")"
  previous="$(current_target)"
  activate "$target" "$previous"
}

status() {
  say "Service: $(systemctl is-active "$UNIT")"
  say "Fixed path: $FIXED"
  say "Current target: $(current_target)"
  say "Pointer configured: $(test -L "$FIXED" && echo yes || echo no)"
  say "HTTP /login: $(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:3000/login || true)"
  say "Main PID: $(service_pid)"
}

case "${1:-status}" in
  setup) setup ;;
  deploy) deploy ;;
  rollback) rollback ;;
  status) status ;;
  *) echo "Usage: $0 {status|setup|deploy|rollback}" >&2; exit 2 ;;
esac
