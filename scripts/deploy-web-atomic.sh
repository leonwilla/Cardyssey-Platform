#!/usr/bin/env bash
# Cardyssey web deployment client: no sudo, no system-service changes.
# The installed root-owned cardyssey-deploy.timer handles immutable
# builds, smoke checks, systemd cutover, and rollback.
set -Eeuo pipefail
ROOT=/home/tv/cardshop
UNIT=cardyssey-web.service
TIMER=cardyssey-deploy.timer
MARKER=/home/tv/.config/cardyssey/web-deployed-commit
FAILURE=/home/tv/.config/cardyssey/web-deploy-failure
cd "$ROOT"

say(){ printf '[Cardyssey] %s\n' "$*"; }
fail(){ say "ERROR: $*" >&2; exit 1; }
[[ "$(id -un)" == tv ]] || fail "Expected user tv"
systemctl is-active --quiet "$TIMER" || fail "Existing automatic deploy timer is not running"

status(){
  say "Automatic deploy timer: active"
  say "Web service: $(systemctl is-active "$UNIT")"
  say "Source commit: $(git rev-parse --short=12 HEAD)"
  say "Deployed commit: $(head -c 12 "$MARKER" 2>/dev/null || echo unknown)"
  say "Current release: $(systemctl show "$UNIT" -p WorkingDirectory --value)"
  say "Login health: $(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:3000/login || true)"
}

deploy(){
  [[ "$(git branch --show-current)" == main ]] || fail "Only main may be deployed"
  if ! git diff --quiet HEAD -- web; then
    fail "Uncommitted web changes detected. Commit and verify first."
  fi
  local target deployed waited failure_rev failure_at
  target="$(git rev-parse HEAD)"
  git push origin main
  say "Published commit ${target:0:12}. The existing automatic deployment timer owns the rollout."
  waited=0
  while (( waited < 360 )); do
    deployed="$(cat "$MARKER" 2>/dev/null || true)"
    if [[ "$deployed" == "$target" ]] &&
       systemctl is-active --quiet "$UNIT" &&
       curl -fsS --max-time 5 http://127.0.0.1:3000/login >/dev/null 2>&1; then
      say "DEPLOYED: ${target:0:12} (HTTP 200)"
      status
      return 0
    fi
    if [[ -r "$FAILURE" ]]; then
      read -r failure_rev failure_at < "$FAILURE" || true
      if [[ "$failure_rev" == "$target" ]]; then
        fail "Automatic deployment failed for ${target:0:12}; previous web release is preserved."
      fi
    fi
    sleep 3
    waited=$((waited+3))
  done
  fail "Deployment not confirmed within monitoring window. Check systemd cardyssey-deploy.service"
}

case "${1:-deploy}" in
  status) status ;;
  deploy) deploy ;;
  *) echo "Usage: $0 {status|deploy}" >&2; exit 2 ;;
esac
