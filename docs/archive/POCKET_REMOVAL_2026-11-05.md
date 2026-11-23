# Removal of digital Pokémon TCG Pocket (2026-11-05)

User requested **complete removal**, including pre-existing collection items. Scope: digital Pocket sets identified by `^(A[0-9]|B[0-9]|P-A)` (includes A1a/B2a). These are not physical cards and must not be included in the Cardyssey collection, search, scanner catalog or price coverage.

## Removed

- 8,322 catalog cards and 74 language/set entries in the current database, plus 74 set aliases.
- 3,733 print-level policy rows, including a mini-set cleanup (V56, V57).
- One existing collection row for a Pocket card by explicit user request. No matching wishlist entries. Existing ordinary physical collections were retained.
- 7,911 images from `/data/catalog/cards/<language>/<cardId>.jpg` on the `cardyssey-catalog` Docker volume.
- 5,483 detail cache rows and 30 cached catalog index rows in V56, plus mini-set cache rows in V57.
- `scripts/backfill-pocket-images.py` and `scripts/backfill-de-pocket-b2a.py`; neither had scheduled references.

## Permanent guards

- `CardCatalog.kt` excludes digital sets from general searches, set lists, set details and card details, including catalog-cache and direct remote indexes.
- `PermanentCatalogRepository.kt` refuses future inserts for Pocket sets/cards; pending mirror work and image matching exclude them.
- `scripts/sync_global_price_source_policy.py` excludes Pocket from price accounting. Daily source policy sync has been rerun.
- V56 and V57 remove existing Pocket catalog, user collection and price/source data; repeat safe (idempotent).

## Verified current baseline

After sync: DE **31,300 physical prints, 1,460 missing**; EN **495 missing physical prints**. The previous DE gap of 2,713 included 1,253 digital Pocket prints; previous EN gap of 2,975 included 2,480 digital Pocket prints. The exclusion does not invent or alter physical card prices.

## Future cleanup

No new containers or services. Never automatically restore Pocket from TCGdex or separate digital card datasets. Deleting the migration history would not be a rollback; restoration of user data would require a separately managed backup.
