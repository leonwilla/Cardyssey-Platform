#!/usr/bin/env bash
# Read-only diagnostics. Does not expose credentials or change firewall.
set -uo pipefail
echo "=== System ==="; id -un; uname -sr
echo "=== SSH installed ==="; command -v sshd || true
echo "=== SSH service ==="; systemctl is-active ssh 2>/dev/null || systemctl is-active sshd 2>/dev/null || true
echo "=== Listening SSH sockets ==="; ss -lnt | grep -E ':(22|2222)[[:space:]]' || true
echo "=== Tunnel binary ==="; command -v cloudflared || true
echo "=== Tunnel service ==="; systemctl is-active cardyssey-cloudflared 2>/dev/null || true
echo "=== Systemd WSL status ==="; ps -p 1 -o comm= || true
echo "=== Tailscale (fallback) ==="; command -v tailscale || true
echo "=== Secrets present? (contents hidden) ==="
if sudo -n test -s /etc/cardyssey/cloudflared.env 2>/dev/null; then echo "token file exists"; else echo "token file absent or sudo unavailable"; fi
echo "=== Firewall ==="; command -v ufw >/dev/null && sudo -n ufw status 2>/dev/null || true
echo "No changes performed."
