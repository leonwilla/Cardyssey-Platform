# Cardyssey DE price priority / 7-day provider refresh (2026-11-05)

## Current database findings
- 31,359 German cache rows had `PRICE_FOUND`; 27 had `NO_PRICE` when this work began.
- The 1,460 unresolved Cardmarket variant worklist was not equivalent to 1,460 cards without prices: 1,300 already had `TCGCSV_TCGPLAYER` prices and 133 `TCGDEX_TCGPLAYER` prices.
- The 27 outstanding variants include special physical prints: World Championship 2007/2008/2009 Tropical Wind staff/placement stamps, special Pikachu promos, Wizard World stamped cards, holo/foil/stamp promos and artist-stamped cards. A generic product's asking price cannot safely stand in for a distinctly stamped copy.
- A legacy unverified print needs evidence for the **specific** printed finish/edition/stamp; this requirement is separate from whether the matching normal Cardmarket product has a price.

## Execution order
The queue was rebuilt using actual DB prices by `scripts/prioritize-cardmarket-scan-queue.py`:

1. Cache row missing or non-positive price: 27 first.
2. Existing price at least EUR 20: high-value comparison.
3. Special prints and rare cards.
4. Other already priced cards.

Sorting preserves all 1,460 unique (card ID, physical variant ID) records, and previously completed entries are not needlessly rescanned. Collector reads the prioritized queue from Windows local `Cardyssey/CardmarketCollector/queue.csv`.

## Stable identifiers and current fallback

The browser stores `product_id`, product link and a filtered German near-mint **asking-price sample** for candidate matches. `import-cardmarket-browser-observations.py` imports verified **catalogue product ID alignment** into `price_review_cases`, and stores the canonical Cardmarket URL + numeric product ID in `price_source_routing` with verification state `SOURCE_ONLY`, `refresh_days=7`, and `fallback_provider=TCGCSV_TCGPLAYER`. This does **not** certify a special stamp, edition or finish.

The collector checks for a previously confirmed candidate URL and ID on a repeat scan and reuses that canonical product page instead of performing a name search. Product URLs are restricted to official HTTPS Cardmarket Pokémon single-product pages; identity is rechecked from the page. Filter parameters, credentials and cookies are not persisted in the product URL.

Existing prices from TCGplayer/TCGCSV and TCGdex remain untouched if Cardmarket only yields partial listings or ambiguous identities. eBay completed-sale evidence remains a separate source, not interchangeable with Cardmarket asking prices. The official Cardmarket price guide is a separate unfiltered aggregate source.

## Scheduling

- Windows Startup shortcut resumes the authenticated browser collector.
- Windows scheduled task `Cardyssey Cardmarket Daily Refresh` launches the collector at 04:35 if there is no active collector, using interactive current-user credentials. The collector only revisits records whose last successful check is older than 7 days; errors may retry earlier.
- Tiny cron every 15 minutes imports incremental browser evidence without modifying production prices.
- Tiny cron Sunday 04:10 performs a fresh **official Cardmarket price guide** refresh and refreshes existing verified Cardmarket price rows. The guide is **not** German NM offer-specific.
- Source candidate links stored under `price_source_routing` allow later per-print checks without repeated product discovery.

No automatic elevation of low-confidence asking samples into production prices. Collect more evidence (including sold eBay offers where useful) for special print cases and avoid substituting the normal-print prices for the missing 27.

## Verification
The prioritized queue was regenerated from live DB, retaining all 1,460 variant records and putting all 27 missing-price rows first. Initial 27-variant browser pass found matching catalogue products and German NM offer samples for some records, but these special-stamp prices were not published without physical variant evidence. Unit tests for triage, importer, source IDs, offer matching, and queue priorities passed.
