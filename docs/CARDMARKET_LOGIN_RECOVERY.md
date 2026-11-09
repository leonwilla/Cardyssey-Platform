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

## Field/filter readiness and unfilterable physical prints

`cardmarket-filter-readiness.py` checks required set/collector/variant/type
fields across both full queues. The admin monitor shows counts of missing or
unrecognized standard-filter inputs and special prints not covered by
Cardmarket's offer filters, instead of presenting them all as false missing
product identities. The scanner now reports `MISSING_REQUIRED_SCAN_FIELDS`
with the exact field names *before* navigating to Cardmarket. Normal and Holo
both imply `isReverseHolo=N`; Reverse implies `Y`. German `1. Auflage` and
English `1st-edition` both imply `isFirstEd=Y`; explicit Unlimited or
`Copyright 1999-2000` imply no First Edition.

Cardmarket's normal offer filters do NOT verify ©1999-2000, shadowless,
cosmos/other foil patterns, and many promo stamps. For those, an independently
validated print/product match is still required and a general filtered offer
median may not be imported as the exact-print price. The importer refuses
observations explicitly marked with unfilterable print attributes. Do not
infer that all special-print cases need a human; first seek product-level
version evidence. Basic fields present in the queues do not imply the provider
supports a filter for every stored variant field.

## 2026-11-09 special-print known pages (Wizards Pikachu, Fossil Aerodactyl)

The owner supplied `Pikachu-WP4`, `Aerodactyl-V1-FO1` (normal) and
`Aerodactyl-V3-FO1` (Prerelease). These are explicit **card-page hints**, not
proof of each physical stamp or holo pattern. In particular the Wizards WP4
product page may contain several movie-stamp treatments; a non-English card
image is not a second English print. Fossil Aerodactyl prerelease Cosmos and
Starlight foil variants share the V3 product page until listing evidence
proves their exact physical foil. Do not assign one shared median to both.

`config/cardmarket-known-print-page-hints.json` maps exact Cardyssey
card/variant IDs to the owner's known product-page slug and the expected
collector-code suffix. `scripts/cardmarket-apply-print-page-hints.py` embeds
these into both queues **after every weekly rebuild**, setting
`reference_print_verified=NO` and retaining any existing variant-specific
product IDs/prices. The browser uses the trusted page hint before falling
back to translated-name search, verifies its set/collector-number path, and
records `PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED`, never publishing a
version-specific median merely because the page was found. Exact foil/stamp
and physical language remain separate checks. The two relevant URL guards
are `base3=Fossil` and `basep=Wizards-Black-Star-Promos`.

A new full DE/EN scan epoch was explicitly created after the corrected queue
export. If the dedicated Edge profile remains on a Cloudflare challenge,
production stays paused with the explicit `BLOCKED` status and must be
released in that same profile before gated manual resume.

## 30th card match vs incomplete Cardmarket price pagination

When the latest scan has `FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE` (or an
analogous price-filter status), **and** the Cardyssey set starts with `30th`,
the browser positively confirmed the product (`identity_confirmed=true`), the
observed `idProduct` agrees with the exact queue candidate, and a previously
known card URL / human-verified route exists, the scan failure belongs to
`PREISPRUEFUNG`, not `ZUORDNUNG`. In particular Pikachu & Zekrom GX
`30th-c-008` / `907963` was observed with 69 offers but load-more disabled;
this does not require selecting or confirming the card again. These records
are shown under **Technische Preisprüfungen**, separate from the default
**Karten-Zuordnungen** and **Browser-/Anbieterfehler** views. A positive scan
with a *different* product ID than the candidate is still a `ZUORDNUNG`
problem and must never be hidden. A valid product ID is not sufficient proof
of the exact 30th stamp's offer price; incomplete price medians are not
published. The categorization runs over the newest scanned observations and
updates on each UI refresh; the scan engine/price observations are unchanged.
