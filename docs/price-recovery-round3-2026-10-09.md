# Price recovery and shared detail fixes (2026-10-09)

## Applied

- 159 additional exact Korean in-stock retail offers from Uturi Trading. Added 159 missing default normal variants together with 159 price/cache/history records. This does not infer reverse, Master Ball, promo or other printing variants. Matching requires explicit Korean language, exact set/SKU/number/rarity, independently verified species, single default product variant, matching JSON-LD new condition/stock/currency/price and unique catalogue identity. Official IDs/images are retained.
- Three exact Japanese edition offers from Hareruya (PCG8-028 first edition, PCG9-041 unlimited, PCG9-018 unlimited), explicitly condition A and in stock. Mixed/unmarked editions and damaged offers are rejected. An existing curated CardTrader edition identity can resolve a mistranslated name only after the live blueprint export confirms expansion, collector number and English species.
- Five exact Japanese public offers remain review candidates. A single asking price over EUR 100 is conservatively withheld from automatic collection valuation pending independent/manual review. This is a quality threshold, not a statement that no public price exists. Original JPY offers and exact URLs are preserved in the report; no price cap or invented market estimate is substituted.
- These prices are asking offers, not completed sales. All observations retain source, original currency/amount, condition, URL, time and conversion provenance. Optimistic cache version checks preserve newer prices; cache/history writes are atomic.
- Fixed shared API details for official supplemental cards: recovered proven mirror variants now reach Android/Web. Original nonempty supplemental variants take precedence; malformed/duplicate variants are rejected. This also makes the previous 259 recovered Japanese entries usable in card details.
- Fixed weekly supplemental import losing verification markers. Unchanged set/number/native name/image identities preserve their proof. Changed identities clear only derived variants and owned derived effective prices for re-verification; history and unrelated provider prices remain intact.
- New source refreshes run weekly, due after six days, with 240-second Korean and 120-second Japanese hard limits. Evidence and withheld high offers are retained as workflow artifacts for 14 days.

## Current coverage

| Language | PRICE_FOUND variants | NO_PRICE | Deferred | Catalogue entries without variants |
| --- | ---: | ---: | ---: | ---: |
| DE | 31,248 | 26 | 0 | 0 |
| EN | 34,005 | 53 | 0 | 0 |
| JA | 14,271 | 2,272 | 27 | 12,765 |
| KO | 398 | 0 | 0 | 19,613 |
| ZH-CN | 44 | 4 | 0 | 0 |
| ZH-TW | 8,137 | 287 | 0 | 7,229 |

2,642 known variants remain unresolved, plus 27 deliberate anniversary release holds. 39,607 catalogue entries lack variant definitions; these include duplicates and are not a count of unique missing cards. Korean cache NO_PRICE=0 does not mean Korean catalogue coverage is complete. Simplified Chinese still has only 48 catalogue entries.

## Validation

- Eight offline matching/hydration/review tests; three PostgreSQL rollback fixtures cover atomicity/idempotence/concurrent prices, the actual supplemental importer, and cross-language isolation.
- Existing 14 price coverage, 10 round-two matching, eight supplemental tests and three PostgreSQL coverage fixtures pass.
- Backend Gradle test/installDist passes, including three new variant detail tests. Shared runtime image builds. No Android-only schema or UI change, so no APK rebuild is needed for this block.
- Before writes, backed up all 167 candidate catalogue identities and their existing cache records under /home/tv/cardyssey-backups/price-round3-20261009T133426Z (uncommitted). Applied evidence stays on Tiny under /tmp/cardyssey-uturi-applied.json and /tmp/cardyssey-hareruya-applied.json.

## Withheld single-ask evidence

- E4-058 / 4ffrmhcfiaejakhepqdkx7o: JPY 60000, https://www.hareruya2.com/products/9013918105920
- E5-005 / 3a83wf50ts0ix73528ej4n7px: JPY 50000, https://www.hareruya2.com/products/9064024146240
- PCG6-039 / 2fnyg4g532wu18r396n1ly75loy: JPY 100000, https://www.hareruya2.com/products/9014120415552
- PCG6-043 / 3a83wf50tz7q114spsx7dw6v5: JPY 250000, https://www.hareruya2.com/products/9014287728960
- web1-036 / endfynwn4n10gzq: JPY 40000, https://www.hareruya2.com/products/9013867839808
