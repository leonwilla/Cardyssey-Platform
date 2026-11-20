# Cardmarket filtered-offer median experiment (2026-11-05)

## Intent

Use **physical** Pokémon singles offers with an explicit Cardmarket product identity, language **German**, target finish and edition, Near Mint or better. Offers without a condition can be *assumed NM* per Cardyssey policy, but should be labeled as an assumption. Exclude played, damaged, graded, signed, altered, bundles, mixed language and mismatched printings.

## Live remote test

From the authorized Tiny, `requests.get` against the ordinary German/English Cardmarket product page, with and without `language=3&minCondition=2`, returned **HTTP 403**, Cloudflare challenge rather than an offer list. We did not use captcha circumvention, impersonate logged-in users or call undocumented private endpoints. No live offers were acquired, no new live price was invented.

Cardmarket's documented **Articles** API supports filters for article language, minimum condition, foil and other options, with pagination; requesting authorized access is the preferred route. Source: https://apiv2.cardmarket.com/ws/documentation/API_2.0:Market_Place_Information . Some third-party vendors offer offer-level APIs, but require separate evaluation of quotas, licensing and fees. Do not conflate such vendors with the official Cardmarket API.

## Implemented, tested, not yet live-priced

`scripts/cardmarket_offer_median.py` reads JSON from an **authorized exported list** (no network). It validates a numeric product ID, explicit DE language, exact finish and first-edition flag, offer card language, product ID, finish, edition, graded/signed/altered flags, single-card offer status, condition and EUR price. Duplicate offer IDs are ignored; explicit Played/Good/Damaged etc are rejected. Missing condition -> `assumed_nm` for DE only. It computes a **median of qualifying active asking offers**, not an eBay sold-price median and not Cardmarket's sales-based trend. Counts rejected reasons and records the assumed-NM count.

Results are marked `PARTIAL_SAMPLE_MEDIAN_NOT_MARKET_WIDE` unless the data explicitly certifies that all pages were fetched and uncapped with a matching total count. The API itself has page/result limits; where these make comprehensive access impossible, never claim full market coverage. Only a complete sample without assumed conditions is marked safe for a possible **future** automatic publishing integration. There is intentionally no database-writing mode here.

Command: `python3 scripts/cardmarket_offer_median.py <approved_offer_export.json> [--report /tmp/offer_report.json]`.

## Rollback

No new Docker image, container, daemon, third-party subscription or secret. Only `scripts/cardmarket_offer_median.py`, `scripts/test_cardmarket_offer_median.py` and this documentation were added. Revert the git commit to remove the experiment. Existing Cardmarket guide prices and eBay sold history are untouched. Temporary remote curl/requests tests created no persistent scraped offers.

## Next step for real offer median

Get authorized Cardmarket Articles API credentials (or a permitted offer export) and validate paging/metadata with **one confirmed German product and exact print**. Only then add a quota-controlled fetch adapter and audit DB table. Until then: existing Cardmarket price guide remains the real integrated source and **the 1,460 still unpriced German physical prints are not reduced by this experiment**.
