# Permanent multilingual card catalog

Cardyssey mirrors immutable card metadata and artwork on the Tiny. Android and
Web use the Cardyssey API; external catalog requests are background sync input,
not part of the normal scan path. Price data deliberately remains separate and
keeps its own TTL.

## Stored permanently

PostgreSQL stores, per language:

- set id, localized set name and card counts
- printed set-code aliases (for example `PBL EN` -> catalog set id)
- card id, local/set number, localized card name and rarity
- exact physical variants supplied by the source
- original source payload, first/last seen timestamps
- local artwork path, byte count and 64-bit visual fingerprint
- per-language import status and progress

The named Docker volume `cardyssey-catalog` stores downloaded JPEG artwork at
`/data/catalog`. It survives API container rebuilds and recreations. PostgreSQL
uses the existing `cardyssey-postgres` volume.

Only deleting those named volumes deletes the mirror.

## Synchronization

At startup the API:

1. refreshes the compact set/card indexes for every configured language;
2. upserts new and corrected records without deleting historical rows;
3. completes detailed variant metadata in resumable batches;
4. downloads missing artwork and calculates a visual fingerprint;
5. repeats the source check after the configured interval.

The initial import can take a long time because it contains every available
language and image. Languages are processed round-robin so one large language
cannot block the others. Restarting the API resumes missing rows/files.

Default settings in `platform/compose.yml`:

```text
CATALOG_SYNC_INTERVAL_HOURS=24
CATALOG_DOWNLOAD_IMAGES=true
CATALOG_DETAIL_BATCH_SIZE=250
CATALOG_IMAGE_BATCH_SIZE=250
CATALOG_LANGUAGES=de,en,fr,es,it,pt,ja,zh-tw,zh-cn,ko,id,th,nl,pl,ru
```

Metadata is permanent. The 24-hour interval only checks for new/corrected
source data. It does not expire or delete stored cards. Prices are refreshed by
the existing pricing system and are not copied into this permanent catalog.

## Coverage and retries

`ready / waiting` means the sync cycle ended without recorded request failures;
it does **not** mean every printed card or every source image exists locally.
`partial / waiting` retains the last failed source/detail/image operation.
Failed items remain pending and are retried in the next cycle. Keyset cursors
allow later items to proceed even when an entire earlier batch fails.

The detail work query keeps stale records inside their requested language.
Wrong-language detail fallbacks are not written as completed localized records.
Index refreshes preserve previously stored detailed payloads. A changed image
URL invalidates the existing fingerprint so the replacement is downloaded and
hashed. Unchanged images are retained; edits at the same upstream URL are not
detected by this mechanism.

Normal catalog reads refresh the persistent response cache after six hours;
on upstream failure an older response remains available. Explicit mirror source
refreshes do not silently treat an old cached response as a successful refresh.

Run the read-only coverage audit from `~/cardshop/platform` after updating:

```bash
docker compose exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < ../scripts/catalog-coverage.sql
```

The audit separates missing source URLs from pending downloads and includes
concrete Asian card/set IDs for validating supplemental-source mappings.
Supplemental sources and their independent import status are described below.
No completeness claim or all-card price backfill is made. Prices can be absent
when the provider does not cover the exact language and physical variant.

## Scanner path

Android extracts OCR plus a compact card crop. It sends that crop only to the
Cardyssey API. The API:

1. hashes the crop;
2. compares it with local fingerprints for the selected language;
3. narrows by normalized card number and known printed set code when available;
4. combines the visual matches with OCR matches;
5. returns local Tiny image URLs and candidate metadata.

No internet-wide image search occurs during a scan. If foil/reverse cannot be
determined safely, Android asks the user instead of stacking an uncertain
variant.

## Deployment

```bash
cd ~/cardshop
git pull --ff-only

cd ~/cardshop/platform
docker compose up -d --build api
```

Do not remove `cardyssey-catalog` during updates.

The API may answer before the first catalog import is complete. Follow progress
without stopping the import:

```bash
docker compose logs --tail=100 -f api
docker volume inspect cardyssey-catalog
docker system df -v
```

Authenticated clients can read:

```text
GET /api/v1/catalog/mirror/status
```

