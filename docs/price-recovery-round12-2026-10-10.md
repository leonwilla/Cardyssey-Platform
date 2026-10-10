# Price recovery round 12 — 2026-10-10

## Live result

- Korean: 79 newly priced catalogue entries (five current-market matches from the existing resolver and 74 from independently verified identities with a missing imported German species field).
- 2,188 existing Korean prices refreshed.
- One atomic Korean batch wrote 79 variants, 2,267 cache prices and 2,267 history points. Replaying the same snapshot wrote zero rows.
- The 15 wholly unpriced English catalogue entries, comprising 17 variants, were reviewed individually. No acceptable new English price was found; no substitutes were imported.
- English: 17 source-specific review statuses saved, with no price or history writes. Three entries never issued in English are held without an automatic availability retry; the two Mewtwo variants are held until the November 2026 release window; twelve remaining variants have a seven-day retry. A temporary source deferral does not assert that no price exists anywhere.

Entirely unpriced catalogue entries: 37,677 → 37,598.
Entirely unpriced by language: de 0, en 15, ja 12,852, ko 17,217, zh-cn 4, zh-tw 7,510.
Missing-variant entries: 36,419 → 36,340. Partially priced entries remain 480.
Korean priced variants: 2,715 → 2,794.
Known NO_PRICE variants: 2,582; deferred NO_PUBLIC_PRICE variants: 44.

The 15 English entries remain in the wholly-unpriced count. Closing or deferring a review task is not the same as finding a price. Catalogue entries can include duplicates; retailer and marketplace references are asking prices rather than verified sales.

## English review

Raichu BW78 was planned but not issued in English.
Beginning Door DP54 and Ultimate Zone DP55 promotional prints were French-only; ordinary English Arceus prints are different products.
Mewtwo MEP104 standard and jumbo are associated with the 30th Celebration Figure Collection, announced for November 2026.

The other checked cards are six Bisharp/Wigglytuff Trainer Kit singles and five Nintendo promo entries (six variants including Jumbo Winner Marshtomp).
The exact Trainer Kit and standard Nintendo TCGplayer products exist, but the current free TCGCSV feed has no relevant price rows. Current exact English marketplace offers are absent or fail condition checks.
The sole Trainer Kit Metal Energy 18 offer was Moderately Played at an extreme price, so it was rejected.
The catalogued Jumbo Winner variant has no compatible explicitly English oversized provider identity; no normal-size price was substituted.
Additional public retail samples for Bidoof, Metal Energy 3 and Torchic were out of stock.

New scripts/review-english-price-leftovers.py rechecks reviewed identities and source availability weekly. Exact current quotes can be imported atomically when they appear. It preserves concurrent catalogue edits and successful quotes, stores source-specific evidence and retains the original price-cache update timestamp for deferrals. After the Mewtwo release window the automatic premature-release deferral ends and fresh product identity must be verified.

References:
- https://bulbapedia.bulbagarden.net/wiki/Raichu_(BW_Promo_78)
- https://bulbapedia.bulbagarden.net/wiki/Beginning_Door_(Arceus_82)
- https://bulbapedia.bulbagarden.net/wiki/Ultimate_Zone_(Arceus_91)
- https://www.pokemon.com/uk/news/pokemon-tcg-30th-celebration-product-showcase
- https://tcgcsv.com/tcgplayer/3/1533/products
- https://tcgcsv.com/tcgplayer/3/1533/prices
- https://tcgcsv.com/tcgplayer/3/1423/products
- https://tcgcsv.com/tcgplayer/3/1423/prices

## Korean source expansion

Existing resolver: 9,885 candidates across 103 expansions; 2,193 qualifying matches (five new).
Pinned-source pass: 229 independently verified additional Pokemon candidates across 33 expansions; 74 qualifying matches, all new.
Both completed with no source errors.

New ko-pinned-species-targets.py reads parsed Korean records from the already imported type-null/PTCG-database cache at revision 18e0de2feb7a35ebe4296ede0ba6cc768961489b.
It requires one unique official identity and matching imported source revision, official source URL/hash/ko_id/language, native name, image, exact set, printed number, rarity and positive individual printed denominator.
The raw Pokemon type or recognized evolution type must also have positive integer HP and nonempty attacks.
Independent PokeAPI Korean/English/German species names must identify one longest species. A trainer containing a Pokemon's name is rejected.
The resulting derived German species is used only for matching and is not written into imported catalogue metadata.
The existing exact Korean marketplace checks and atomic catalogue/cache/history writer remain in use.
Source metadata is explicitly identified as a pinned parsed official record; only the marketplace offer is freshly observed.

This additional target path is integrated into the existing weekly Korean resolver. No paid subscription was activated.

## Paid-source findings

Coverage needs to be tested on unresolved exact cards before subscribing; a multilingual catalogue or a language filter alone does not prove usable Korean/Chinese price coverage.

- CardTrader: the existing API supplies explicit Japanese/Korean current offers. More credentials or a subscription would not create offers that are absent.
- Master Setter: lists Korean/Japanese/Chinese catalogue coverage and 1,000 free requests per month, but explicitly has no price data yet. It does not presently solve the price backlog.
  https://api.master-setter.com/
- PkmnPrices Pro: advertised USD 14.99/month, 20,000 credits/day and commercial use; priced catalogue languages advertised as English/Japanese/German. Korean/Chinese pricing is not established by that plan.
  https://www.pkmnprices.com/pricing
  https://www.pkmnprices.com/docs/cards
- cardmarketapi.com: independent third-party service, not Cardmarket's official API. Advertises listing language filters including Korean and both Chinese locales. Docs list a three-day trial at ten requests/day, then USD 49.99/month for 2,000 requests/day, USD 99.99 for 6,000/day, USD 199.99 for 20,000/day. The homepage also calls ten/day a free tier, so the trial duration should be verified before signup.
  Actual Asian product/variant match rate remains untested without an account/key.
  https://www.cardmarketapi.com/docs
  https://www.cardmarketapi.com/

We can implement our own provider adapters, exact matching, caching, history and scheduled refresh. Purchasing an API does not automatically grant perpetual post-subscription access or redistribution rights for its underlying data. No proprietary source code needs to be copied.

## Validation and weekly operation

141 offline checks passed across ten suites.
Nine English PostgreSQL scenarios passed: deferral, price/history write, replay and preservation of newer prices, timestamps and changed catalogue identities.
Existing Korean/Japanese atomic and official-reimport PostgreSQL checks passed, as did the card-count rollback fixture.
All 2,267 Korean API detail/price pairs passed with Web sample pairs: exact source, language, variant, NM EUR amount and history ranges.
All 17 deferred English variants returned no invented API price.
An initial smoke assertion assumed low/high equalled the current price; existing refreshed cards correctly have a historical range. The assertion was corrected to require the current quote to lie inside that range, and the full check passed.
No backend code changed, so no API rebuild was required.

Weekly workflow includes the new English review and regression suite, and saves its evidence artifact for 14 days. Existing weekly Korean step automatically includes the pinned-species targets.

Backup: /home/tv/cardyssey-backups/price-round12-20261010/pricing.dump.
Evidence: /tmp/cardyssey-round12-en-applied.json, /tmp/cardyssey-round12-ko-applied.json.
Final audit: /tmp/cardyssey-round12-audit.log.
Smoke evidence: /tmp/cardyssey-round12-en-smoke.log and /tmp/cardyssey-round12-ko-smoke.log.
