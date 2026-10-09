# Price recovery round 11 — 2026-10-09

## Live result

1,233 additional official catalogue entries gained an ordinary-print variant and a price:
- Japanese: 871 (750 ordinary booster entries + 121 additional Shiny/SSR entries).
- Korean: 362 (345 XY/M entries + 17 additional Shiny entries).
Another 24 already-priced entries were refreshed in the Shiny passes.
The four atomic batches wrote 1,233 new variants, 1,257 prices and 1,257 history points. Every replay wrote zero rows.

Entirely unpriced catalogue entries: 38,910 → 37,677.
Missing-variant entries: 37,652 → 36,419.
Japanese priced variants: 14,314 → 15,185; Korean: 2,353 → 2,715.
Entirely unpriced by language: de 0, en 15, ja 12,852, ko 17,296, zh-cn 4, zh-tw 7,510.
480 entries remain partly priced; known NO_PRICE variants remain 2,599, with 27 deferred variants.
Catalogue entries can include duplicates. These are asking references, not completed sales.

## Large source passes

Korean XY/M pass: 1,868 candidates, 19 expansions, 345 matches, zero source errors.
Japanese primary website verification was attempted, but the official site subsequently returned HTTP 403. The unfinished pass made no database writes; website requests were stopped.
The final resolver uses the already-imported, parsed official records from the pinned type-null/PTCG-database cache revision 18e0de2feb7a35ebe4296ede0ba6cc768961489b. It does not bypass the website restriction or portray cached metadata as a live page observation.
Japanese main pass: 2,815 catalogue candidates, 2,017 verified source records, 34 expansions, 750 matches, zero marketplace errors.
652 ambiguous official identities and 146 unsupported/unlabelled rarity records were held before marketplace matching.
Of verified rows, 60 lacked a unique expansion, 607 lacked a unique blueprint, 596 lacked a qualifying Japanese NM single and four expensive offers were held.
Japanese Shiny pass: 153 candidates, 149 verified records, 137 matches (121 new), zero source errors.
Korean Shiny pass: 829 candidates, three expansions, 25 matches (17 new), zero source errors.

## Verified Japanese identities

Require the cached source revision to match the imported catalogue source revision.
Verify the official source URL and numeric source ID, URL-derived catalogue ID, Pokémon card type, native title, image URL, set code, printed number, positive printed denominator and exact official rarity-icon URL.
Use the individual source record's printed denominator rather than a catalogue set aggregate that can include extra printings.
Uniqueness is among rarity-labelled official entries. Unlabelled mirror records are held and never priced by inference.
Reviewed XY aliases additionally require the original Japanese expansion title in the source record. Reprint-only plain XY6/XY7 entries remain excluded.
Blueprint and offer checks then require exact expansion, number/denominator, compatible rarity, independent English/German/Japanese species names, explicit Japanese Near Mint/Mint, ungraded/unsigned/unaltered/non-reverse/non-first-edition flags, single-unit stock, empty description and agreeing positive EUR-cent fields.
Shiny Holo Rare is accepted only for explicitly classified S records; the official S4a-226/190 image was visually checked for the S mark when reviewing rare_s_2. SSR requires an explicitly compatible Shiny Ultra Rare blueprint.
Offers above EUR 100 remain held. No Japanese prices are assigned to Korean records.

The dedicated Japanese writer protects the original catalogue/price snapshot and writes catalogue/cache/history atomically. Official reimports preserve unchanged provenance and invalidate derived prices on changed identity/image. The shared API exposes recovered variants only for the appropriate language/source.

## Weekly operation and validation

The Sunday 04:17 UTC workflow includes the Japanese resolver and expanded Korean coverage. Both refresh owned prices every run.
Japanese source evidence joins the existing 14-day artifact retention; requests to CardTrader remain sequential and at least 1.1 seconds apart.
Japanese limit: 1,200 seconds / 21-minute step; Korean: 900 seconds / 16-minute step. Overall workflow limit: 90 minutes.
127 offline checks passed across nine suites. Korean and Japanese atomic/reimport PostgreSQL scenarios plus the card-count fixture passed.
Kotlin tests and installDist passed. The API image was rebuilt and deployed.
All 345 Korean, 750 Japanese and 162 subsequent Shiny API detail/price pairs passed, with Web samples in every batch; admin authentication smoke passed. Checked exact source/language/variant, NM EUR amount and equal price ranges.

Backup: /home/tv/cardyssey-backups/price-round11-20261009/pricing.dump.
Previous image: cardyssey-api:before-round11-20261009.
Final coverage: /tmp/cardyssey-round11-audit-final.log.
Evidence: /tmp/cardyssey-round11-ko-applied.json, /tmp/cardyssey-round11-ja-applied.json and both language-specific Shiny applied reports.
