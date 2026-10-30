#!/usr/bin/env bash
# Install the safe deploy logic into the existing service and timer, never create duplicates.
set -Eeuo pipefail
[[ "$(id -u)" -eq 0 ]] || { echo "Run via sudo bash scripts/install-safe-autodeploy.sh";exit 1; }
ROOT=/home/tv/cardshop
SERVICE=cardyssey-deploy.service
TIMER=cardyssey-deploy.timer
systemctl cat "$SERVICE" >/dev/null
systemctl cat "$TIMER" >/dev/null
systemctl stop "$TIMER"
# Wait for any currently-running old deployment to finish/stop.
systemctl stop "$SERVICE" || true
install -d -m 755 /etc/systemd/system/"$SERVICE".d
cat > /etc/systemd/system/"$SERVICE".d/50-safe-release.conf <<'EOF'
[Service]
Type=oneshot
User=root
Group=root
WorkingDirectory=/home/tv/cardshop
ExecStart=
ExecStart=/usr/bin/bash /home/tv/cardshop/scripts/cardyssey-deploy-safe.sh
TimeoutStartSec=0
EOF
systemctl daemon-reload
echo "Safe deployment installed. Existing timer not yet enabled."
echo "Manual smoke test: sudo systemctl start cardyssey-deploy.service"
echo "Only after success: sudo systemctl enable --now cardyssey-deploy.timer"
