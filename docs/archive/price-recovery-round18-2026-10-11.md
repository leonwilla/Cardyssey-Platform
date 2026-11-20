# Price recovery round 18 — 2026-10-11

Added **849** first-price Japanese catalogue entries. The full applicable TorecaCamp inventory was considered, with **1,541** in-stock product candidates checked live and **0** provider errors. No arbitrary card cap was used.

## Results

- Entirely unpriced catalogue entries remaining: **33,616**.
- Existing positive rows preserved inside the manual transaction: **94,549**.
- All newly imported amounts, sources and actual generated variants verified in the database.
- API and Web verified for **21** representatives covering source/set/rarity/printing cohorts and price extremes.
- Import replay created no additional variants, prices or history points.

These are catalogue-entry counts, including existing duplicate records, rather than a count of deduplicated physical cards or cache variants.

| Language | Entirely unpriced entries |
| --- | ---: |
| de | 0 |
| en | 15 |
| ja | 8,928 |
| ko | 17,164 |
| zh-cn | 0 |
| zh-tw | 7,509 |

| Source / retailer printing caption | New prices |
| --- | ---: |
| WEB_TORECACAMP_JP/reverse | 271 |
| WEB_TORECACAMP_JP/ordinary | 578 |

## Exact print disambiguation

The ordinary bulk reader retains its unique-identity requirement. A separate full-card reader considers pinned official Japanese peers with otherwise identical complete native name, printed set, number and denominator. Every official peer in a group must pass raw-record/revision/official URL/hash ID/native name/number/image/rarity checks. Unknown or incomplete peers hold the group. Already priced and otherwise ineligible peers remain in the image competition; their prices are never reassigned to another unpriced print.

Full-card renders are normalized to 217 × 303 pixels, and both the entire frame and a fixed lower-card foil/text-background region (16,165,201,265) are compared. The best peer must have mean RGB error at most 2.5 in both regions. Every competitor must have error at least 8 in both regions and at least four times the best error in each region. Equal images, close peers, artwork-only agreement, insufficient foil distinction and poor images remain held. These calibrated gates were checked visually against accepted and held full-card examples and covered by negative tests.

TorecaCamp's public card renders support this method. Hareruya photographed examples did not pass the same raster proof and were not imported through this method. The default image reader therefore uses TorecaCamp; the existing unique-print Hareruya reader continues separately. Modern eligible code limits remain in force, including the existing older-edition holds.

When retailer rarity is omitted, the exact pinned full-card raster identifies the official print; catalogue rarity is retained unchanged. Explicit contradictory retailer rarity remains held. This exception is confined to the image-backed reader; the original textual reader stays strict.

Public product feed and live Ajax product metadata, original title, product ID/handle, variant/SKU, condition A, stock, unit quantity and price must agree. Anonymous session cart currency must remain JPY before and after the run. Shopify's documented Ajax JPY price units and dated JPY/EUR conversion remain unchanged, with NM factor 0.92. Expensive asking references above EUR 100 are held for review.

Normal and reverse prints are written using their actual generated variant and NORMAL/REVERSE cache legacy. Explicit retailer Pokéball/masterball captions can carry their corresponding foil label. A generic mirror caption creates a reverse variant without inventing a named foil. Existing catalogue variants cannot be reclassified. Conflicting retailer finish descriptions for the same official image are held.

Stored source evidence includes live offer metadata, original title, dated FX, retail image URL/hash, each official template URL/hash, both image errors for every peer, and the image thresholds. Prices remain labelled retail asking references, rather than claims of completed-sale market values.

## Additional free API check

The existing PokéWallet reader also checked 858 eligible unpriced Japanese targets, using 30 requests with an allowed per-run ceiling of 80 and the existing free-plan hourly/daily reserve. It found zero qualifying new market quotes, with zero provider errors and no quota limitation. The remaining candidates were held for provider-set/blueprint/quote ambiguity or missing evidence; one market reference exceeded the existing high-price review threshold. No API price was fabricated or written. This was not a 50-card run cap.

## Preservation and weekly refresh

Manual import uses the established atomic transaction with a cache writer lock, a transaction-local snapshot of all positive rows, missing-only guards, catalogue/price snapshot agreement, expected per-batch import counts, and a before/after comparison of all existing positive rows. Sunday's separately authorized weekly API updates before or after that short transaction are not reverted.

The weekly workflow now has an independent bounded image-reader job, with an isolated virtual environment and pinned Pillow dependency. It tests the reader, fetches complete current applicable public inventories, rechecks exact images and live quotes, recovers new eligible entries, and refreshes source-owned prices weekly. Its evidence report is retained as a workflow artifact. Existing weekly readers retain their own job budget.

## Validation and evidence

- 17 full-card/metadata/condition/currency/variant negative and positive tests passed.
- 12 real PostgreSQL variant creation, positive-price preservation, replay and authorized weekly refresh cases passed.
- Existing round-16 tests (30), round-13 offline tests (13) and round-13 PostgreSQL cases (24) passed.
- Workflow YAML parsed and isolated job structure checked.
- Transaction preservation, all-new-price/variant checks, replay, API/Web checks and final coverage audit passed.
- Pricing backup: /home/tv/cardyssey-backups/price-round18-20261011/pricing.dump.
- Runtime evidence: /tmp/cardyssey-round18-preview.json, /tmp/cardyssey-round18-applied.json, /tmp/cardyssey-round18-result.json and matching logs.
- Primary product contract: https://shopify.dev/docs/api/ajax/reference/product
- Primary retailer: https://torecacamp-pokemon.com/
- Primary official prints: https://www.pokemon-card.com/card-search/

## Held reasons

- best_print_ineligible: 155.
- feed_condition_or_stock: 173.
- image_not_distinct: 535.
- incomplete_pinned_peer_group: 1.
- invalid_full_card_image: 2.

These are rejection-event counts, not deduplicated missing-card counts. Cards without a safe offer remain unpriced.

## New prices by set

| Set | New prices |
| --- | ---: |
| S10a | 58 |
| S11a | 77 |
| S12a | 114 |
| S9a | 75 |
| SV11B | 1 |
| SV2a | 153 |
| SV4a | 119 |
| SV8a | 248 |
| SVI | 4 |
