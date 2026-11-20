# Price recovery round 15 — 2026-10-11

Recovered **51 previously entirely unpriced Korean physical cards**: 13 BlackRoseSkulls and 38 NeroCards. These are explicit in-stock, Near Mint, ordinary single-card retail asking references, not verified sales. No existing positive price was refreshed. All 91,445 positive cache rows captured immediately before this round retained their source, value and timestamp.

## Coverage

| Language | Entirely unpriced cards after round |
|---|---:|
| German | 0 |
| English | 15 |
| Japanese | 12,822 |
| Korean | 17,164 |
| Simplified Chinese | 4 |
| Traditional Chinese | 7,510 |
| Total | 37,515 |

The total counts physical catalogue entries with no positive price across any variant. It excludes 480 partly priced entries. The separate missing-variant count is 36,257; it must not be presented as the total of unpriced physical cards.

## Sources and identity

- BlackRoseSkulls: 412 collection products checked against 12,681 eligible official Korean targets. Thirteen exact matches, no provider errors. Public collection, product JSON and Ajax detail must agree on product, title, SKU, selected variant and GBP amount. Language, condition, printed number/denominator, set, rarity and finish are explicit. Independent Korean/English/German species mapping and exact pinned official identity are required. Unit quantity, stock and subscription guards reject bundles, stale offers and unsuitable condition. GBP converts through the dated Frankfurter GBP/EUR quote.
- NeroCards: 1,216 collection products, 38 exact product candidates, all 38 validated. ProductGroup JSON-LD needs the exact live product group ID/name, child name, SKU and variant-specific offer URL. Product feed, Ajax and structured data must agree on EUR price, stock, Korean language, NM condition and normal printing. Existing Lake Cards/ManaMarket compatibility is retained.
- CardAnvil: 2,214 products, three eligible product candidates, zero accepted offers. Variant-specific structured quote identity is required even when feed/Ajax look plausible.
- Traditional Chinese: missing-only preview of 188 eligible known variants through existing retailers returned zero new quotations. This is not coverage of every one of the 7,510 unpriced physical entries.

New retailers participate in the existing weekly refresh workflow as independent source steps. Manual missing-only mode filters positive cards before retrieval and repeats the guard atomically at write time, including positive prices with inconsistent resolution status and positive prices on another variant. Weekly mode continues to refresh source-owned prices. Supplemental reimports and API variant preservation recognize the three new Korean source markers.

## Japanese identity limitation

Of 12,822 unpriced Japanese entries, 11,864 are imported official identities and 958 are other entries. Rarity is absent on 7,724 official records. Exact comparison with the already imported pinned source files confirmed that rarity is absent there too. This is not a dropped import field. Many are promos or deck/reprint sets: e.g. SI, XYP, SMP, XY, S-P, SV8a, SV4a and S12a. Booster rarity cannot be invented to make the current price adapters accept them. Further recovery needs a dedicated deck/promo/finish identity path with a source that proves the particular printing.

Additional sources were held: Nuneski is currently behind an Opening Soon/password storefront; LunaHobby variable singles lack exact printed numbers/SKUs; TCGBOX has a large Korean inventory but the checked listing did not prove Near Mint condition; LottiCards direct retrieval did not yield usable structured source data. No access restriction was bypassed.

## Validation and deployment

- 10 round-15 offline tests, 19 existing retailer regression tests and 13 round-13 identity tests pass.
- 18 PostgreSQL Korean/Japanese missing-only import and preservation cases pass.
- 3 PostgreSQL traditional-Chinese missing-only cases pass, including a positive target and an inconsistent positive other variant.
- Both successful source batches wrote one variant, one price and one history row per recovered card; replay wrote zero rows.
- Kotlin backend tests and installDist pass. Updated runtime deployed to Tiny.
- All 51 cards pass both direct API and Web detail/price checks: exact language and generated variant, correct source and NM EUR amount, valid range.
- Pre-existing positive price snapshot comparison reports zero changes.
- Database backup before the write: /home/tv/cardyssey-backups/price-round15-20261011/pricing.dump.
- Reports and full source observations remain outside the repository under /tmp/cardyssey-round15-*.

No new PokéWallet requests were needed in this round. No secret is stored in the repository.
