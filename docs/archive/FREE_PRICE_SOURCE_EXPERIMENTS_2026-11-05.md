# Temporary free price-source experiments — 2026-11-05

## Decision and result

**No live price-provider integration was added.** No production API/database data was modified. No recurring worker, task, systemd unit, or running scraper was added by this experiment.

### Baseline

`python3 scripts/price_source_coverage.py`, last summary 2026-11-05 03:48 UTC: DE 17,048 / 18,728 bulk prints priced; EN 19,232 / 20,851; JA 3,000 / 11,147; KO 1,621 / 7,517; zh-tw 108 / 2,569. Main gaps are regional market coverage and physical-variant identity in Asian languages, not a general lack of English-language APIs.

### Solverr isolated trial

- Project: `ghcr.io/unseensnick/solverr:latest` (Solverr 1.9.2, Chromium 156). External reference: https://github.com/unseensnick/Solverr
- Created a **temporary** container named `cardyssey-test-solverr` bound only to `127.0.0.1:18191`; 2 CPUs, 2.5 GB memory cap, 512 MB shared memory, no restart policy, no Cardyssey DB connectivity/credentials provisioned.
- Local readiness endpoint returned `FlareSolverr is ready!`; browser startup completed successfully.
- One attempted GET of `https://www.pricecharting.com/` via `request.get`, maxTimeout 25 seconds. Response `status=error`; message **`Error: Error solving the challenge. Challenge still present after solving attempts`**. No price content or verified card mapping obtained. An earlier test also returned an error result; the wrapper mistakenly expected `solution.response` to be a string, so that first diagnostic was inconclusive. Second test inspected the actual error message.
- **Cleaned up immediately**: `docker rm -f cardyssey-test-solverr` and `docker image rm ghcr.io/unseensnick/solverr:latest`. Confirmed container absent and image removed. The one-time image download may temporarily grow WSL VHDX; Docker layers were removed but shrinking Windows host files requires the separate storage-maintenance procedure.
- No solver service installed permanently. Re-running without evidence of benefit is not recommended.

### Alternatives evaluated (not installed)

- FlareSolverr (https://github.com/FlareSolverr/FlareSolverr): free/open source but explicitly warns that its CAPTCHA solvers do not currently work; additional installation would likely duplicate browser costs.
- PokéWallet API (https://pokewallet.io/api-docs): published Free tier offers 100 calls/hour, 1,000/day, a new **API key**, and TCGplayer/Cardmarket pricing. Its per-set prices/history are Pro features. We did not register an account, invent credentials, or ingest prices. Data overlaps existing Cardmarket/TCGplayer sources; validate commercial use rights and precise variant identities before treating it as incremental coverage.
- TCGdex and TCGCSV already present in Cardyssey's existing ingestion. Keep existing sources and improve exact variant mapping/source freshness before adding another overlapping provider.
- PriceCharting official API requires paid access and verified product mapping; separate commercial use permission may be needed for Cardyssey's shop/app. Previous subdomain/cookie test and Capsolver evaluation are recorded in the archived Git history (commits `8e6ecfc`, `15eaa17`), and the current `docs/archive/PRICE_SOURCE_COVERAGE_AND_CLEANUP_2026-11-05.md`.

## Cleanup registry

| Resource | Location/name | Added this experiment? | Current state | Rollback |
|---|---|---|---|---|
| Solverr container | `cardyssey-test-solverr` | Yes | **Removed** | Nothing further |
| Solverr Docker image | `ghcr.io/unseensnick/solverr:latest` | Yes | **Removed** | Nothing further |
| Port exposure | `127.0.0.1:18191` | Temporary | **Closed** | Nothing further |
| Test config/secrets | None | No | None | Nothing further |
| Background services/timers | None | No | None | Nothing further |
| Source code files | This audit document only | Yes | Tracked | Delete this document if obsolete |
| Legacy CapSolver preflight | `scripts/capsolver_preflight.py`, `scripts/setup_capsolver_key.py` | No (pre-existing) | Preserved | Remove separately only if abandoning CapSolver |
| Locally saved CapSolver API key | `/home/tv/.config/cardyssey/capsolver.key` | No (user-created prior to experiment) | Preserved | `rm -f /home/tv/.config/cardyssey/capsolver.key` after user's decision; revoke in provider dashboard |

## Follow-up gate

Only add a new free API after demonstrating: (1) permitted use, (2) exact card+language+physical variant identity, (3) genuinely new coverage against existing price rows, (4) no overwrites of better verified prices, (5) explicit and tested cleanup procedure, and (6) rate-limit and cost controls. Start with a dry run on a tiny sample of unresolved DE/EN and Asian entries, never a blind mass import.

## Final rollback (2026-11-05)

PriceCharting/CapSolver exploratory tools, their test helpers, empty mapping CSV and optional weekly workflow tasks have been removed. The locally stored CapSolver key was deleted. Existing regional TCG, Cardmarket, CardTrader and eBay collectors remain active. See `docs/archive/PRICE_SOURCE_COVERAGE_AND_CLEANUP_2026-11-05.md`.
