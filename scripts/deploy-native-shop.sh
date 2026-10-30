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
echo "== Health checks =="
sudo systemctl is-active cardyssey-web.service
curl -fsS -m 15 http://127.0.0.1:3000/login >/dev/null
curl -sS -m 15 -o /dev/null -w 'Shop auth status: %{http_code}\n' http://127.0.0.1:3000/api/admin/shop/native
echo "DONE. Shop DB online. Native admin requires existing admin session; no checkout enabled."
