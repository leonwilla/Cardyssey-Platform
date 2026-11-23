# Free price sources — 2026-10-10

Requested languages: German, English, Japanese, Korean, Simplified Chinese, Traditional Chinese. No subscription purchased. Manual recovery only fills cards with no positive cached price; the previously requested weekly refresh remains enabled.

## Practical findings

| Source | Free access | Relevant language price coverage | Decision |
|---|---|---|---|
| CardTrader current offers | Existing authenticated API, no new subscription | Explicit language on individual offers. DE/EN/JA/KO already supported by our verified adapters; Chinese language/printing distinction must be proved per product | Keep and extend exact identities. Offers are asking prices, not sales |
| TCGCSV | Public JSON/CSV, no key | Current category list contains Pokemon (3) and Pokemon Japan (85); no separate Korean/Chinese category | New category-85 adapter joins exact Japanese TCGplayer IDs from verified CardTrader blueprints |
| PokéWallet | 100 requests/hour, 1,000/day; account/key required | EN and JA documented; CBB3C Chinese product example exists. DE image availability does not prove German-specific prices. KO and traditional Chinese pricing not confirmed | Best free API candidate for evaluation with a free key; no prices imported without responses |
| TCGdex | Free, no key | Metadata for DE/EN/JA/zh-TW. KO and zh-CN still advertised as coming soon | Existing catalogue source; marketplace aggregates cannot automatically be assigned to every translated language |
| Master Setter | 1,000 requests/month, free key | Metadata for all six required languages | No prices yet; advertised future paid add-on. Useful for identity, not closing price gaps |
| True Unicorn | Public retail products | Two available Korean singles found; one already priced | New exact NM single adapter. USD currency, stock and SKU checked across collection/detail/Ajax |
| HKTCG | Public retailer | EN, zh-CN, zh-TW collections explicitly separate | Continue exact native title/set/number/variant matching; sealed boxes are excluded |
| SimplifiedTCG | Public guide without account; longer history paid | Separate EN, JA and zh-CN card lines; Chinese completed-sale guide | Promising additional research source. No automated API or reuse entitlement verified; no unverified imports |
| JustTCG | 1,000 calls/month, 100/day | Filters accept all six languages; actual populated price coverage needs response checks | Free tier noncommercial only. No production import on free plan |
| TCG API (tcgapi.dev) | 100 calls/day | TCGplayer data; six-language price completeness not established | Free/Hobby/Starter noncommercial; commercial Pro $49.99. Outside present budget preference |
| pokemontcgapi.com | One-time 800-credit/30-day trial | Free current quotes English only; CN metadata explicitly has no price rows | Not a recurring free Asian price solution |
| PikaQian | 500 calls/month free metadata | zh-CN | Raw API prices start at Hobby $20; Pro marketed for commercial use. Free website guide is a different access path |
| TCGGraph | Starts $29/month | DE/EN/JA/KO language-specific offers documented, growing coverage | Cheaper paid fallback only; not activated |
| Scrydex | Paid plans | EN/JA; KO/Chinese advertised on roadmap | Not a verified solution for all six languages |

## Price identity and evidence

A localized card name or image does not establish a localized quote. Cardmarket product-wide trend/low figures can combine languages and conditions. CardTrader's kr/jp flags, TCGCSV category 85, and explicit Chinese retailer version are actual price identity evidence.

The Japanese TCGCSV recovery requires a unique pinned official printing, matching native/species identity, exact booster expansion, collector number/denominator/rarity, a unique CardTrader blueprint and its exact Japanese TCGplayer product ID. Product names may carry an exact numeric suffix; a different suffix is rejected. Ordinary Normal/Holofoil quote selection stays strict; reverse, special, edition and ambiguous products are held. Quotes are labelled MARKET_ESTIMATE, stock unknown and aggregate-market condition, never live NM offers. Existing 0.92 NM/base representation is retained for API compatibility.

Missing-only filtering happens before provider requests. Transactional writers additionally block any card with a positive cached price, including another variant or an inconsistent status. Snapshot guards and conflict guards preserve concurrent newer prices. Weekly runs keep their existing refresh behavior.

## Primary references

- https://www.cardtrader.com/en-US/docs/api/full/reference
- https://tcgcsv.com/ and https://tcgcsv.com/tcgplayer/categories
- https://pokewallet.io/pricing
- https://pokewallet.io/api-docs
- https://pokewallet.io/terms-conditions
- https://tcgdex.dev/ and https://tcgdex.dev/markets-prices
- https://api.master-setter.com/
- https://trueunicorntcg.com/products/whatnot-singles-81-160
- https://www.hktcg.com/collections/pokemon-cn
- https://www.hktcg.com/collections/pokemon-tc
- https://www.hktcg.com/collections/pokemon-en
- https://simplifiedtcg.com/
- https://justtcg.com/pricing and https://justtcg.com/docs/api/cards-v2
- https://tcgapi.dev/pricing/
- https://pokemontcgapi.com/free-api-key and https://pokemontcgapi.com/coverage
- https://pikaqian.com/pricing
- https://tcggraph.com/pricing and https://tcggraph.com/docs/prices
- https://scrydex.com/faq

Provider claims are distinguished from verified live imports; no claim that a single free provider currently fills every language and variant.
