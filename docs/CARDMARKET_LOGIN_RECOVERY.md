# Cardmarket scan: safe pause and resume

The persistent Edge profile on the Tiny is `CardmarketEdgeProfile`.
No user passwords, 2FA secrets or clearance cookies are exported or sent to the backend. The browser must itself be signed in and Cloudflare must have allowed the normal session.

- `Cardmarket-Session-Status.ps1`: read-only DOM login check, with explicit `BLOCKED` / `LOGIN_REQUIRED` / `AUTHENTICATED` / `UNVERIFIED` states. The status is included in `cardmarket_scan_monitor.py` and visible at `/admin/prices`.
- `Cardmarket-Collector-Launcher.ps1` refuses to start if Cloudflare remains active or authenticated status isn't positively established. A `LOGIN_UNVERIFIED` state is fail-closed, not an excuse to scrape as guest.
- The production queue runner is started with `-RequireLogin` and stops immediately if auth disappears during a run; Cloudflare also stops the run. No price is published for either failure.
- New Windows scheduled task `Cardyssey Cardmarket Manual Resume` starts `Cardmarket-Manual-Resume.ps1`, which calls the same gated launcher. The authorized admin endpoint `/api/admin/cardmarket-scan-control` triggers the Windows task, never receiving login credentials or launching a new independent browser.
- The 15-minute resume watchdog rechecks the same session, and does not restart against Cloudflare/login failure. It may resume after observed account authentication, but the user can also click `Scan fortsetzen`.
- Queues for **both** German and English are refreshed using the official feed and validated Cardyssey-set crosswalk. The runner processes them sequentially (`both`), German first and English after German completion. Existing observations and source routes are preserved; risky expansion name-list duplicates remain review candidates rather than automatic verified print identities.

**Owner intervention:** Open the *dedicated Cardmarket Edge window on the Tiny* (not a separate Firefox or normal browser profile). Complete an ordinary Cloudflare challenge if shown, and sign in through Cardmarket if needed. In Cardyssey `/admin/prices`, verify the session status and click `Scan fortsetzen`. If the browser is not authenticated or Cloudflare remains active, the button requests a gated attempt and no scan begins. Don't share passwords with the assistant.

## Full fresh DE/EN recheck

A one-time `full-rescan-epoch.json` (stored in the collector's local directory, not in git) holds the user-requested start of the new full verification cycle. Previous observation logs remain on disk and can still be inspected, but they **do not count as rechecked in the new cycle**. The collector processes cases with observations older than the epoch, marks them once per cycle, and continues after a pause without repeatedly replaying the first batch. The admin monitor shows new-cycle progress separately from cumulative historical observations. Do not reset the epoch on each scheduled launch.

The 19 unresolved overlapping set-name lists are quarantined: 1,857 DE / 1,858 EN candidate rows have their unverified Cardmarket IDs cleared, and the collector records `SET_MAPPING_PENDING` without making a browser request. This is not counted as a verified mapping. Confirmed human product routes are not quarantined; cases are re-enabled when the expansion has independent evidence and the weekly queue is regenerated.

## Live failures and forced restart

A founder can click **Komplett neu scannen (DE + EN)** even while the queue is
running. `cardmarket-reset-rescan.py` stops only the Cardmarket runner/collector
processes, waits for shutdown, then atomically starts a **new** epoch and
resets both progress counters; old observation JSONL and accepted prices are
preserved. The existing authenticated Windows resume task starts the next run.
The restart can still pause on a provider challenge or missing login.

The default-open `Scanfehler live prüfen` section loads
`/api/admin/cardmarket-scan-failures` every 15 seconds. It reads the newest
scanner observation per (card, variant), filters to the current epoch by
default, paginates 50 per page and allows switching to all historical failures.
Errors have distinct `ZUORDNUNG` or `TECHNISCH` categories. A technical error
must never be presented as proof that a product does not exist.
`Einzelkarte erneut testen` writes a priority timestamp onto only the exact
queued card variant (no product mapping or price edits), which the existing
scanner prioritizes in the next batch. Failed cases lacking a current queue
variant are explicitly reported as not actionable instead of guessing an ID.
