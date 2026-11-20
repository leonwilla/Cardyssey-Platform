# Price recovery round 16 — 2026-10-11

Added **2,786 previously entirely unpriced Japanese physical catalogue entries**. No prior positive price was refreshed: all **91,496** positive cache rows retain their original card, language, variant, source, amount and timestamp.

## Coverage

Entirely unpriced physical catalogue entries remaining: **34,729**. This counts physical catalogue entries, not individual price variants.

| Language | Entirely unpriced entries |
| --- | ---: |
| de | 0 |
| en | 15 |
| ja | 10,036 |
| ko | 17,164 |
| zh-cn | 4 |
| zh-tw | 7,510 |

| New reference source | Cards |
| --- | ---: |
| WEB_HARERUYA_JP | 1,968 |
| WEB_TORECACAMP_JP | 818 |

## Large block and evidence

Read complete public collection inventories: 16,132 Hareruya products across SV, Sword/Shield and Sun/Moon; 7,050 TorecaCamp products across 70 relevant set collections. These are 23,182 provider records, not 23,182 distinct catalogue cards. Selected 4,137 eligible pinned official identities and 2,786 candidate cards. Verified every selected quote live; 2,786 passed, 0 provider errors.

The 50-card interval is a progress checkpoint only. The full candidate block is processed without an arbitrary 50/300-card limit. Global request pacing and provider Retry-After backoff protect the public services. A remote finalizer imports and verifies the completed block after a clean preview.

The matcher requires the complete native Japanese name, printed set code, card number and denominator, one physical catalogue identity, exact pinned official URL/ID, source revision, image and raw source record. Modern trainer/deck cards whose official rarity is absent remain rarity-less. It does not manufacture rarity or variant distinctions. Duplicate official identities at the same set/number, possible mirror/reverse prints, graded cards, sealed products, alternate editions and unproved older first editions are held.

Each price is an in-stock single-card retail asking reference in retailer condition A, not a sold-price aggregate or a guarantee that retailer condition A equals a grading standard. Hareruya must explicitly state that unmarked condition is A; TorecaCamp must expose the exact A option. Feed and live Ajax must agree on print, product, SKU, stock and price. Quantity rules must prove unit purchasing; subscriptions and quantity discounts are rejected.

JPY currency is verified through cart.js in the same anonymous session before and after processing, as required by Shopify’s Ajax monetary-value contract. JPY Ajax prices contain two trailing zeroes; conversion checks the feed amount against Ajax integer units. References record original JPY, dated Frankfurter JPY/EUR conversion, source URL, official identity and observation timestamp. Single asking references exceeding EUR 100 remain under review.

Primary contracts:

- https://shopify.dev/docs/api/ajax/reference/product
- https://shopify.dev/docs/api/liquid/objects/product
- https://www.hareruya2.com/pages/card-condition
- https://www.cardtrader.com/en-US/docs/api/full/reference

## Other language checks

CardTrader reviewed 7,790 eligible Korean targets across 103 expansions with no new verified match and no provider errors. English review completed for 13 cards / 15 variants with no additional verified price. No existing price or deferral was rewritten by these previews.

CardTrader inventory quantity is now distinguished from bundle size. Multiple stock units are accepted only when explicit bundle_size=1 proves per-card pricing; unknown multi-unit bundles, inconsistent counts and non-unit bundles remain held.

TCGBOX’s public guide describes both NM and LP inventory; inspected product listings do not prove an unmarked card is NM. These quotes remain held. PriceCharting Korean set pages returned HTTP 403 from the authorized runtime; no access bypass was attempted. Pokémon TCG API’s public documentation explicitly excludes Korean. No paid source was purchased.

## Preservation, deployment and weekly run

The backend and supplemental importer preserve the new source-owned Japanese variant markers on unchanged official identities. Actual print identity changes invalidate derived prices for re-verification. Manual missing-only recovery checks for a positive price on any variant both before provider work and atomically when writing. Replay writes zero variants, prices and history rows.

Backend tests/installDist passed, the runtime image was rebuilt and the API redeployed before import. A pricing backup was taken before writes. The weekly workflow includes this bulk reader without missing-only, allowing the previously authorized weekly refresh. Weekly collection discovery also includes the observed XY numbered-promo collection and explicit TorecaCamp XY/SV promo handles when eligible official targets exist. The current manual block used the three modern Hareruya series and 70 TorecaCamp scopes described above. Reader timeout is 65 minutes; total job budget is 180 minutes to accommodate it alongside existing sources. The schedule remains Sunday 04:17 UTC.

## Validation

- All 15 offline test scripts from the weekly workflow passed; round 16 contains 27 cases.
- 24 live PostgreSQL JA/KO missing-only import and positive-price preservation cases passed.
- Three additional live PostgreSQL English missing-only cases prove creation of absent prices and preservation of positive target/other-variant rows, including stale statuses.
- Nine existing English PostgreSQL replay, identity-change and deferral cases passed.
- Verified all 2,786 newly written database prices against the validated source and exact amount; all 91,496 pre-existing positive rows remained exactly equal as decoded records.
- API and web price/catalogue verification passed for 162 representatives covering every source/set/missing-rarity cohort and price extremes, including source, EUR conversion, range bounds, exact language/variant and generated variant.
- Coverage audit completed after import.
