# Cardyssey native commerce: replace WordPress/WooCommerce

Status: ARCHITECTURE DECISION / IMPLEMENTATION BACKLOG. **Not deployed.** Keep existing production shop online and private until replacement passes acceptance tests.

## Decision

- Preserve Next.js web UI, Kotlin/Ktor API, PostgreSQL, Android app, and Docker.
- Replace WordPress/WooCommerce/MySQL with Cardyssey-owned shop APIs and a Next.js storefront. Do **not** replace established commerce payment processing with self-written card handling.
- Integrate external PSP hosted checkout/webhooks (provider selection pending); never collect/store credit-card PAN/CVV.
- Evaluate Keycloak OIDC for one login across web/app/shop **after** identity migration plan and account mapping; do not abruptly switch auth or create self-service registration. Only the two existing explicitly approved accounts can access the private beta.
- Avoid a second full commerce platform (Medusa/Vendure) by default, as it duplicates another product/catalog/account backend. Re-evaluate if a formal gap analysis finds native implementation risk exceeds platform operational cost.

## Store model

Catalog reference is NOT inventory. Catalog uses immutable printing key (language, set ID, card ID) and verified printed number. Selling offer binds that print to (actual foil/variant, condition, seller-owned photos, quantity, price, publication state). No fabricated condition/foil, no automatic live stock or publication during catalog import. Unique SKUs and idempotent imports.

Minimum schema:
- shop_categories (parent, locale, slug)
- shop_products (catalog ref OR non-card product, localized metadata)
- shop_offers (product, language, print, variant, condition, stock, price minor units, status, SKU)
- shop_media (offer, provenance/licensing, references)
- carts/cart_items (expiry, owner/guest), orders/order_items (immutable money snapshots), payments/payment_events, stock_movements, shipments, refunds, audit_events.
- Multi-lingual catalog supports de/en/ja/ko/zh-cn/zh-tw; shop country/shipping constraints must remain explicit.

## Non-negotiable security and correctness

- All monetary amounts integer minor units with currency; explicit tax/VAT treatment.
- Server-side identity and owner/admin role enforcement on every mutation. Private beta access remains closed.
- Stock allocation/reservation must be atomic in DB transactions; idempotency keys for checkout, PSP webhooks, refunds, payment events; verify webhook signatures and replay protection.
- Protected admin API, CSRF mitigations where cookie auth applies, rate limiting, audit trail, image upload constraints/scanning, secure secrets in runtime env, TLS and trusted proxy headers.
- Legal checkout disclosures, consumer cancellation/refunds, postage, order confirmation, invoice/record retention, German tax status (including Kleinunternehmer rule) must be validated prior to public sales.
- Test backups and restore; PCI scope minimize using hosted provider checkout. No production payments until E2E tests pass.
- Card images in commercial storefront require a vetted rights/usage policy; support original owned photos.

## Staged rollout

0. Freeze Woo import, leave existing WP private and read-only operational. Backup WP DB/uploads and Cardyssey DB. No secrets in Git.
1. Implement PostgreSQL migration + API read/catalog model, all existing set views, localized identities, offer drafts, tests.
2. Build dedicated /shop UI with card search, set/category tree, card details, only user-created offers, original photos; no checkout at first.
3. Build secured admin for stock/listings/prices and batch drafts; migrate/verify existing metadata; smoke-test both light/dark and Android links.
4. Implement carts, order state machine, atomic stock, shipment, refunds, hosted PSP checkout with webhook signatures, integration tests and sandbox orders.
5. Deploy parallel under a **non-public preview route** with permission gating, backup/rollback, real Android/web tests. Final DNS cutover only after signoff; disable WP endpoints, revoke Woo keys, archive export; then stop/remove WordPress/MySQL containers and their volumes **only after verified backup**.

## Keycloak evaluation

Optional auth service, not a security guarantee. OIDC Authorization Code + PKCE, identity mapping from existing accounts and roles, explicit registration disabled. Separate admin hostname/private access, HTTPS, proxy header trust, MFA, secret rotation, upgrades and healthchecks. Evaluate CPU/RAM and availability on 12–13 GiB WSL2 memory before adding a new container. If operational overhead is not justified for only two private users, retain/harden existing identity initially and defer migration.

## Current evidence

- `platform/compose.yml` hosts Ktor API + PostgreSQL; `web/package.json` runs Next.js.
- WooCommerce shop has zero products according to Oct 30 2026 local SQL check; no commerce-order migration demonstrated.
- WordPress private gate redirects unauthenticated `/wp-json/wc/v3` requests; do not weaken the gate for an integration being retired.
- `web/app/admin/shop-catalog`, `web/app/api/admin/shop/sync`, `scripts/shop_catalog_bootstrap.py` are legacy Woo integration and must not be used for the new native shop.
- Existing public WordPress shop remains live/private until explicit cutover; do not delete database or volumes.
