# Native shop rollout on Tiny (no checkout)

**Must not mark complete until this runbook passes on real Tiny.** WordPress/WooCommerce remain private until domain cutover. No payment processing implemented.

## One batch on Tiny

```bash
set -e
cd ~/cardshop
sudo systemctl stop cardyssey-deploy.timer
git pull --ff-only origin main
sudo apt-get update
sudo apt-get install -y postgresql-client
(cd web && npm run build)
bash scripts/deploy-native-shop.sh
sudo systemctl enable --now cardyssey-deploy.timer
bash scripts/check-native-shop-readiness.sh
```

On failure, recover timer: `sudo systemctl enable --now cardyssey-deploy.timer`; do not run WordPress retirement script. Inspect `sudo journalctl -u cardyssey-web.service -n 100 --no-pager`. Deploy script creates PostgreSQL backup before schema changes, applies additive schema, restarts DB with localhost-only port 5433 and restarts existing web service. DB service may briefly restart; schedule an appropriate maintenance period.

## Acceptance tests (private admin account)

- Login at Cardyssey; /shop shows sets, cards and images; switching all six languages works and no WooCommerce links.
- /admin/shop-catalog loads; create one item as draft, reload, then check GET /api/admin/shop/native with admin session; update condition/variant, stock and price.
- Publishing a positive-price, nonzero-stock item shows the price and availability on /shop; no checkout/Buy button.
- Non-admin mutation returns 403; request with incorrect Origin returns 403; unauthenticated offers request returns 401.
- Re-run the same SKU upsert: only one offer and same ID, stock updated, no duplicate.
- Ensure image licences / media rights before commercial use; original condition photos recommended.
- Take tested SQL dump and ensure restore works before discontinuing WordPress.

## WordPress removal deliberately separate

- Check that `shop.cardyssey.de` reverse proxy directs to the native Next.js app, **not** the old WordPress port 8080. This DNS/reverse-proxy change is deployment-specific and must be verified with authenticated private browser.
- Confirm no remaining `/wp-json`, Woo CSV, shop URLs, storefront purchase links or external app dependency needs WP.
- Back up WordPress MySQL database, uploads, site config, secrets and shop data. No Woo product migration is expected from Oct 30 2026 evidence (zero products).
- Verify fallback/rollback path and cutover evidence. Only then retire WP/MySQL using `scripts/retire-wordpress-after-shop-cutover.sh` with explicit approval. The script intentionally only stops containers and **does not delete volumes**. Prune images/volumes only after tested restore and explicit later approval.
- No payment, shopping cart or order taking should be enabled until payment system, atomic stock reservations and consumer compliance are implemented.
- Keycloak migration is separate; existing Cardyssey login remains in place for this release. Never turn on unrestricted registration.
