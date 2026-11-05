# Cardmarket HTTP / CF test 2026-11-05

The user supplied `pricecharting_cf.py`, whose transport combines Chrome/CDP, challenge-session detection, and the `wreq` HTTP client. A provider-specific `cardmarket_cf.py` was generated from that original file for independent, read-only evaluation (separate local artifact). It adds a Cardyssey CSV queue, URL discovery, request metrics and JSONL evidence output. It does not publish card prices. It must only run against a permitted session and should not share or commit session cookies.

## Verified results

- Independent Linux `wreq==0.13.0`, without Cardmarket browser session: HTTP 403 Cloudflare challenge for 2 product pages. The 0.02-0.08 second responses were *not* product data, hence not a usable speed improvement.
- Same-origin `fetch()` inside the already authenticated Windows Chrome CDP session: 5 distinct searches returned HTTP 200 and 27-30 linked products, in 375-444 ms apiece.
- Five cards (base1-8, basep-1, basep-4, ex8-105, ex9-56) through full Windows Cardmarket collector:
  - New CDP authenticated background-fetch search: **33.4 seconds**.
  - Original full-navigation search: **36.2 seconds**.
  - **Identical outcomes**: four MULTIPLE_SEARCH_HITS, one FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE; matching product 276567 and sampled median 14.97 EUR for ex9-56.
  - Total runtime improvement **7.7%**, not orders of magnitude.
- This does *not* demonstrate that transferring a Cloudflare cookie from Chrome to `wreq` will work. The Python adaptation has not passed an authenticated end-to-end `wreq` test on the Tiny because its WSL environment lacks local Chrome, and the Windows machine did not have native Python installed.
- The existing Windows collector now uses session-bound background HTTP search; product identity and variant checking stay as before.
- A previously hung Windows collector made no progress for more than 40 minutes; it was safely restarted with progress records kept.

## Security and integrity

No cookie export or TLS-verification changes were made to the deployed collector. The benchmark kept separate result files under the Windows CardmarketCollector directory; it did not import benchmark sample prices into production. Exact foil, first-edition and special-stamp print identities remain unverified by aggregate asking samples.

Further speed gains require reducing browser checks by catalogue crosswalk and verified product IDs, rather than repeatedly solving browser challenges. In-browser HTTP can improve search overhead but provider throttling must be respected.
