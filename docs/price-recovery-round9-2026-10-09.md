# Price recovery round 9 — 2026-10-09

## Live result

1,563 additional Korean official catalogue entries gained an ordinary-print variant, a price-cache row and a history point from exact CardTrader Korean Near Mint/Mint offers.
Korean PRICE_FOUND: 523 → 2,086. Missing-variant entries: 19,488 → 17,925.
All imports were new variants/prices. Replaying the evidence batch wrote zero rows.

These are current qualifying ASKING references, not completed sales. The stored value is the lowest qualifying offer, not an average of every available listing. Existing 0.92 NM/base representation is preserved.

## Provider coverage and strict identity

The general semantic CardTrader resolver excludes ko. A separate preview-first resolver now checks Korean ordinary booster prints without changing the existing western/classic resolvers.
5,296 eligible catalogue rows were checked; 51 expansions were uniquely matched by game and exact set code.
131 rows lacked a unique expansion, 2,451 lacked a unique verified blueprint, 1,140 lacked an acceptable Korean NM single, and 11 exceeded the EUR 100 single-offer review ceiling. No source errors occurred.

Require:
- Unique official_ko set/number identity, official denominator, complete catalogue details and image source.
- Game 5, category 73, exact expansion, numeric collector number and exact version number/denominator.
- Compatible explicit rarity and ordinary printing; exclude promo, reverse, Master Ball/Poké Ball, edition, stamp and special foil versions.
- Independent English/German/Korean species-name agreement.
- Blueprint language options include kr; listing explicitly selects kr and Near Mint/Mint.
- Exact listing/blueprint name, expansion, collector number and rarity.
- Explicit ungraded, unsigned, unaltered and non-reverse/first-edition flags when present or editable.
- Active seller, stock quantity exactly one, empty seller description, no explicit multi-unit bundle.
- Positive integer EUR cents and agreement between both API price representations.

The marketplace response does not expose the inventory-export bundle schema. This resolver uses category-73 single-card blueprints and stock=1 rather than silently treating arbitrary multi-stock offers as singles. It does not read another seller's inventory or manipulate carts.
CardTrader reference: https://www.cardtrader.com/it-IT/docs/api/full/reference
The marketplace endpoint is lightly cached by the provider; prices and stock are observations, not reservations.

## Weekly operation and import protection

The existing Sunday 04:17 UTC refresh now includes the Korean CardTrader resolver.
Requests are sequential and spaced at least 1.1 seconds. The step has a 900-second process limit / 16-minute workflow limit; overall job limit is 60 minutes.
Owned prices are refreshed each run. Source evidence is kept for 14 days, with incomplete checkpoints and atomic JSON replacement if a run is interrupted.
Incomplete or failed fetches do not apply database writes. Imports guard the full original catalogue identity, image, variants and price snapshot in the existing atomic catalogue/cache/history transaction.
Supplemental reimports preserve this source's verified ordinary print only while the identity remains unchanged; changed identities invalidate its derived prices.

## Validation and deployment

- 102 offline Python checks passed across eight suites.
- Four PostgreSQL rollback scenarios passed for the new source, including idempotence, concurrent-write protection and reimport invalidation.
- Kotlin tests and installDist passed; API runtime rebuilt and deployed.
- All 1,563 API card-detail/price pairs passed.
- 17 Web sample detail/price pairs passed across the import batch.
- Checked source, exact language/variant, converted NM amount and equal price ranges.
- Admin auth smoke passed.
- Full import snapshot was under 20 minutes old.
- Backup: /home/tv/cardyssey-backups/price-round9-20261009/pricing.dump.
- Previous image: cardyssey-api:before-round9-20261009.

## Other investigations

An exact full-pixel comparison of 1,690 same-language/set/number/name image-source conflict pairs found zero identical decoded full images: 163 differed, 1,527 lacked at least one local image. No image-based price/variant copies were made.
RocketColl's exact SC1D-135 product was out of stock.
Luna Hobby's Korean ex variation page has condition evidence but no reliable variant collector-number/SKU identity; some image metadata has inconsistent English names. No prices were copied from these unverified options.
True Unicorn has two available Korean singles, held for a future complete source adapter rather than partially imported.
Chinese and expensive Japanese review cases remain unchanged. Missing-variant counts can include duplicate catalogue entries; this round does not claim full coverage.
