# Cardyssey Shop catalog – rollout checklist (private beta)

## Current implementation
- Admin selection UI: `/admin/shop-catalog`. Founder/Admin only, with client-side check; proxy gates authenticated routes.
- Set/card identity from existing Cardyssey catalog APIs (`/api/sets`, `/api/sets/[id]`), six supported languages.
- WooCommerce CSV draft export. Each selected card/variant/condition receives a separate product SKU and stock/price.
- All exported products have `Published=0` even when marked for sale. Manual approval required.
- Reference artwork derives from `imageBase + /high.webp`; optional per-listing HTTPS photo overrides the image.
- UI stores unfinished selected listings locally in the browser, not server-synced.
- Optional WP alternate styling: `scripts/wordpress-cardyssey-shop-preview.php`. **Not deployed**.

## Important checks BEFORE importing any large catalog
1. Back up the WordPress database and uploads. Use **one small, controlled test set** first.
2. Verify build, login, authorization, responsive UI, output WooCommerce CSV encoding and import mapping.
3. Verify real card count, name, printed number, language, and image identity; all catalog images must resolve to the exact printing.
4. Check image licensing/redistribution permission for commercial shop use. Do not bulk-copy unlicensed assets just because the app displays them.
5. Check that the WordPress Docker instance can actually retrieve public image URLs from the Cardyssey image host. Internal/private paths or session-authenticated image endpoints do not work for Woo imports.
6. Validate the product attributes and separate inventory per condition and physical variant. Do not merge variants.
7. Do not repeatedly re-import CSV indiscriminately: duplicate SKUs and product matching/update behavior must be tested before bulk import.
8. Confirm that reference artwork is clearly described as representative, not a photo of physical condition. Use individual photos for damaged/high-value cards.
9. Ensure out-of-stock catalog entries are not buyable; keep **all imported products unpublished** until manually reviewed.
10. Confirm WordPress shop private gate remains intact, public registration closed, dark web design untouched.
11. Confirm tax configuration, shipping classes, legal policies, payment flow, refund workflow and commerce image usage before any public launch.

## Remaining engineering work
- Server-side authenticated WooCommerce draft/product upsert keyed by stable SKU and verified catalog/variant IDs.
- Explicit founder confirmation for publishing/unpublishing (with stock validation), instead of CSV round trips.
- Reconciliation of Woo stock after orders, refunds and cancellations; atomic overselling protection.
- Product variation taxonomy based on *actual* available variants, not free-text guesswork.
- Durable server-side listing drafts and import progress for many thousands of catalog entries.
- Admin image availability report and licensed asset strategy, plus owned-photo upload and thumbnail pipeline.
- Real WooCommerce categories: Einzelkarten > Set > cards, and separately Booster / Displays / Boxen / Zubehör.
- Deploy and visually test optional WooCommerce theme without disturbing checkout.
- Test Node.js/Brotli security update on the Tiny before launching publicly.

**No claim of live deployment or functioning WooCommerce synchronization until independently tested on the Tiny.**

## Prepared direct WooCommerce API integration (not enabled)

- Route: `POST /api/admin/shop/sync`, permitted only to approved private-beta admins/founder.
- Supports `draft`, `publish`, `unpublish`. Requires matching-origin request and WooCommerce API keys.
- Looks up by stable card/language/set/variant/condition SKU before updating; rejects ambiguous results.
- WordPress WooCommerce REST API credentials must have read/write products access, be stored in server-only environment variables (never `NEXT_PUBLIC_`), and be scoped to the shop.
- Set `CARDYSSEY_WC_URL=https://shop.cardyssey.de`, `CARDYSSEY_WC_CONSUMER_KEY`, `CARDYSSEY_WC_CONSUMER_SECRET`.
- After audit, live backup and testing, explicitly set `CARDYSSEY_WC_SYNC_ENABLED=true`. **Do not enable it before verification.**
- Requests fail closed if credentials or opt-in are absent; no products are published during coding.
- Frontend editor has buttons for draft/publish/unpublish, returning descriptive errors until enabled.
- Full catalog staging in the editor is not a durable bulk import. A separate paginated, rate-limited background reconciliation worker and media rights checks are still required.

## Large initial import tooling (prepared, not executed)

`python3 scripts/shop_catalog_bootstrap.py --language de` is a **read-only dry-run**.
After database backup, rights review and controlled staging test, use
`python3 scripts/shop_catalog_bootstrap.py --language de --apply --limit 20` and inspect
results before a full `--apply`.

Required environment:
`CARDYSSEY_API_URL`, `CARDYSSEY_ADMIN_TOKEN`,
`CARDYSSEY_WC_URL`, `CARDYSSEY_WC_CONSUMER_KEY`, `CARDYSSEY_WC_CONSUMER_SECRET`.

The script stages catalog cards as **unpublished, hidden, zero-stock** WooCommerce
products and creates category roots for Einzelkarten, Booster, Displays,
Elite Trainer Boxen, Kollektionen & Boxen, Zubehör. Per-card set categories
are created under Einzelkarten. It checkpoints successful products and does
not upload card art pending image rights and endpoint audit. It does not guess
foil/edition/condition. **Catalog placeholder SKUs and sellable listing SKUs
are intentionally distinct**, so staging a card cannot accidentally replace
an offer; shop presentation should bind catalog entries to offers by Cardyssey
card/set/language metadata instead of assuming identical Woo products.

WooCommerce native stock management is enabled for listings. Native WooCommerce
order processing should decrement purchased product stock once configured.
Validate the shop's order status settings, overselling/holding and restock
behavior for refunds/cancellations before enabling sales. **Do not implement
a second stock decrement hook** on top of WooCommerce native stock handling.
