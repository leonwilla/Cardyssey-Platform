# German price refresh and NM-assumption policy — 2026-11-05

## User-requested rule and boundaries

- Only **German** offers with **no condition stated** may be treated as **Near Mint assumed**. This is *not a verified NM declaration*; retain the assumption in evidence.
- Explicit non-NM (`Good`, `Played`, `Excellent`, `Lightly Played`, `Damaged`, etc.) is rejected, not converted to NM.
- Unknown/unrecognized condition labels are not automatically NM. No condition fallback to non-German languages in this rollout.
- Product identity remains exact: language, card, print, edition, foil/reverse, stamp, number. No invented card identity, no automatic cross-language valuation.
- Cardmarket's public **price-guide trend/average is an aggregate**, not an individually language- and NM-filtered retail listing. *Do not claim that it is a verified German NM offer.* The explicit NM-default rule applies only to actual listing condition fields (e.g. CardTrader), not to a published aggregate.

## Source changes

- `scripts/market_condition_policy.py`: reusable missing-condition/explicit-grade classifier; used by `scripts/refresh-cardtrader-price-cache.py`. Tracks `condition assumed NM for N listings` in the source evidence. Explicit inferior grades excluded. CardTrader listing filtering already enforced the exact language and foil; this is preserved.
- `scripts/refresh-cardtrader-price-cache.py --language de`: restrict processing to German. **0 eligible German targets** during this run; no new CardTrader quotes imported. The missing-condition path is unit-tested, but not yet verified against a real eligible German offer.
- `scripts/refresh-cardmarket-price-cache.py --language de`: allow re-evaluating German TCGplayer-derived cached variants for a matched Cardmarket product; preserve existing TCGplayer identity, but do not present the USD/US market value as a German price. Continue using validated product IDs or high-confidence set+name matches; no unsupported variant conflation. `--dry-run` supported.
- The other price scripts' explicit condition filters (especially Korean/Japanese specialist feeds) are **left intact** because this rollout is DE only. Existing eBay sold-only/NM-default rules remain intact. The bulk market policy remains independent of eBay.

## Actual run on authorized Tiny

- Cardmarket public singles catalog: **75,105 products**. Price guide: **80,390 price entries**, guide created `2026-11-05T02:50:00+0100`.
- Round 1 `--language de` dry run and apply: 319 candidate quotes, of which 305 were new eligible Cardmarket values; 14 updates were to already priced Cardmarket rows.
- Round 2 expands German search to existing verified TCGplayer routes: 2,091 eligible cache rows scanned; **631** candidate refreshes (including the 319 previously refreshed), with 319 existing + 312 new; 1,460 unresolved candidates in the Cardmarket review output (978 with tentative search matches).
- Daily source-policy sync rerun after both applies. **German missing prices fell from 3,330 to 2,713 (-617)**. English missing stayed **2,975**.
- Of the German 2,713 unresolved, **1,253 are Pokémon TCG Pocket**, which must not be valued as physical Cardmarket cards. **1,460 physical variants** remain without eligible pricing.
- The 1,460 unresolved physical variants need further correct source mapping, edition/language verification or specialized price evidence. No guessed or zero-valued prices were added.

## Generated reports (temporary outside Git)

- `/tmp/cardyssey-de-cardmarket-dryrun.log`
- `/tmp/cardyssey-de-cardmarket-targets.log`
- `/tmp/cardyssey-de-cardmarket-final-apply.log`
- `/tmp/cardyssey-de-cardmarket-final-review.json`
- `/tmp/cardyssey-de-policy-sync-final.log`

These reports are disposable diagnostic outputs. Do not commit huge raw provider data. For current counts, use `python3 scripts/price_source_coverage.py`.

## Safe rollback

- Git source changes are reversible by reverting the subsequent commit. Do not delete the production cache or price history wholesale.
- Each successful Cardmarket import records source `CARDMARKET_OFFICIAL` and an exact product/guide key and the acquisition date in `tcg_price_cache` and `tcg_price_history`. If individual mappings prove wrong, investigate and correct by card+language+variant, preserving historic audit records.
- No new Docker service or long-running daemon was installed.
