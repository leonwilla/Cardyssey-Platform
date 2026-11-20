# Price recovery round 13 — 2026-10-10

## Result

32 additional official catalogue entries received their first ordinary-print variant, price-cache row and history point:
- 30 Japanese: one exact CardTrader NM/Mint asking reference and 29 Japanese TCGplayer market estimates through free TCGCSV.
- Two Korean: one exact CardTrader NM/Mint asking reference and one True Unicorn retail NM reference.

No existing positive price was deliberately audited or refreshed. All manual runs used missing-only filters and transactional preservation guards. No subscription was bought.

Wholly unpriced entries decreased from 37,598 to 37,566. These are catalogue entries including duplicate records, not a count of unique physical cards. German remains zero wholly unpriced; English 15; Japanese 12,822; Korean 17,215; Simplified Chinese four; Traditional Chinese 7,510.

## Recovery scope and source review

The Korean CardTrader missing-only pass checked 7,843 eligible candidates across 103 expansions and found one new acceptable offer. The Japanese pass found one new offer. The expanded Japanese identity pass additionally checked untranslated records against pinned source/PokeAPI evidence, but these newly considered records were trainers or ambiguous identities; no prices were invented.

The TCGCSV category-85 pass checked 1,252 verified Japanese candidates. Exact CardTrader-to-Japanese-TCGplayer product IDs yielded 29 usable market estimates. Ordinary quote finish, set/number/denominator, product name including any number suffix, rarity, HP and presale flag must agree. Missing/ambiguous product IDs, printings, unsupported groups and high estimates are held.

True Unicorn's public catalogue had 205 products and two available Korean AR singles. Drowzee SV1V 086/078 was missing and received a price; Iono's Kilowattrel SV9 104/100 was already priced and was skipped. The collection, public product JSON and Ajax quote agree on identity, SKU and USD price; NM condition and available stock are explicit. Current currency conversion evidence is stored.

See [free source review](free-price-source-review-2026-10-10.md) for all six languages and evaluated providers. PokéWallet is a promising recurring free API candidate requiring a free account/key; exact six-language quote coverage has not been verified. Metadata-only services are not treated as price sources.

## Persistence and weekly operation

Both new sources participate in the existing Sunday weekly workflow and preserve evidence for 14 days. Supplemental catalogue reimports preserve verified variants for unchanged identities and invalidate derived prices if the identity changes. API and Web share the same recovered variants and prices.

The missing-only option filters any already-positive card before provider requests, then blocks positive cache rows again inside the atomic catalogue/cache/history statement. This includes other variants and positive rows with an inconsistent status. Existing snapshot and conflict guards remain in force. Default weekly source refresh behavior remains enabled as requested earlier. The API background worker now only queues missing prices outside Sunday 04:17–24:00 UTC; that Sunday lane permits existing-price refresh. Queued targets are rechecked before provider calls and the cache upsert itself protects positive rows. Ignored writes cannot create history points.

TCGCSV evidence is MARKET_ESTIMATE with aggregate-market condition and unknown stock. It does not claim a live NM offer or an individual completed sale. The established 0.92 NM/base representation is kept.

## Validation

All offline price-matching suites passed, including new source/finish/language/stock/currency/number and missing-only checks. PostgreSQL rollback scenarios verify imports, repeat-run idempotence, positive-price preservation, unchanged reimport preservation and changed identity invalidation for both new sources. Import replay wrote zero rows. Kotlin tests and installDist passed; API runtime rebuilt and deployed.

Backup: /home/tv/cardyssey-backups/price-round13-20261010/pricing.dump.
Previous runtime image: cardyssey-api:before-round13-20261010.
Remote evidence: /tmp/cardyssey-round13-*.json and logs. No user-owned edits were committed.

## Background worker correction and final verification

The final whole-cache comparison exposed a separate API background refresh loop. It had changed 170 previously positive TCGdex-derived rows during runtime restart. These unwanted changes were restored in one transaction from the round-13 backup, only when the backup matched the baseline and the current row still matched the observed worker write. All original cache fields were restored; 170 corresponding unwanted history points were removed. The 32 new recovery prices were preserved.

The worker now keeps existing prices for the Sunday weekly lane while filling missing prices continuously. Kotlin tests cover the Sunday boundary and UTC conversion; four PostgreSQL fixtures execute the actual cache-upsert SQL for missing values, existing positives, inconsistent positive statuses and allowed weekly refresh. The guarded history insertion only runs after an actual write.

All 32 API detail/price pairs and all 32 Web pairs passed. The final comparison of 91,414 previously positive cache rows found zero differences in source, value, identity or original update timestamp after restoration. New import replay remained zero.
