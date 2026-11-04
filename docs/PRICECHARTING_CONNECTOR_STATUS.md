# PriceCharting connector – verified status (2026-11-04)

## Outcome of `ae.pricecharting.com` suggestion

- `http://ae.pricecharting.com/` responds with HTTP 301 to `https://www.pricecharting.com/`.
- `https://ae.pricecharting.com/` has a TLS certificate with `notAfter` 2021-12-11. **Never disable TLS validation** or forward session cookies, redirects, authentication data or API keys to this host.
- `https://www.pricecharting.com/` returned HTTP 403 (Cloudflare challenge) on the authorized Tiny.
- This is **not a working or secure independent price endpoint**. There is no justified production scraping integration through this subdomain.

## Existing safe implementation

- `scripts/refresh-pricecharting-exact.py`: official **paid** PriceCharting `/api/product` requests by explicitly verified unique product IDs. No bulk HTML scraping; converts USD to EUR with a validated exchange rate and records that ungraded-to-NM is a Cardyssey assumption, not an official PriceCharting condition.
- `scripts/prepare-pricecharting-review.py`: stages human-review links and evidence; never infers exact card print or price from a similar title alone.
- `scripts/diagnose-pricecharting-access.py`: certificate, redirect, Cloudflare status and safe API-readiness check. Writes `/tmp/cardyssey-pricecharting-access.json`.
- The existing global Cardyssey source policy does **not** select PriceCharting for bulk cards.

## Current blockers

1. No `PRICECHARTING_API_KEY` environment variable configured on the Tiny.
2. `config/pricecharting-exact-variants.csv` currently has its CSV header only, **zero exact product mappings**. Product name alone is insufficient to map language, edition, variant and physical print.
3. PriceCharting's official terms state that reusing its subscription/API/CSV prices in a public or customer-facing application requires a separate commercial license and express permission.
4. API has current values; it does not provide historical sales/price curves. Cardyssey must independently record future snapshots if licensed.

## To enable when the prerequisites are satisfied

- Obtain a valid subscription and **commercial use permission** from PriceCharting.
- Store the API key in a server-side secret, not GitHub, client, URL displayed in logs or an untrusted domain.
- Verify and record each PriceCharting unique product ID against Cardyssey card ID + language + physical variant ID, adding evidence to `config/pricecharting-exact-variants.csv`.
- Run `python3 scripts/diagnose-pricecharting-access.py` and verify readiness. Then run `python3 scripts/refresh-pricecharting-exact.py` without `--apply` to preview; only then run with `--apply` in a controlled test and check the monitor.
- Never replace reliable Cardmarket/TCG or eBay sales with an unverified PriceCharting mapping.

## Production decision

**Not enabled.** The suggested subdomain is not a safe or verified bypass of the 403 and must not be used as a price provider. Continue with the established regional TCG/Cardmarket and verified eBay sold listings while the paid/commercial license and exact product mappings are outstanding.
