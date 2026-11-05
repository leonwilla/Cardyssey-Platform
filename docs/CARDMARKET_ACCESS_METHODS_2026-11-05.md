# Cardmarket access methods tested on Lenovo Tiny, 2026-11-05

* Official Pokemon product catalogue JSON: HTTP 200, application/json, 13766177 bytes. Already used for identity candidates by refresh-cardmarket-price-cache.py.
* Official Pokemon price guide JSON: HTTP 200, application/json, 15789998 bytes. Already integrated as pricing source. The guide is not a German/NM-filtered quote.
* Interactive public product filters: successful on 30C Pikachu 025 with German, at least NM, unsigned, unaltered. The overall price trend did not change with filter selection. Tested on one product only.
* Logged-in commercial account: dedicated Chrome profile and login store file exist, but browser login was not verified. Normal site re-authentication remains necessary after logout.
* Bulk browser offer crawling: intentionally not attempted; rate throttling is not itself authorization for mass requests.

The isolated browser profile remains in Windows local Cardyssey configuration. Do not export cookies, passwords or session tokens to reports, scripts or GitHub.

## Full audit of unresolved German variants

The offline audit inspected all 1460 unique variant keys in the already generated fallback report. Counts: 637 single in-set candidates, 333 multiple in-set candidates, 389 name-only hints, 93 without candidates, 7 direct Cardmarket ID conflicts, 1 matching direct ID. Product identity and prices remain unconfirmed until number, set, language, edition, finish and special stamps are verified.

Audit command:

    python3 scripts/audit-cardmarket-variant-evidence.py --input /tmp/cardyssey-cardmarket-login-review.json --output-dir reports/cardmarket-review

Local CSV and JSON reports are stored under reports/cardmarket-review and copied to the Windows Desktop folder Cardyssey-Cardmarket-Pruefung. No production prices or account credentials were modified by this audit. All 24 unit tests passed.
