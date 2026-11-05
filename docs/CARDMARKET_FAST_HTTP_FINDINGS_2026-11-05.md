# Cardmarket 429 root-cause debugging — 2026-11-05

## Verified technical findings

- `pricecharting_cf.py` Chrome-to-`wreq` session transport worked on Cardmarket's homepage and nine product pages, then began returning HTTP 429 (`cf-mitigated: challenge`).
- A new attempt after the previously recorded 30-minute cooldown also immediately returned HTTP 429. Increasing the delay alone was not effective.
- An existing real Chrome tab could fetch an unfiltered product page in 393 ms (HTTP 200) even while external `wreq` received 429.
- A same-origin Chrome `fetch` can also retrieve a *filtered* German/Near Mint product page directly with `?language=3&minCondition=2&isSigned=N&isAltered=N`. A single page returned HTTP 200 in 323-447 ms for three selected products; correct IDs, filter values, and 7/50/50 offer rows were verified.
- However a subsequent limited Chrome batch returned 200, 200, **429**. Thus Chrome traffic is also throttled/challenged when repeated. The 0.3-0.4 s **network response time is not sustained verified price throughput**, and 50 visible rows can be only the first page.
- A standalone PowerShell fast browser collector was added for known canonical URLs, same-origin filtered GET, per-card JSONL checkpoints, and fail-closed HTTP 429 / challenge handling. A single-case live execution returned HTTP 429; it recorded `BLOCKED` correctly and did not alter production prices. No infinite automatic retry.
- Existing Windows collector was found to have treated 1,070 abandoned WebSocket calls as separate card errors. This was repaired and the remaining errors were triaged offline: 473 single-product candidates (358 unique products), 226 multi-candidate cases, 372 with no candidate.
- Cardmarket official JSON priceguide bulk audit successfully refreshed staging for 31,386 German variants in 18.72 seconds, with 15,979 candidate guide values. These **are not confirmed exact German NM/print prices**.

## Current decisions

Cardmarket's challenge is an external access policy, not a deterministic local code error. Repeatedly resetting identities, sessions, or IP addresses to evade access limits would not be a stable path. Do not do this. Safe path to scale is official feed batching, cache, metadata crosswalk, and limited per-product review with respected 429 and `Retry-After`.

The fast collector is **not yet approved for unattended high-throughput price ingestion**, and no estimate for a tenfold production speed-up is justified.

### Fast collector

`scripts/Cardmarket-Fast-Chrome-Collector.ps1` uses the signed-in or normal Chrome page already open through CDP port 9222, only performs GETs to explicitly supplied Cardmarket product URLs, does not export cookies and does not publish sample median prices. `MaxCases=10` is the default, and rate-limit detections immediately stop and mark a checkpoint.

### Operational consequence

The scheduled Windows recovery run after the prior cooldown stopped with `CONNECTION_LOST` rather than mislabeling another thousand cards. It will need a functioning Chrome session before remaining cases can be verified. Avoid overlapping multiple collectors against Cardmarket.
