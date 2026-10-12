# Missing-price bulk preflight — 2026-10-11

> Update 2026-10-12: The user superseded the 1,000-card manual minimum. Nonempty verified missing-price cohorts may now be imported; see price-recovery-round22-2026-10-12.md. This document records the earlier audit.
## Manual run requirement

The user now requires at least 1,000 new, evidenced prices per manual run. Do not start another small import merely because a few offers are available. Manual recovery still targets only cards with no positive price on any variant. Candidate checks, existing-price refreshes, copied duplicate catalogue references and fabricated estimates do not count as independent new price discoveries. Weekly authorized refresh remains enabled; this threshold applies to manual recovery runs.

## New source checks

No pricing import was run during this preflight. These new sources did not establish a verified 1,000-price block:

| Source | Observed scope | Result |
| --- | --- | --- |
| Sammelsucht | Complete single-card collection: 2,042 products, 1,161 with an available variant | Title/tag language mentions: 1,432 DE, 50 EN, 181 JA, 12 KO, 3 Chinese. Asian offers still require exact missing-card, printing, condition and live quote verification. The total stock number is not an Asian price-recovery count. |
| JustPlay'nCards | Complete Japanese singles collection: 40 products (first page shorter than 250) | Explicit Japanese/Near Mint examples exist, but the scope is too small for the requested block. No prices imported. |
| Starz Collectibles | Complete Japanese singles collection: four products | No available variant on any of the four; one listing is an AR set bundle. No eligible stock block. |
| Zardo | Public Korean category filtered to NM | One displayed product and no pagination: Bulbasaur SV2a 001/165, non-holo, EUR 0.21. No large block. |
| Cardpick | Public homepage and data description | Explicitly an English-card TCGplayer/Cardmarket reference in KRW, not Korean-language card prices. Do not transfer onto Korean catalogue cards. |
| Pokard | Public homepage | Displays 293 Korean catalogue cards, not 1,000 priced Korean targets. Ranking mixes graded/ungraded and displayed observation dates are 2026-07-10; no current bulk import established. |
| PokaHub | Direct public catalogue request | Retrieval failed with a URL error; search catalogue count is not verified quote coverage. No inferred prices or access workaround. |

Previously assessed CardRush is already held after direct HTTP 403. A new search result is not authorization to bypass the restriction or proof of usable live quotes. Yuyu-tei and Fullcomp condition guidance likewise does not establish universal NM for their ordinary inventory.

## What remains unresolved

The next manual import needs a new sufficiently large source or a rigorously proved identity/printing route yielding at least 1,000 independent new quotes. Raising a request/card cap does not create missing offers. Small candidate pools may be retained for a later combined batch, but this preflight does not claim that 1,000 quotes are ready or that these sources have no prices anywhere.

Runtime source checkpoints: /tmp/cardyssey-round20-*-inventory.json and logs. Price/cache rows and existing weekly refresh code were unchanged.

Primary sources:
- https://sammelsucht-shop.de/collections/einzelkarten/products.json
- https://www.justplayingcards.shop/collections/japanese-singles/products.json
- https://starzcollectibles.de/collections/pokemon-einzelkarten-japanisch/products.json
- https://www.zardo.cards/en/korean-cards/p-condition/nm
- https://cardpick.kr/
- https://pokard.io/
- https://pokahub.com/ko/cards
