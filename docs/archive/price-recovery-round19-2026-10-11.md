# Price recovery round 19 — 2026-10-11

## Result

Eight additional Japanese catalogue entries now have verified live retail references: six ordinary prints and two generic mirror/reverse prints. No named Pokéball or Masterball foil was inferred. All 95,398 positive rows present at the manual transaction start were preserved unchanged. Entirely unpriced catalogue entries remaining: 33,608 (DE 0, EN 15, JA 8,920, KO 17,164, zh-CN 0, zh-TW 7,509). These are catalogue-entry counts, including duplicate identities.

## Full-card matching extension

Some official holographic renders differ mainly in the illustration; the lower text body can be identical or less contrasting. Visually reviewed SV4a ordinary/mirror and SVAW/SVEL foil peers prove this case. The reader continues to require a close full-frame AND lower-body match (mean absolute RGB error at most 2.5). Every competing pinned print must differ by at least 8 in the full frame and four times the selected print's error.

Local separation now requires either the established lower-body contrast (at least 8 and four times best body error), or a fixed illustration crop (16,41,201,147), with selected illustration error at most 3.5 and rival illustration contrast at least 16 and four times the selected illustration error. This does not allow artwork-only identity or ignore close competitors. The full native name, Japanese language, set, collector number, denominator, pinned official revision, image identity and existing-variant guards remain required. Recorded evidence includes every rival score, image hashes, source URLs, crop bounds and thresholds.

A complete fresh relevant TorecaCamp inventory contained 4,071 products. Existing image checkpoints prefiltered that inventory into 181 potential follow-ups: 173 failed current feed stock/condition checks; the eight remaining offers passed independently re-fetched live product, currency, stock, quantity, price and full-image checks. This round did not claim to re-fetch all 4,071 product-detail images. The weekly job already invokes this reader directly with fresh complete inventories, so the extension applies automatically to future recovery and authorized source-owned weekly refreshes.

## Validation

- 18 offline image/metadata/quote guard tests passed, including illustration thresholds, the fourfold rival ratio, every competing peer, wrong body and poor/identical matches.
- 12 real PostgreSQL variant creation, other-positive-price preservation, replay and authorized refresh cases passed.
- Eight exact DB prices and actual variants verified; replay wrote zero variants, prices or history.
- API and Web verification passed for 11 cohort checks covering all eight cards, including ordinary/reverse and price extremes.
- Short atomic missing-only transaction locked the cache, verified expected batch counts and compared all transaction-local positive rows before/after.
- Backup: /home/tv/cardyssey-backups/price-round19-20261011/pricing.dump.
- Runtime reports: /tmp/cardyssey-round19-preview.json, /tmp/cardyssey-round19-applied.json, /tmp/cardyssey-round19-result.json.

## Additional free Korean source survey

The complete public Pokemon collections of Dojo TCG and Three for One Trading were retrieved with duplicate/pagination guards. Dojo contained 176 products and four explicit Korean NM singles. Three for One contained 460 products and five Korean cards, four graded and one NM single. None was imported in this round.

The five ungraded offers do not provide a thousand-card recovery block. Dojo's Keldeo CP5 014/036 is labelled rare in the retailer description while the current official catalogue has rarity U; hold for identity review. The Mew S12a 183/172 listing has no corresponding current catalogue target in the exact query. The two Mega listings (M1S 087/063 and M1L 090/063) are candidate follow-ups requiring independent print/species or trainer identity checks and a maintained source adapter. Three for One's Umbreon SV8a 217 is EUR 250 and remains a high-price review candidate. No graded price was applied to an ungraded card, and no missing denominator or condition was assumed.

Primary sources:
- https://torecacamp-pokemon.com/
- https://www.pokemon-card.com/card-search/
- https://dojotcg.com/collections/cartes-pokemon/products.json
- https://shop.threeforonetrading.com/collections/pokemon-tcg/products.json
- https://shopify.dev/docs/api/ajax/reference/product
