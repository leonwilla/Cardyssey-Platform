# Missing-price bulk audit and import threshold — 2026-10-11

> Update 2026-10-12: The user superseded the 1,000-card manual minimum. Nonempty verified missing-price cohorts may now be imported; see price-recovery-round22-2026-10-12.md. This document records the earlier audit.
## Result

No manual prices imported. A complete 181-expansion CardTrader inventory audit found 1,366 blueprint/expansion combinations with offers that passed the existing Korean NM stock/offer checks. Those are not 1,366 independently identified missing cards. Running the existing complete identity matcher against that saved inventory produced only **10 distinct missing Korean cards**. No rarity, edition, language, stock, condition or identity guards were relaxed to inflate the result.

The requested 1,000-new-price manual block is still blocked by insufficient independently verified missing-card coverage. The ten CardTrader matches remain candidates for a future combined block; no small import was started.

## Tested sources

| Source | Inventory test | Missing-card outcome |
| --- | --- | --- |
| CardTrader | All 181 Pokémon expansions whose normalized code occurs among entirely unpriced Korean catalogue cards; both blueprint and Korean-product exports saved; no provider errors | 2,785 blueprint/expansion combinations had any offers, 2,662 had Korean NM/Mint stock, 1,366 passed strict stock/offer checks. Final full identity matcher: 10 distinct missing cards. These levels must not be conflated. |
| Cardotaku | Complete Pokémon collection, 2,155 products, 1,058 with an available positive-price variant | Expanded numbered-title parser processed 1,273 products, including titles without a rarity suffix; ten available products share a set/number with missing Japanese rows, seven touch pinned unique target candidates. These are preliminary candidates, not verified quotes. The remaining 882 titles include promos and merchandise outside this parser; the audit does not claim they have no possible prices. Condition, exact printing/image, currency and live quote validation remain required. |
| BGTCG | Complete mixed single-card collection, 3,121 products, 2,233 with available stock | Parsed available Asian singles: 274 Japanese, 1,599 traditional Chinese. Exact native-name/set/number preflight: 130 traditional-Chinese products touch missing targets, no Japanese matches. Another 41 Asian titles were outside the grammar. Exact denominator, rarity/printing, unique identity, NM condition, currency and live quote remain unproved; no import. |

CardTrader full eligible-target identity pass (12,630 entirely unpriced targets, before regular-set restriction): 4,840 nonregular sets; 4,149 missing/ambiguous blueprints; 2,875 without an exact Korean NM single-card offer; 742 missing/ambiguous expansions; 14 high asking prices held for review; 10 accepted candidates. The offer audit additionally includes catalogue types which the existing identity reader cannot establish, including trainers; those were not silently treated as verified Pokémon identities.

Primary endpoints:
- https://api.cardtrader.com/api/v2/expansions
- https://api.cardtrader.com/api/v2/blueprints/export
- https://api.cardtrader.com/api/v2/marketplace/products
- https://cardotaku.com/collections/pokemon/products.json
- https://cardotaku.com/en-fr/pages/condition-of-the-cards
- https://bgtcg.com/collections/single-card-pokemon-bao-ke-meng/products.json

## Implemented manual-run gate

Four current bulk entrypoints use a shared gate: CardTrader Korean, CardTrader Japanese, Japanese bulk retail, and Japanese image-print recovery. Their `--apply --missing-only` mode requires at least **1,000 distinct entirely unpriced cards** before calling any writer. Offer counts, duplicate card/variant rows and existing prices do not count. Immediately before the writer, the gate queries positive prices across every variant and blocks the whole manual batch on stale existing-price targets, duplicate targets, invalid/nonpositive/nonfinite amounts or provider errors. Existing transactional writer preservation and source-specific identity validation remain in place.

The report includes `import_gate` with the threshold, distinct new-card count and blocking reason. An attempted blocked manual apply saves its report and exits 2. Provider errors retain exit 1. Preview remains read-only. Weekly mode without `--missing-only` retains its existing refresh behavior and does not inherit the manual threshold. The four CLI gates are not a replacement for the low-level transaction guard; direct writer calls and historical importers must not be used to bypass the user's manual-run requirement.

## Validation

- 12 gate/CLI tests passed: 999/1,000 boundary, duplicate card/variant rows, a positive price on another variant, stale PRICE_FOUND snapshots, invalid amounts, provider failure, weekly small-batch behavior, and end-to-end CLI writer prevention/dispatch with mocked sources.
- Existing round-18 print-identity regression suite: 18 offline tests and 12 PostgreSQL checks passed.
- Live read-only gate applied to the ten saved CardTrader matches: `below_minimum_new_cards`, zero writer calls.
- All four changed entrypoints imported successfully; `git diff --check` passed.

No price/cache/history writes were made by this audit. Weekly automation was not changed. Provider inventories, raw exports, match reports and test logs are checkpointed under `/home/tv/cardyssey-backups/price-source-round21-20261011/`. No credentials are included in those files.
