#!/usr/bin/env bash
# Root-owned systemd entry point; reuses the EXISTING cardyssey-deploy.timer.
# Performs updates in isolated worktrees and keeps the live Next build intact.
set -Eeuo pipefail
ROOT=/home/tv/cardshop
SERVICE=cardyssey-web.service
OVERRIDE=/etc/systemd/system/cardyssey-web.service.d/20-release.conf
LOCK=/run/lock/cardyssey-deploy-safe.lock
exec 9>"$LOCK"
flock -n 9 || { echo "Deployment already active; skipping."; exit 0; }
[[ "$(id -u)" -eq 0 ]] || { echo "Run as root from systemd."; exit 1; }
run_tv(){ runuser -u tv -- "$@"; }
cd "$ROOT"
echo "== Checking current repository =="
run_tv git fetch --quiet origin main
local_rev="$(run_tv git rev-parse HEAD)"
remote_rev="$(run_tv git rev-parse origin/main)"
if [[ "$local_rev" != "$remote_rev" ]]; then
  run_tv git pull --ff-only origin main
fi
target="$(run_tv git rev-parse HEAD)"
active="$(systemctl show -p WorkingDirectory --value "$SERVICE")"
if [[ -z "$active" || ! -d "$active" ]]; then
  echo "Previous working directory not found; refusing deployment." >&2; exit 1
fi
# Bound disk use: only retain the live release and the two newest
# successful/rollback candidates. Remove via git worktree first to keep
# Git metadata consistent. Never remove current live WorkingDirectory.
prune_old_releases() {
  local live_root candidate keep=0
  live_root="$(systemctl show -p WorkingDirectory --value "$SERVICE")"
  live_root="${live_root%/web}"
  local -a candidates=()
  mapfile -t candidates < <(find "$ROOT/releases" -mindepth 1 -maxdepth 1 -type d -name 'web-*' -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-)
  local dir
  for dir in "${candidates[@]}"; do
    [[ "$dir" == "$live_root" ]] && continue
    if (( keep < 2 )); then
      keep=$((keep + 1))
      continue
    fi
    [[ "$dir" == "$ROOT/releases"/web-* ]] || continue
    # Do not follow symbolic links or delete unrelated directories.
    [[ ! -L "$dir" ]] || continue
    run_tv git -C "$ROOT" worktree remove --force "$dir" || {
      echo "Unable to remove old worktree $dir safely" >&2
    }
  done
  run_tv git -C "$ROOT" worktree prune || :
}
prune_old_releases
# A WSL ext4 disk can have abundant free space while the Windows host is
# completely full. Abort before npm creates another large release.
if [[ -d /mnt/c ]]; then
  host_free_kb="$(df -Pk /mnt/c | awk 'NR==2 {print $4}')"
  if [[ "$host_free_kb" =~ ^[0-9]+$ ]] && (( host_free_kb < 5242880 )); then
    echo "Windows C: has less than 5 GiB free; skipping deployment safely." >&2
    exit 0
  fi
fi
# Prevent a broken commit from generating another ~800 MB worktree every
# minute. A new commit can be attempted immediately; failed ones wait 6h.
failure_marker=/home/tv/.config/cardyssey/web-deploy-failure
if [[ -r "$failure_marker" ]]; then
  read -r failed_target failed_at < "$failure_marker" || :
  if [[ "${failed_target:-}" == "$target" ]] && [[ "${failed_at:-}" =~ ^[0-9]+$ ]] &&
     (( $(date +%s) - failed_at < 21600 )); then
    echo "Skipping failed commit within six-hour cooldown: $target"
    exit 0
  fi
fi
record_failure() {
  install -d -m 755 /home/tv/.config/cardyssey
  printf '%s %s\n' "$target" "$(date +%s)" > "$failure_marker"
  chown tv:tv "$failure_marker"
  if [[ -n "${release:-}" && -d "$release" ]]; then
    run_tv git -C "$ROOT" worktree remove --force "$release" || :
  fi
}
trap record_failure ERR
# A release marker prevents rebuilding the same commit on every timer tick.
marker=/home/tv/.config/cardyssey/web-deployed-commit
if [[ -r "$marker" && "$(cat "$marker")" == "$target" ]] && systemctl is-active --quiet "$SERVICE"; then
  echo "Already deployed: $target"; exit 0
fi
mkdir -p "$ROOT/releases"
chown tv:tv "$ROOT/releases"
stamp="$(date +%Y%m%d-%H%M%S)"
release="$ROOT/releases/web-$stamp-${target:0:9}"
echo "== Creating isolated worktree: $release =="
run_tv git worktree add --detach "$release" "$target"
for file in web/.env.production web/.env.local web/.env; do
  [[ ! -f "$ROOT/$file" ]] || run_tv cp -p "$ROOT/$file" "$release/$file"
done
# Turbopack requires dependencies inside the release project root.
# Generated OpenAPI TS model files may be untracked in Git; the live build has them.
# Preserve repository files and fill only missing generated files from the working tree.
if [[ -d "$ROOT/web/lib/generated/cardyssey" ]]; then
  install -d -o tv -g tv "$release/web/lib/generated/cardyssey"
  run_tv cp -a -n "$ROOT/web/lib/generated/cardyssey/." "$release/web/lib/generated/cardyssey/"
else
  echo "Missing generated Cardyssey API client in working tree" >&2
  exit 1
fi
run_tv bash -c 'cd "$1/web" && npm ci --no-audit --no-fund' _ "$release"
echo "== Building candidate without touching the running .next =="
run_tv bash -c 'cd "$1/web" && npm run build' _ "$release"
[[ -s "$release/web/.next/BUILD_ID" ]] || { echo "Missing BUILD_ID; refusing cutover."; exit 1; }

had_override=0
saved="$(mktemp)"
if [[ -f "$OVERRIDE" ]]; then cp "$OVERRIDE" "$saved";had_override=1;fi
rollback(){
 echo "== Restoring previous release =="
 if [[ "$had_override" == 1 ]]; then cp "$saved" "$OVERRIDE";else rm -f "$OVERRIDE";fi
 systemctl daemon-reload
 systemctl restart "$SERVICE"
 rm -f "$saved"
}
install -d -m 755 "$(dirname "$OVERRIDE")"
printf '[Service]\nWorkingDirectory=%s/web\n' "$release" > "$OVERRIDE"
systemctl daemon-reload
echo "== Switching service =="
if ! systemctl restart "$SERVICE"; then rollback;record_failure;exit 1;fi
healthy=0
for attempt in {1..25}; do
  if curl -fsS -m 3 http://127.0.0.1:3000/login >/dev/null 2>&1; then healthy=1;break;fi
  sleep 2
done
if [[ "$healthy" != 1 ]] || ! systemctl is-active --quiet "$SERVICE";then rollback;record_failure;exit 1;fi
install -d -m 755 /home/tv/.config/cardyssey
printf '%s\n' "$target" > "$marker"
chown tv:tv "$marker"
rm -f "$saved"
rm -f "$failure_marker"
trap - ERR
prune_old_releases
echo "== Deployed ${target:0:12}; old release preserved: $active =="
