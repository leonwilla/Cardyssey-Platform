# Cardmarket connected browser collector (Lenovo Tiny)

The collector uses the **dedicated local Chrome profile** at
`%LOCALAPPDATA%\Cardyssey\CardmarketReviewProfile`. It only accesses
Cardmarket in the already signed-in browser. Neither password nor login
cookie/token is exported, copied to the project, or saved in reports.

## Operating mode

1. `Cardmarket-Collector-Launcher.ps1` opens the isolated browser with a
   localhost-only debugging endpoint, unless it is already running.
2. `Cardmarket-Account-Collector.ps1` resumes the 1,460-row German
   variant queue from the last processed key. The test used
   `MEP-095 Lucario`, product 895610: German/NM/signed-no/altered-no
   filters returned 50 visible German NM offers.
3. For each row, the collector searches by name and printed number,
   requires a unique search hit and an in-set candidate ID, and then
   applies German, minimum NM, unsigned and unaltered filters. It stores
   **visible asking-price samples** separately from official reference
   prices. It does not pretend the cheapest page is a complete market
   median, and it does not assume a product ID proves special stamps,
   edition or foil.
4. The worklist and progress are kept only under
   `%LOCALAPPDATA%\Cardyssey\CardmarketCollector`, not on the Desktop.
   A Windows Startup shortcut restarts the launcher after a Windows
   logon. Login-required / blocked sessions stop rather than attempting
   challenge bypasses. Product errors are eligible for retry after
   restart.
5. The existing Tiny cron service runs the
   `import-cardmarket-browser-observations.py` script every 15 minutes.
   That script upserts only validated **review evidence** into
   `price_review_cases`. It never overwrites production
   `tcg_price_cache` with a partial sample.

The official product catalogue and price guide are still the primary
catalogue and price feed. The separate
`refresh-cardmarket-price-cache.py --language de` production update ran
successfully on 2026-11-05, reporting **631 applied refresh/price rows**
using existing validated Cardmarket mappings. This figure is the number
of applied updates, not the number of newly resolved physical variants.

## Manual checks / recovery

Current collector progress lives at
`%LOCALAPPDATA%\Cardyssey\CardmarketCollector\progress.json`.
If login expires, sign into the dedicated Chrome window normally, then
launch `Cardmarket-Collector-Launcher.ps1` again. When the site blocks
access, stop and review the cause rather than trying to bypass access
controls. The JSONL log is resumable and contains no credentials.

The account collector has been smoke-tested against a genuine product
and native on-page filters. Python unit tests for the importer and
cross-reference checks passed (32 tests). The full browser queue is
multi-hour and can be monitored independently on the Tiny; a started
queue is not a completed queue.
