# Price coverage: second recovery block (2026-10-09)

This follows the first coverage audit. It does not declare the backlog finished.

## Applied changes

- Added CardLand's public WooCommerce Store API as a free Traditional Chinese single-card source. Imported 35 exact, currently purchasable offers; six otherwise relevant offers were rejected for stock status. Matching requires language category, set, number, denominator, native name, explicit non-holo SKU, simple product without options, product ID and store URL. Currency minor units are read from the feed rather than assumed.
- These are retailer asking prices, not completed sales. Each price retains its source URL, original HKD amount, currency conversion date/rate and observation time using the existing shared retail import transaction. Cache/history writes remain atomic and conditional on the previous cache version.
- Recovered 259 Japanese duplicate catalogue entries from a single verified counterpart each. Required same language, set, normalized number, native raw name and exact nonempty image URL. Different images/names and ambiguous counterparts were rejected. No card IDs or collection records were merged or deleted.
- The recovered catalogue entries expose 562 variants. Copied 562 existing successful price records and 446 available matching original history points. This is duplicate coverage recovery, not 562 independent new market observations. Original price/history timestamps are retained; absent history is not invented. Newer destination prices are preserved.
- Added both recovery scripts and offline matching tests to the weekly workflow. Public HTTP imports have a 180-second hard limit; catalogue repair has a 40-second limit and 20-second SQL timeout.

## Database coverage after this block

| Language | PRICE_FOUND variants | NO_PRICE variants | Deferred variants | Catalogue entries without variants |
| --- | ---: | ---: | ---: | ---: |
| DE | 31,248 | 26 | 0 | 0 |
| EN | 34,005 | 53 | 0 | 0 |
| JA | 14,268 | 2,275 | 27 | 12,765 |
| KO | 239 | 0 | 0 | 19,772 |
| ZH-CN | 44 | 4 | 0 | 0 |
| ZH-TW | 8,137 | 287 | 0 | 7,229 |

There are 2,645 unresolved known variants and 39,766 catalogue entries without variant definitions. The latter include duplicates and must not be interpreted as that many unique missing cards. The 27 deferred Japanese anniversary promos retain their intentional release hold. The Simplified Chinese catalogue contains only 48 entries and is not a complete market inventory.

Together with the preceding block, 869 additional exact retailer offers have been recovered. PRICE_FOUND also includes older provider guides, estimates and retailer references; it is not a count of verified sales.

## Remaining evidence limits

Many Japanese leftovers distinguish first edition, unlimited or special printings. Hareruya's public VS descriptions explicitly warn that generic listings can mix editions unless the title identifies the edition, so these generic prices were not copied onto exact-edition variants. Native catalogue names can also be mistranslated. CardRush returned HTTP 403 and the Japanese TCGCSV group feed HTTP 401 in this audit; those probes were stopped rather than bypassed. Western leftovers include championship/trophy and other special printings requiring exact identity evidence.

Both Android and Web use the shared backend price cache. This block changes scripts/workflow and shared data only; it does not claim the catalogue detail UI or missing-variant admin UI has been completed.

## Validation and recovery

- 14 existing offline coverage/import tests and 10 new CardLand matching tests pass.
- Two isolated PostgreSQL fixture scenarios pass, covering partial-identity rejection, ambiguous-source rejection, original timestamps and repeat-run idempotence. Fixtures use temporary tables and roll back.
- Production import: 35 applied, zero source errors. Catalogue repair: 259 entries / 562 prices / 446 history points.
- Restricted server backups before mutation: `/home/tv/cardyssey-backups/price-round2-20261009/`. They include all 259 affected catalogue rows and 2,707 previously unresolved/deferred cache rows; import results and the coverage report are stored alongside.
- No application binary changes; no APK rebuild required. User edits, `.env` and `founder_duplicates.csv` were untouched.
