# Price recovery round 10 — 2026-10-09

## Live result

267 additional Korean official catalogue entries gained an ordinary-print variant, a price-cache row and a history point. Another 1,563 source-owned prices were refreshed from current exact CardTrader Korean Near Mint/Mint asking offers.
The atomic import wrote 267 variants, 1,830 prices and 1,830 history points. Replaying the evidence wrote zero rows.
New rarities: 162 R, 64 C, 24 U, 17 RR.
Korean priced variants: 2,086 → 2,353. Korean entries without variants/prices: 17,925 → 17,658.

## Expanded strict coverage

The existing exact Korean resolver now includes SM-numbered booster sets alongside S and SV.
It checked 8,017 eligible rows across 84 uniquely matched expansions. Final preview: 1,830 matches, 458 rows lacking a unique expansion, 3,593 lacking a unique verified blueprint, 2,125 lacking an acceptable in-stock Korean NM single, 11 expensive offers held for review, zero fetch errors.
R cards additionally require fixed rarity Holo Rare and the complete version format Holo Rare | number/denominator. Generic Rare, non-holo and unspecified foil are insufficient.
The existing exact set, denominator, species, native name, Korean language, offer identity, condition, non-reverse, single quantity, seller status and EUR-cent agreement checks remain in force.
These prices are asking references, not completed sales.

The existing Sunday 04:17 UTC job invokes the expanded resolver automatically; owned prices are refreshed each run. Its 900-second process and 16-minute step limits remain sufficient for this completed run. Source evidence is retained for 14 days.

## Accurate backlog accounting

The audit now reports entirely_unpriced_entries and partially_priced_entries independently from variant counts.
A catalogue entry is entirely unpriced only when none of its current variants has a same-card, same-language, same-variant PRICE_FOUND row. Orphaned cache rows and prices in another language do not count.
A partially priced entry has both a priced variant and a variant without PRICE_FOUND.
Digital catalogue sets remain excluded. Entries can include catalogue duplicates; the totals are not a count of unique physical print identities.

After import:
- Entirely unpriced entries: 39,177 → 38,910.
- Partially priced entries: 480.
- Missing-variant entries: 37,919 → 37,652.
- Known NO_PRICE variants: 2,599; deferred variants: 27.
- Entirely unpriced by language: de 0, en 15, ja 13,723, ko 17,658, zh-cn 4, zh-tw 7,510.

## Validation

103 offline Python checks passed across eight suites, including the new explicit-holo/reverse rejection case.
Four existing Korean PostgreSQL rollback scenarios passed, covering atomic catalogue/cache/history writes, replay idempotence, concurrent newer prices, preservation and invalidation during reimport.
A new isolated temporary-table PostgreSQL fixture validates whole/partial price counts, missing variants/cache, wrong language/variant, deferred status and digital exclusion. Its transaction rolls back.
All 1,830 API detail/price pairs and 20 Web sample pairs passed for source, exact language/variant, NM EUR amount and equal price ranges; admin authentication smoke passed.
The import evidence was under 20 minutes old.
No API code changed, so the existing shared API served the updated catalogue and prices immediately.

Backup: /home/tv/cardyssey-backups/price-round10-20261009/pricing.dump.
Evidence: /tmp/cardyssey-round10-preview.json and /tmp/cardyssey-round10-applied.json.
Live verification: /tmp/cardyssey-round10-smoke.log.
Coverage: /tmp/cardyssey-round10-audit.log.
