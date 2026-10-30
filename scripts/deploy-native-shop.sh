#!/usr/bin/env bash
# One-shot native Cardyssey shop installation. Stops on any failure.
# Only host-local DB access; no WordPress deletion or payment activation.
set -Eeuo pipefail
cd /home/tv/cardshop
test "$(id -un)" = tv || { echo "Run as tv (not root)"; exit 1; }
test -r platform/.env || { echo "Missing platform/.env"; exit 1; }
command -v docker >/dev/null
command -v psql >/dev/null || { echo "Install PostgreSQL client: sudo apt-get update && sudo apt-get install -y postgresql-client"; exit 1; }
echo "== Backing up Cardyssey DB =="
mkdir -p backups/native-shop
chmod 700 backups/native-shop
backup="backups/native-shop/cardyssey-before-shop-$(date +%Y%m%d-%H%M%S).dump"
docker exec cardyssey-db pg_dump -U cardyssey -d cardyssey -Fc > "$backup"
test -s "$backup" || { echo "Backup empty"; exit 1; }
chmod 600 "$backup"
echo "DB backup saved: $backup"
echo "== Applying native shop SQL schema =="
docker exec -i cardyssey-db psql -X -v ON_ERROR_STOP=1 -U cardyssey -d cardyssey < scripts/native-shop-schema.sql
echo "== Opening local-only PostgreSQL port =="
(cd platform && docker compose --env-file .env up -d --no-deps db)
echo "== Setting up application DB URL (secret will not be printed) =="
install -d -m 700 "$HOME/.config/cardyssey"
python3 - <<'PY'
import os, pathlib, urllib.parse
root=pathlib.Path.home()/'cardshop'
conf={}
for line in (root/'platform/.env').read_text().splitlines():
 if line.strip().startswith('#') or '=' not in line: continue
 k,v=line.split('=',1);conf[k.strip()]=v.strip().strip('"').strip("'")
 user=conf.get('POSTGRES_USER','cardyssey');pwd=conf.get('POSTGRES_PASSWORD','')
 db=conf.get('POSTGRES_DB','cardyssey')
if not pwd:raise SystemExit("POSTGRES_PASSWORD missing")
url='postgresql://'+urllib.parse.quote(user,safe='')+':'+urllib.parse.quote(pwd,safe='')+'@127.0.0.1:5433/'+urllib.parse.quote(db,safe='')
f=pathlib.Path.home()/'.config/cardyssey/native-shop.env'
# systemd EnvironmentFile quoting handles special characters in credential values.
import shlex
f.write_text('CARDYSSEY_SHOP_DATABASE_URL='+shlex.quote(url)+'\nCARDYSSEY_NATIVE_SHOP_DB_ENABLED=true\n')
os.chmod(f,0o600)
PY
echo "== Configuring existing systemd web service =="
sudo install -d -m 755 /etc/systemd/system/cardyssey-web.service.d
printf '[Service]\nEnvironmentFile=/home/tv/.config/cardyssey/native-shop.env\n' | sudo tee /etc/systemd/system/cardyssey-web.service.d/native-shop.conf >/dev/null
sudo systemctl daemon-reload
sudo systemctl restart cardyssey-web.service
echo "== Health checks (bounded startup wait) =="
ready=0
for attempt in {1..15}; do
  if curl -fsS -m 3 http://127.0.0.1:3000/login >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "Cardyssey web did not become ready; showing service diagnostics." >&2
  sudo systemctl status cardyssey-web.service --no-pager -l >&2 || true
  sudo journalctl -u cardyssey-web.service -n 60 --no-pager >&2 || true
  exit 1
fi
sudo systemctl is-active cardyssey-web.service
echo "== PostgreSQL loopback =="
pg_isready -h 127.0.0.1 -p 5433 || true
echo "== Native shop auth protection =="
curl -sS -m 15 -o /dev/null -w 'Unauthenticated admin HTTP: %{http_code}\\n' http://127.0.0.1:3000/api/admin/shop/native
echo "DONE. No WordPress services or volumes changed."
