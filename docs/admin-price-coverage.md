# Admin: missing prices by set and language

Open `/admin/prices`, section **Fehlende Preise nach Set & Sprache**. Android already opens the shared web admin from Account, so both platforms reach the same administrative view without a new APK.

- Search set name/code, filter the six supported languages, or restrict to missing prices / missing variant data.
- One group per exact set ID and language. Shows affected catalogue cards, missing price variants, the deferred subset and separate cards lacking usable variant IDs.
- Open a group's cards to view number, variant, status, diagnostic and next retry. Pages contain up to 100 entries. Copy the filtered summary or the current card page; the copied page states its range and total.
- Uses current positive finite PRICE_FOUND cache values. Old successful prices remain present here; stale refreshes continue in the existing monitor below. NO_PUBLIC_PRICE, provider errors, missing cache rows and invalid prices remain visible.
- Missing variant entries may be duplicate catalogue records; they are not presented as that many unique missing prices. Digital Pocket sets and unsupported languages are excluded. Set names prefer available DE/EN catalogue names.

Authenticated admin-only routes: `GET /api/v1/admin/price-coverage` and `/price-coverage/cards`. Filters are validated and bound as SQL parameters. Both queries have a 15-second database timeout; detail count and page come from one statement. No catalogue, price or user records are modified.

Validation: `python3 scripts/test-admin-price-coverage.py` exercises the actual repository SQL using temporary tables with rollback. Covers language/set isolation, digital exclusions, zero/NaN prices, deferred cases, missing variants/cache, multilingual set names and empty-page totals. Production read-only check reported 663 groups, 2,672 missing variant prices (27 deferred) and 39,766 catalogue entries without variant definitions. Counts change as imports run.

Backend Gradle tests/installDist and Web TypeScript/build passed. The initial constrained backend build reached its timeout; retry with persistent Gradle cache, four CPUs and 2 GB compiler heap completed in 3m08s. No `.env`, founder export or user edits were committed.

Manual check: select Japanese, open a set, inspect cards and copy a page; then select Traditional Chinese and verify the summary changes. Use the missing-variant filter to inspect Korean catalogue gaps. Refresh after a price import to confirm resolved variants disappear.
