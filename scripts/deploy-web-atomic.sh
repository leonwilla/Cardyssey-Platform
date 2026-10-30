#!/usr/bin/env bash
# Build a separate immutable release, then switch systemd WorkingDirectory.
# Does not modify the live .next; restores the previous service directory on failure.
set -Eeuo pipefail
ROOT=/home/tv/cardshop
WEB_SERVICE=cardyssey-web.service
DROPIN=/etc/systemd/system/cardyssey-web.service.d/20-release.conf
LOCK=/home/tv/.cache/cardyssey-web-deploy.lock
mkdir -p /home/tv/.cache
exec 9>"$LOCK"
flock -n 9 || { echo "Another web deployment is running."; exit 75; }
cd "$ROOT"
[[ "$(id -un)" == tv ]] || { echo "Run as tv"; exit 1; }
command -v npm >/dev/null
command -v git >/dev/null
command -v flock >/dev/null
[[ -d web/node_modules ]] || { echo "Missing web/node_modules"; exit 1; }

# The application must stay running while the candidate is built.
previous_dir="$(systemctl show -p WorkingDirectory --value "$WEB_SERVICE")"
[[ -n "$previous_dir" && -d "$previous_dir" ]] || { echo "Cannot detect previous working directory"; exit 1; }
previous_override="$(mktemp)"
had_override=0
if sudo test -f "$DROPIN"; then
  sudo cat "$DROPIN" > "$previous_override"
  had_override=1
fi
stamp="$(date +%Y%m%d-%H%M%S)"
release="$ROOT/releases/web-$stamp-$(git rev-parse --short HEAD)"
mkdir -p "$ROOT/releases"
git worktree add --detach "$release" HEAD
for file in web/.env.production web/.env.local web/.env; do
  if [[ -f "$ROOT/$file" ]]; then
    cp -p "$ROOT/$file" "$release/$file"
  fi
done
ln -s "$ROOT/web/node_modules" "$release/web/node_modules"
echo "== Building release $(basename "$release") while the old web service keeps running =="
(cd "$release/web" && npm run build)
test -s "$release/web/.next/BUILD_ID" || { echo "Release has no BUILD_ID"; exit 1; }
echo "== Switching systemd to the verified build =="
sudo install -d -m 755 "$(dirname "$DROPIN")"
printf '[Service]\nWorkingDirectory=%s/web\n' "$release" | sudo tee "$DROPIN" >/dev/null
sudo systemctl daemon-reload
sudo systemctl restart "$WEB_SERVICE"
ready=0
for n in {1..25}; do
  if curl -fsS -m 3 http://127.0.0.1:3000/login >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "New release failed health check, restoring previous web service." >&2
  if [[ "$had_override" == 1 ]]; then
    sudo cp "$previous_override" "$DROPIN"
  else
    sudo rm -f "$DROPIN"
  fi
  sudo systemctl daemon-reload
  sudo systemctl restart "$WEB_SERVICE"
  rm -f "$previous_override"
  exit 1
fi
rm -f "$previous_override"
echo "== Web release active: $release =="
echo "Previous release retained at: $previous_dir"
echo "Automated deployment timer was not enabled or changed."
