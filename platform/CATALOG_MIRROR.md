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
