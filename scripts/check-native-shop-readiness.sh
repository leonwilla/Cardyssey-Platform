#!/usr/bin/env bash
# Read-only readiness report; does not run migrations or expose secrets.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
echo "=== Native Cardyssey shop release gate ==="
printf 'Git: '; git log -1 --format='%h %s' || true
printf 'Native storefront: '; test -f web/app/shop/page.tsx && echo present || echo missing
printf 'PostgreSQL schema: '; test -f scripts/native-shop-schema.sql && echo present || echo missing
printf 'Web: '; curl -sS -m 5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/shop || true
printf 'Backend: '; curl -sS -m 5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/ || true
printf 'DB: '; docker inspect -f '{{.State.Health.Status}}' cardyssey-db 2>/dev/null || true
echo "=== Native commerce gates NOT YET CLEARED ==="
echo "- schema migration not run in production"
echo "- offer CRUD, server-side authorization and stock transaction code not deployed"
echo "- carts, orders, PSP sandbox/webhook/refunds not implemented"
echo "- Keycloak identity mapping/MFA migration not completed"
echo "- no DNS cutover, payment acceptance or WordPress removal authorized"
