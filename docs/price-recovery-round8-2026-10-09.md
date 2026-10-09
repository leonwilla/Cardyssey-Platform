# Price recovery round 8 — 2026-10-09

## Live result

27 additional Korean official catalogue entries now have a verified ordinary-print variant and an in-stock Near Mint retail reference:
- Level Up Games: 19, USD offers converted with dated Frankfurter USD/EUR.
- ShinyCardboard4U: 8, GBP offers converted with dated Frankfurter GBP/EUR.

Korean PRICE_FOUND: 496 → 523. Entries missing variants: 19,515 → 19,488.
These are ASKING references, not completed sales or market averages. Existing NM/base factor 0.92 is preserved.

## Identity and offer checks

The public Korean collections were fully paginated: Level Up Games 139 products, ShinyCardboard4U 31.
Only unique official_ko catalogue identities are eligible. An explicit set-name/code mapping, collector number, printed denominator, official set count, independent English/German/Korean species names and catalogue rarity must agree.
Level Up requires both the Korean title and language tag, Single Card product type, Korean set body description and a dedicated Near Mint condition option.
Shiny requires explicit card-detail fields for Korean, Near Mint, Reverse Holo: No, the exact number and an ordinary Holo/Non-Holo finish, plus the set code. Rare offers require explicit Holo proof; unlabelled Level Up rares are excluded.
Special printing, slabs, signatures, ambiguous conditions, unknown set aliases and trainers without species proof are excluded.
Feed, product JSON and Ajax variant identities and prices agree; product JSON declares currency and major units, Ajax confirms stock and integer minor units. Bundles and subscriptions are excluded.

Imports use the existing atomic catalogue/cache/history statement with complete old identity, image, variant and price snapshot guards. Replaying each evidence batch writes zero rows.

## Weekly refresh

Both sources are included in the existing Sunday 04:17 UTC workflow, with independent failure handling, 240-second source limits, and 14-day evidence artifacts. Owned prices are selected on every weekly run; language remains strictly ko.
Trusted source preservation/invalidation is extended in the supplemental importer and shared API. The overall workflow budget is 50 minutes.

## Validation and deployment

- 89 offline Python checks passed across seven suites.
- Eight PostgreSQL rollback scenarios for the two new sources passed: atomic writes/history, idempotence, concurrent price protection and catalogue reimport preservation/invalidation.
- Kotlin tests and installDist passed; API runtime rebuilt and deployed.
- All 27 API card-detail/price pairs passed; four Web pairs passed, covering both sources.
- Verified exact language, variant, source, converted NM EUR and matching ranges.
- Admin auth smoke passed.
- Preview evidence batches were under 15 minutes old at import; no source errors.
- Backup: /home/tv/cardyssey-backups/price-round8-20261009/pricing.dump.
- Previous runtime image: cardyssey-api:before-round8-20261009.

## Additional source investigation

TorecaCamp e1 and VS available first-edition offers did not close the remaining alternate-edition targets; web collection had no condition-A stock.
The two expensive Japanese round-7 candidates remain held: Hareruya's exact first-edition Electrode 036/092 listing was out of stock at JPY 30,000, so it does not corroborate TorecaCamp's JPY 45,800 current offer. Arcanine 016/088 unlimited did not gain an independently verified in-stock NM offer.
HobbyX public Pokemon feed and additional traditional-Chinese retailer search did not produce a validated exact open-target offer in this block. No Chinese prices were invented or imported.

Remaining missing variants include duplicate catalogue entries and are not a count of unique cards. This round does not claim complete coverage.
