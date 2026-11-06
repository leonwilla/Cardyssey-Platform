# Decodo vs. current Cardyssey Cardmarket collector — 2026-11-06

## Evidence-based comparison

- User-provided Decodo Playground **Markdown** output: Tangela, Unbroken Bonds, `idProduct=372309`, filter URL `language=3&minCondition=2&isReverseHolo=Y`; eight visible offer entries and a catalogue statistic of 139 *available articles*. The 139 figure **cannot** be interpreted as 139 German NM Reverse matches. Markdown merges seller/condition/price text and does not preserve the original independent row-level language/edition/offer ID attributes necessary for a provable complete filtered median.
- Existing Cardyssey authenticated Edge pilot on the Tiny: Tangela Reverse (`sm10-16`) had **8/8 German NM offers**, asking median **0.32 EUR**, `all_pages_complete=true`; normal had **44/44** German NM offers, median **0.15 EUR**, complete. These are asking medians, not sold-market or official price-guide medians.
- Decodo's public Web Data API `POST https://data.decodo.com/v1/scrape` responds correctly on Tiny; without token it returns **401 Missing authorization header**. A secret-free authenticated request could not be made in this session; earlier interactive credential handoff failed. **No authenticated Decodo benchmark and no measured Decodo latency**; do not claim an improvement or that browser-action pagination works with this particular `/v1/scrape` account.
- Provider docs support `headless:html` and raw HTML rendering. Older Decodo Web Scraping API materials describe `browser_actions` such as CSS click + wait; support in the new `/v1/scrape` endpoint is **not validated**. Even when available, click may be constrained by login/visible-offer limits; only output per-offer unique ID, language, condition, edition/foil, exact product ID, and full pagination can justify price publication.
- **Decision:** no modification to the working Cardmarket collector and no import of Decodo price observations. The existing collector remains the trusted source for filtered offers; official Cardmarket JSON remains the fast aggregate reference. Do not replace known correct results with unverified Markdown.

## Safety

The API token posted in conversation is exposed. Do not store it in the repo, logs, scripts, or reports. Rotate it on Decodo. A later live benchmark should use `DECODO_API_KEY` from the environment with the rotated key, compare raw HTML, limit to Tangela normal/reverse and Lucario, capture request duration and per-offer identity, and publish no prices without verification.
