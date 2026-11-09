# Cardmarket: confirmed manual link feedback loop

In admin `/admin/prices` a human may paste an EXACT Cardmarket singles URL or an official `?idProduct=...` redirect link.

1. `POST /api/admin/cardmarket-manual-product` (`action=preview`), founder-only: create a separate tab in the persistent Edge Cardmarket profile. This tab does not reuse or navigate the background scanner's tab. Extract `input[name=idProduct]`, canonical singles URL, visible heading and breadcrumbs; cross-check ID against the official product catalog and show official price guide. Retain the preview in a private, random-token file for 15 minutes; **write no mapping or price at this stage**. Return an explicit error if Cloudflare blocks reading.
2. Human confirms exact set + number + artwork + language + print including holo/reverse and edition, plus an additional checkbox when the old crosswalk conflicts or the candidate is new. `action=confirm` atomically updates the existing admin review and source route. A conflicting existing verified product/provider is left untouched and the transaction is aborted. Existing price cache remains untouched.
3. The confirmed product ID and canonical URL are added to the browser queue and a `manual_scan_requested_at` timestamp is recorded, putting this exact card/print before routine browser cases on the next run. Only then may the scanner request explicitly filtered NM / language / edition / foil offers. A price is published by the existing gated importer only when the full filtered market and exact human-confirmed route are present; a public guide price in the preview is **not** the language-specific asking median.
4. One correction creates one `cardmarket_manual_identity_examples` row with old candidate IDs, exact confirmed URL and discrepancy details. The catalog builder explicitly recognizes previously verified ID+URL mappings on this exact print and does not re-ask the same question after subsequent catalog refreshes. Generalized set/print mappings are intentionally not inferred from a single example.
5. Cloudflare: the Edge profile is reused; the normal challenge is awaited without solving or bypassing it, then the collector resumes automatically on real clearance. The 15-minute watchdog observes a blocked session and requests a single restart when it becomes available. If still blocked, it does **not** publish guesses or fake 'not found' records.

## 2026-11-09: exact card number/variant ID is mandatory

The official Cardmarket singles catalog contains product IDs and expansion IDs,
but **not** a trustworthy machine-readable collector number. A name-only search
in a matching expansion must never be interpreted as an exact card identity.
For example, Undaunted Houndoom `hgss3-5` (5/90) and `hgss3-82` (82/90)
were mistakenly assigned the same three candidates by card-name aggregation.
The Cardyssey catalog already carries `cardmarketProductId` inside **each
individual physical variant**, and the queue exporter now preserves that exact
ID instead of unioning all name matches. For Houndoom 5 those are `279258` and
`371567` (different variants); for Houndoom 82 it is `279335`.

High-confidence Cardmarket expansion mapping now uses votes from at least five
distinct card identities with official product IDs, rather than fuzzy name
lists. Any variant with a physical ID is verified against the official
product's expansion, not assigned a price or foil by association. When two
collector numbers of the same set share the same species/name, the name-only
candidate table returns `SAME_NAME_DIFFERENT_NUMBERS_REQUIRE_VARIANT_ID` and
**does not** pretend that every same-name product belongs to every number.
Manual product confirmations and prices are never overwritten. Previously
merged open review candidates and conflicting official-name SOURCE_ONLY routes
are reconciled only when the matching official product expansion corroborates
the exact variant ID.

The admin default manual-review list shows only `MANUAL_COMPARISON_READY` with
a product-version comparison; all other automatic recheck cases remain
accessible through the explicit 'Alle automatischen Nachprüfungen anzeigen'
mode, where the UI makes clear that the user does not have to assign a set.
The variant-recheck data refreshes every two minutes and the browser page
reloads the review summary every 30 seconds.

## Verified card is not a verified print: Quappo BS13 regression

For `base1-13` Quappo/Poliwrath, the official Cardmarket product catalog
lists **273708** (V1) and **660215** (V2) in expansion 1523, the confirmed
Base Set. Cardyssey's special physical print `Copyright 1999–2000` has no
specific `cardmarketProductId`. The older scanner incorrectly emitted
`PRODUCT_ID_NOT_IN_VERIFIED_SET` even when Cardmarket resolved to V1 BS13.
It was conflating a missing *variant* ID with a missing *card in its set*.

The queue now exports `set_card_candidate_ids` separately from the exact
`cardmarket_ids`; the former are official candidate products for the given
card, not a verified print. The scanner validates (1) the confirmed set URL
slug where a trusted guard exists, (2) the collector number from the **final**
URL suffix (`-BS13`, never the preceding `-V1`), and (3) membership in the
card's or variant's product candidate IDs. If correct card/set are found but
print attribution is missing, it emits
`PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED`, with `identity_confirmed=false`.
No language-specific price or exact print mapping can be published from that
status. With no card-number evidence it remains an unresolved product result.

Card-level candidates are shared in DE and EN from the independently mapped
DE card identity, not inferred from the locale. Worklist/review records for
missing-variant IDs retain those *candidate IDs* with classification
`CARD_IN_VERIFIED_SET_PRINT_NOT_IDENTIFIED_SPECIAL_PRINT`, rather than falsely
showing zero possible products. The 1999–2000 print is still pending a real
version/edition comparison. This change is durable across the next catalog
export and the next two-minute review refresh. The exact Quappo variant has
been queued for targeted retest in both DE and EN once the saved Cardmarket
session is allowed by the provider again.
