#!/usr/bin/env bash
# Stop WordPress after native shop cutover verification. Never deletes DB/volumes.
set -Eeuo pipefail
cd /home/tv/cardshop
if [[ "${1:-}" != "--execute" ]]; then
 echo "DRY RUN only. Usage: sudo bash scripts/retire-wordpress-after-shop-cutover.sh --execute"
 echo "Requirements: verified Cardyssey shop DNS, admin workflows, backup, rollback and explicit cutover."
 exit 0
fi
if [[ "${CARDYSSEY_SHOP_CUTOVER_APPROVED:-}" != "YES" ]]; then
 echo "Refusing: require CARDYSSEY_SHOP_CUTOVER_APPROVED=YES after actual cutover tests." >&2
 exit 2
fi
if [[ ! -f /home/tv/cardshop/backups/native-shop-cutover-approved.txt ]]; then
 echo "Refusing: missing human-reviewed cutover evidence file in backups." >&2
 exit 2
fi
if ! curl -fsS -m 10 http://127.0.0.1:3000/login >/dev/null; then
 echo "Refusing: Cardyssey frontend unavailable." >&2; exit 2
fi
echo "Stopping WordPress and its dedicated MySQL only; volumes are preserved."
docker stop cardshop-wordpress cardshop-db
echo "Stopped. Do not delete volumes; restore with docker start cardshop-db cardshop-wordpress"
