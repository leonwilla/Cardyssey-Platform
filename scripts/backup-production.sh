#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${CARDYSSEY_ROOT_DIR:-/home/tv/cardshop}"
PLATFORM_DIR="${CARDYSSEY_PLATFORM_DIR:-$ROOT_DIR/platform}"
BACKUP_DIR="${CARDYSSEY_BACKUP_DIR:-/home/tv/cardyssey-backups}"
RETENTION_DAYS="${CARDYSSEY_BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$BACKUP_DIR/$TIMESTAMP"

mkdir -p "$RUN_DIR"

if [[ ! -d "$PLATFORM_DIR" ]]; then
  echo "ERROR: platform directory not found: $PLATFORM_DIR" >&2
  exit 1
fi

cd "$PLATFORM_DIR"

if ! docker compose ps --status running db | grep -q cardyssey-db; then
  echo "ERROR: cardyssey-db is not running" >&2
  exit 1
fi

if ! docker compose ps --status running api | grep -q cardyssey-api; then
  echo "ERROR: cardyssey-api is not running" >&2
  exit 1
fi

echo "==> PostgreSQL backup"
docker compose exec -T db sh -lc \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$RUN_DIR/postgres.dump"

echo "==> Avatar backup"
TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

docker cp cardyssey-api:/data/avatars "$TMP_DIR/avatars" >/dev/null

tar -C "$TMP_DIR" -czf "$RUN_DIR/avatars.tar.gz" avatars

cat > "$RUN_DIR/README.txt" <<EOF
Cardyssey production backup
Created UTC: $TIMESTAMP
Platform path: $PLATFORM_DIR

Files:
- postgres.dump   PostgreSQL custom-format dump (restore with pg_restore)
- avatars.tar.gz  /data/avatars from cardyssey-api
EOF

(
  cd "$RUN_DIR"
  sha256sum postgres.dump avatars.tar.gz > SHA256SUMS
)

# Remove incomplete/empty backups before considering this run successful.
[[ -s "$RUN_DIR/postgres.dump" ]]
[[ -s "$RUN_DIR/avatars.tar.gz" ]]
[[ -s "$RUN_DIR/SHA256SUMS" ]]

echo "==> Retention cleanup (> ${RETENTION_DAYS} days)"
find "$BACKUP_DIR" \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  -mtime "+$RETENTION_DAYS" \
  -print \
  -exec rm -rf {} +

echo "OK: backup created at $RUN_DIR"
ls -lh "$RUN_DIR"
