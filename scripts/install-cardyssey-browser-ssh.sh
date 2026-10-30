#!/usr/bin/env bash
# Install a Cloudflare Tunnel connector for private browser SSH.
# NO public firewall changes. Requires existing Zero Trust Access policy and
# a named tunnel token from Cloudflare, supplied via root-only env file.
set -Eeuo pipefail
if [[ ${EUID} -ne 0 ]]; then echo "Run with sudo" >&2; exit 1; fi
if ! command -v systemctl >/dev/null; then echo "systemd required" >&2; exit 1; fi
if ! command -v sshd >/dev/null; then echo "Install openssh-server first" >&2; exit 1; fi
if ! systemctl is-active --quiet ssh && ! systemctl is-active --quiet sshd; then echo "SSH service is not running" >&2; exit 1; fi
if [[ ! -f /etc/cardyssey/cloudflared.env ]]; then
  install -d -m 0700 /etc/cardyssey
  printf '# Set CLOUDFLARE_TUNNEL_TOKEN=<token from Zero Trust>\n' > /etc/cardyssey/cloudflared.env
  chmod 600 /etc/cardyssey/cloudflared.env
  echo "Created /etc/cardyssey/cloudflared.env. Add token securely and rerun." >&2
  exit 2
fi
if ! grep -Eq '^CLOUDFLARE_TUNNEL_TOKEN=[^[:space:]]+' /etc/cardyssey/cloudflared.env; then
  echo "Set CLOUDFLARE_TUNNEL_TOKEN in /etc/cardyssey/cloudflared.env" >&2
  exit 2
fi
if ! command -v cloudflared >/dev/null; then
  echo "Install cloudflared from Cloudflare's signed package instructions first:" >&2
  echo "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" >&2
  exit 2
fi
cat > /etc/systemd/system/cardyssey-cloudflared.service <<'EOF'
[Unit]
Description=Cloudflare Tunnel for private Cardyssey browser SSH
Wants=network-online.target
After=network-online.target ssh.service
[Service]
Type=simple
EnvironmentFile=/etc/cardyssey/cloudflared.env
ExecStart=/usr/bin/env cloudflared tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now cardyssey-cloudflared.service
systemctl status cardyssey-cloudflared.service --no-pager
echo "Connector installed. Verify Cloudflare Access deny-by-default policy, browser SSH auth and recovery."