A healthy response contains one row per configured language with `phase`
(`index`, `details`, `images`, or `waiting`) and set/card/image counts.

## Required containers

For catalog, scanner, collection, themes and chat:

- `cardyssey-db` — PostgreSQL and catalog metadata
- `cardyssey-api` — API, background catalog sync and local image matching

Additional price infrastructure:

- `cardyssey-ebay-browser` — only required for direct eBay collection

The Next.js web app runs as `cardyssey-web.service` on the host, not as a
Compose container. WordPress/cardshop, Vinted and Palworld are unrelated to the
Cardyssey catalog.

## Supplemental Asian sources (V29)

`Supplemental Catalog Sync` is a daily Tiny workflow (02:10 UTC) and supports
manual dispatch. A change to this workflow on main deploys the API and starts
the import automatically; a manual dispatch can set `deploy_api=true`. It rebuilds only
the API, using the existing Tiny environment and Compose project, waits for V29,
and starts the import. Later scheduled runs do not redeploy the API.

- Japanese, Korean and Traditional Chinese records come from the data files in
  https://github.com/type-null/PTCG-database (MIT, attribution in
  `docs/THIRD_PARTY_CATALOG_SOURCES.md`). Official page and image URLs are retained.
  The source revision is recorded. No code from that repository is executed.
- Thai and Indonesian records are read from the official Pokémon Asia lists and
  detail pages. Product code and collector number must be explicitly present.
- Simplified Chinese has **no new source** in this change. Its existing TCGdex
  records are not a verified complete Simplified Chinese catalog. The separate
  PTCG-CHS-Datasets repository is not imported: its published terms exclude
  redistribution without authorization.

The importer defaults to a read-only dry run; `--apply` writes to the Tiny database:

```bash
python3 scripts/sync-supplemental-catalog.py --apply
```

A dedicated sparse Git cache and cached official detail pages live under
`~/.cache/cardyssey-catalog`. A file lock prevents overlapping imports. Records
are committed in batches; a timeout or source refusal preserves completed work
and reports an error/partial status. The next run resumes from cached pages.
No challenge bypass is performed. The first download can take hours.

New official cards have stable source-derived IDs. A record reuses an existing
TCGdex ID only when language, explicit set code, printed number and original
name uniquely agree, and the source does not show multiple illustrations at that
identity. Streaming Thai/Indonesian imports retain independent IDs. This can
leave visible duplicates; it prevents silently replacing an existing print.
Unverified or malformed rows are counted as skipped, not imported successfully.

Supplemental cards are available in search, card details, sets and set details.
The original name is retained, with a German species-name aid when the data
contains a unique Pokédex number. This is not a translation of the entire card.
No normal/holo/reverse variants or prices are inferred from a picture or rarity.
Existing TCGdex variant and pricing identities are preserved.

The existing image worker downloads and hashes the added images into the same
permanent volume. It also drains pending images between daily source cycles.
An imported metadata record is not yet an indexed image. Public image responses
have a one-hour cache lifetime so future replacements are not declared immutable.

`catalog_supplemental_sync` reports metadata-source progress separately from
`catalog-coverage.sql`'s actual downloaded/indexed image counts. `imported` means
all accepted metadata from that source run was processed, not full worldwide
card coverage or completion of every image download. Rejected records produce
`partial` and a non-zero workflow result so gaps cannot silently appear green.

### Prices

Image downloads do not supply market values. Existing exact-language,
exact-variant pricing providers continue to retrieve available prices on demand.
There is no all-card price backfill in this change. Unsupported languages,
unknown variants and blocked eBay requests remain without a verified price.
Nothing substitutes a different-language price or zero for an unavailable value.

### Validation

- Python source/parser regressions: `python3 scripts/test-supplemental-catalog.py`.
- Catalog Kotlin sources compiled with Kotlin 2.1.20 and the serialization plugin.
- V28/V29 and the actual import SQL were exercised with PostgreSQL (PGlite):
  language/number matching, unchanged-image retention, changed-image invalidation,
  variant preservation, repeated import and ambiguous-print separation.
- Official Thai/Indonesian HTML and Korean M1S 013/056 source records were checked.
- Production deployment, full import counts and physical scanner behavior require
  the Tiny workflow and the device tests; these are not claimed by local checks.
