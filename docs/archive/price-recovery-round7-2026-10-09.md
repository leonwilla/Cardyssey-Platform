# Price recovery round 7 — 2026-10-09

## Live result

111 additional physical card/variant price cases resolved with three new free
public retailer sources:

| Source | Language | New priced variants | New catalogue variants |
| --- | --- | ---: | ---: |
| Lake Cards | Korean | 21 | 21 |
| ManaMarket | Korean | 49 | 49 |
| TorecaCamp | Japanese | 41 | 0 |

Korean PRICE_FOUND increased from 426 to 496; missing Korean catalogue variants
decreased from 19,585 to 19,515. Japanese PRICE_FOUND increased from 14,273 to
14,314 and NO_PRICE decreased from 2,270 to 2,229.

These are retail asking quotations, not verified completed sales. Price history
and source evidence preserve the listed currency, exact selected variant, shop
condition, observation time and conversion basis.

## Korean source matching

The public singles collections were completely paginated: Lake Cards 7,249
products, ManaMarket 391. Require one eligible Korean / Near Mint / Normal
variant, exact set/collector number/SKU, an unambiguous official Korean catalogue
identity, and independent English/German/Korean species agreement.

Validate the selected variant's stock and EUR price in the collection feed,
product Ajax JSON and variant-specific schema Offer. Match product IDs, variant
IDs, SKU and same-domain canonical URLs; reject bundles, subscriptions, graded
cards, reverse/special prints and bulk discounts. Read JSON only; execute no
storefront JavaScript.

ManaMarket's Fixed rarity label does not identify a foil. Only independently
non-holo C/U catalogue rarities are accepted under that label. Unclear R or
multiple official print identities remain blocked. Other rarity labels must
agree with the exact catalogue rarity. Rate-limit requests sequentially and
prefilter invalid identities before fetching details. The initial faster preview
hit HTTP 429 and wrote nothing; the revised complete preview had zero errors.

Source-owned variants remain visible through the shared API and survive an
unchanged official catalogue import. A changed official set/number/name/image
invalidates these derived variants and effective source prices. Existing newer
prices are protected by catalogue and cache snapshots. Reapplying the same
evidence wrote zero variants, prices and history rows.

## Japanese classic-edition matching

The importer checks 43 curated card/edition identities: four VS Trainers and 39
E/PCG candidates discovered across the following collections:

VS, E2, E3, E4, E5, PCG1, PCG2, PCG3, PCG4, PCG5, PCG6, PCG7, PCG8, PCG9.
The remaining PCG collections had no eligible exact-edition condition-A offer
in the examined stock.

The committed identity manifest preserves the exact Japanese retail title,
product ID, source collection/category, collector number/denominator, edition,
catalogue variant ID and independently fetched CardTrader expansion/blueprint
ID/English alias. This resolves provider catalogue names that are transliterated
or mistranslated without treating those names alone as a price identity.

Require explicit 1ED or unlimited print identity, exactly one catalogue printing
for that edition, and the exact condition-A variant. A-minus and other conditions
are excluded. Product JSON explicitly declares major-unit JPY; Ajax stock refers
to the same variant ID and SKU. No Ajax currency-unit assumption is made.
JPY/EUR uses the dated public rate and the established 0.92 NM/base convention.

Four VS prices were imported first; 37 further classic prices were imported
after the broader identity audit. The four existing same-round prices were kept
during the second application. Both repeated evidence applications wrote zero
new rows. Two single asking quotations exceeding EUR 100 remain in the review
report: E2-036 first edition and E5-016 unlimited. They are not imported as
automatic valuations without independent price corroboration.

TorecaCamp's primary guide distinguishes A from A-minus and explicitly says that
unlabelled edition listings do not establish 1ED/unlimited. The importer follows
that rule. Condition provenance is recorded as the shop's Japanese pre-BW A
grade, not an undisclosed conversion of a poorer condition.

## Weekly refresh

All three new sources are wired into the existing Sunday workflow, with bounded
execution and evidence reports retained for 14 days. No paid API was added.

The Korean, Traditional Chinese and Hareruya retailer loaders now revisit their
own prices on every weekly run. This removes the calendar gap caused by a
six-day age threshold: a Friday import skipped on Sunday could otherwise become
nine days old before the next Sunday. A sold-out or invalid offer never receives
a fabricated fresh timestamp.

Independent source steps continue after another provider fails, provided the
shared safety tests passed and the workflow was not cancelled. Errors still
fail the workflow and retain diagnostic evidence. The job limit is 40 minutes;
each newly added source has its own bounded timeout.

## Verification

- 77 offline safety tests passed across six suites.
- 13 PostgreSQL rollback scenarios passed for the new Korean/Japanese sources,
  including repeated evidence, concurrent newer prices, catalogue changes,
  cross-language protection and official-import provenance/invalidation.
- Kotlin backend tests and installDist succeeded; runtime rebuilt and deployed.
- Live Android API: 111 detail/price pairs verified.
- Live Web proxy: nine detail/price pairs verified across both languages/sources.
- Exact language, exact edition/variant, source and condition-adjusted EUR agree.
- Shared admin authorization/filter/pagination smoke tests passed after deployment.
- Weekly workflow parsed successfully as YAML; git diff --check passed.
- No newly priced cache rows are older than eight days in the live audit.

Examples to test in the app or Web (NM at the observed rate):

| Card | Language | Price |
| --- | --- | ---: |
| Aquana ex SV8a-205 | Korean | EUR 49.99 |
| Feurigel SV9a-015 | Korean | EUR 0.99 |
| VS1-133 first edition | Japanese | EUR 3.84 |
| E3-060 unlimited | Japanese | EUR 16.81 |

## Remaining physical catalogue gaps

| Language | Known variants without price | Held cases | Entries without verified variants |
| --- | ---: | ---: | ---: |
| de | 26 | 0 | 0 |
| en | 53 | 0 | 0 |
| ja | 2,229 | 27 | 12,765 |
| ko | 0 | 0 | 19,515 |
| zh-cn | 4 | 0 | 0 |
| zh-tw | 287 | 0 | 7,229 |

Entries without variants may contain duplicate or distinct print records; they
are not counts of unique unpriced cards. No blanket no-public-price conclusion
or fabricated variant was applied. Remaining blockers include ambiguous official
prints, unsupported special editions, missing exact-condition stock and the two
high asking quotations held for independent review.

## Evidence and rollback on Tiny

Backup: /home/tv/cardyssey-backups/price-round7-20261009T163536Z

Evidence:
- /tmp/cardyssey-round7-lake-applied.json
- /tmp/cardyssey-round7-mana-applied.json
- /tmp/cardyssey-round7-toreca-applied.json
- /tmp/cardyssey-round7-toreca-classic-applied.json
- /tmp/cardyssey-round7-smoke.log
- /tmp/cardyssey-round7-ja-smoke.log
- /tmp/cardyssey-round7-audit-final.json

Previous runtime image: cardyssey-api:before-round7-20261009.
