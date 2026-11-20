# Missing-price recovery, round 22 — 2026-10-12

## Outcome

63 newly priced Korean catalogue entries: ten via the existing independent species matcher on 2026-10-11 and 53 via a new pinned native-art matcher, imported and verified on 2026-10-12. Every import targeted cards with no positive price on any variant. No existing price was refreshed by these manual transactions.

The user superseded the 1,000-card minimum and prioritized filling missing prices. Manual batches now accept any nonempty verified cohort. Existing-price, duplicate-card, invalid-amount and provider-failure protections remain. Empty batches remain blocked. Weekly work was not expanded or changed.

Current entirely unpriced physical catalogue entries: **33,545** (not variant count): DE 0, EN 15, JA 8,920, KO 17,101, zh-CN 0, zh-TW 7,509. The project is not fully priced.

## New identity route

`resolve-cardtrader-ko-art-prices.py` establishes unique ordinary Korean C/U prints from a pinned official Korean record, exact set/number/denominator/rarity, and two disjoint illustrated image patches. It verifies the selected blueprint against three different-number ordinary C/U blueprints in the same expansion. Native title and rules text are excluded from this cross-language artwork check; this route does not establish rare, full-art, reverse or other foil finishes. Only an explicit Korean NM/Mint in-stock single-card offer supplies the EUR amount; no Japanese price is copied.

Blueprint/metadata matching remains strict. A real counterexample with identical set/number but different artwork was observed and rejected. Image dimensions, shape, content and negative-control separation remain enforced. The matcher holds unresolved translated names without fabricating them; matching artwork provides independent identity evidence for trainers where the existing species-name matcher cannot apply.

The preview scanned 2,713 pinned missing targets. The prior complete 181-expansion inventory selected 38 relevant expansions, whose blueprints and Korean offers were fetched again live before this import. Of 196 live image checks, 53 passed, 95 failed image separation and 48 had insufficient full-card image dimensions. The 48 invalid image cases create no updates and are reported independently in `image_failures`; they do not block independently completed proofs. Provider/API failures still block the batch and mark the run incomplete. No image-quality thresholds were relaxed to suppress those errors.

Every accepted native/blueprint/control image SHA-256 and patch score was independently recomputed immediately before the import, and every official record was rechecked against the current pinned cache and catalogue. Evidence remains stored with each quote. Prices are live asking references, not sold-price claims.

## Import verification

- Ten-card transaction preserved all 95,406 pre-existing positive cache rows; 53-card transaction preserved all 95,416 positive rows present immediately before it.
- Both imports were atomic, checked expected write counts, created actual NORMAL generated variants and history, and replayed to zero writes.
- Every one of the 63 new cards passed authenticated API and Web price/language/variant checks.
- Tests: 13 manual gate/CLI cases, nine native-art identity/image/error-isolation cases, and 18 existing print-identity regression cases passed (40 total).
- `git diff --check` passed. Unrelated user files were not included in the commit.

Backups/evidence: `/home/tv/cardyssey-backups/price-round22-20261011/`. The full source exports from round 21 remain in `/home/tv/cardyssey-backups/price-source-round21-20261011/`. No credentials are stored in these checkpoints.

## Remaining limits

The majority of Korean misses do not currently have qualifying, unambiguous quotes. Rarity taxonomy differences, duplicate native prints, unavailable stock and incomplete image evidence remain held. Japanese and traditional-Chinese retail candidates from the previous source audit still require exact printing, live condition and quote validation; stock/product counts are not imported prices. BGTCG live product pages tested here did not establish NM condition, so its 130 preliminary traditional-Chinese matches were not imported.
