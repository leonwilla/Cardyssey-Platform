# Exact Korean Near Mint retail recovery (2026-10-09)

## Applied

- 28 previously unpriced Korean official print entries now have a documented ordinary/default variant, exact retail offer and price history. No existing card IDs, images or collection references were replaced.
- New free source: Mewtwo.eu Korean singles. The bounded 33-page category discovery found 289 products, of which 35 were marked in stock. Exact product checks accepted 28; five lacked an eligible unresolved catalogue target and two were out of stock on the detail page.
- Require Korean category/title, exact set and collector number, unique official catalogue identity, independent English/German/Korean species agreement, single explicit Near Mint condition option and agreement between stock quantity and structured availability.
- Price currency must be EUR in all three metadata sources. The gross price including VAT must agree between product metadata, Offer metadata and the condition option. The retailer's analytics price excludes VAT and is not used. Public JavaScript is never executed; only bounded JSON and HTML metadata are parsed.
- Asking prices remain labelled ASKING with original offer URL, condition, tax basis and observation time. They are not completed sales.
- Atomic catalogue/cache/history writes preserve concurrent newer prices. A repeat of the applied evidence wrote zero additional variants, prices or history.
- Explicitly allow the second Korean source in shared official-card details and weekly supplemental-import identity checks. Unchanged identities retain proof; changed set/number/name/image identities invalidate only derived variants and source-owned effective prices. Existing histories and unrelated providers remain untouched.
- Refresh weekly with a 240-second hard limit; keep the report as a workflow artifact for 14 days.

## Validation

- Ten new offline source tests pass, including gross-versus-net prices, stock disagreement, wrong currency/language/number/species, printing/condition ambiguity, metadata scope and source allowlists.
- Existing 37 price regression tests pass.
- The four transactional PostgreSQL fixtures pass for each of the two Korean sources, including actual supplemental importer preservation/invalidation, atomicity/idempotence and concurrent-price protection.
- Backend Gradle test/installDist passed with the offline dependency cache; runtime deployed.
- All 28 detail/price pairs pass through the Android API; three detail/price pairs also pass through the Web proxy. Quotes retain exact language/variant matches and condition-correct ranges.
- Pre-write backup: /home/tv/cardyssey-backups/price-round5-20261009T150657Z. Applied evidence: /tmp/cardyssey-round5-mewtwo-applied.json.

## Coverage and manual checks

- Korean PRICE_FOUND: 398 to 426. Catalogue entries without variants: 19,613 to 19,585. This is still incomplete Korean catalogue coverage.
- Known unresolved variants remain 2,640 plus 27 deliberate release holds; this block recovered catalogue entries previously absent from that variant count.
- Test Korean SV1V-089 (Bombirdier/Adebom) at EUR 1.60, SV9-107 (Lycanroc/Wolwerock) at EUR 2.25 and SV1a-074 (Tropius) at EUR 1.60, condition Near Mint, in App and Web.

## Traditional Chinese read-only follow-up

- Enumerated 1,952 Players Club and 1,999 Beehive collections with bounded pagination, then checked additional Chinese deck/GO/anniversary collections using the existing strict matching logic.
- The expanded read-only probe produced no eligible price updates: 133 candidate offers were out of stock; 13 had name/printing disagreements; the remaining rejections included wrong set, ambiguous retailer variant or invalid price. This does not prove that no public price exists elsewhere.
- No Traditional Chinese prices or variant definitions were changed by this probe. The temporary report is /tmp/cardyssey-round5-zhtw-preview.json.
