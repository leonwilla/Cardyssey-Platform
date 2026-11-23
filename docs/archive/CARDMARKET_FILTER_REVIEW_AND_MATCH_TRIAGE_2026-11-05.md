# Cardmarket product filters and German variant identity triage (2026-11-05)

## Browser test (Lenovo Tiny, isolated interactive Chrome profile)

- Chrome started at the ordinary German Cardmarket Pokemon site. Its browser page was inspected using a temporary localhost-only DevTools connection, with no credential, cookie or token export.
- **Login could not be confirmed:** a visible username/password field appeared on the account header. No claim of authenticated account features is made.
- On the public product `30th-Celebration/Pikachu-30C025` (public Cardmarket product 907632), the product filter form exposes `language[3]=3` (Deutsch), `minCondition=2` (Near Mint minimum, including Mint), `extra[isSigned]=N` and `extra[isAltered]=N`.
- A single interactive form submission returned with these values selected. The visible cheapest offer changed from 0.02 EUR (unfiltered) to 0.10 EUR (filtered), while the page-wide price trend remained 0.77 EUR. These are **observations for this single page at test time**, not prices to import or a claim about every offer.
- Product page filter is a POST with session-specific form security fields; never hard-code or log them. Filters are **not** guaranteed to prove a unique edition, foil, reverse, stamp or print. Product number and set metadata must still be separately verified.
- Cardmarket on-page trend is not recalculated as a German/NM median and must not be used as one.

## Queue improvements

`python3 scripts/prepare-cardmarket-browser-review.py --input /tmp/cardyssey-cardmarket-login-review.json --output-dir reports/cardmarket-review`

From 1,460 unresolved German variants, 978 have in-set product candidates. 96 have third-party variant references; 8 include a direct Cardmarket variant product ID. Among the 8, one equals a current in-set candidate and seven differ, requiring conflict review. 389 variants without in-set candidates have name-only hints; these are **not promoted** into matches.

The updated CSV includes external variant references, name-only hints, action reason, concrete filter reminders and individual proof fields for card number, set, language, edition, foil and stamp. P1-P5 are review priority, not proof or price-readiness. No variant identity is automatically approved and no cache/database writes are performed by this script.

## Safety / rollout boundary

This browser-side sample only establishes that normal public product filters work. It does not authorize bulk extraction, provide an API or make 1,460 variants immediately matchable. Before attaching a Cardmarket product ID to a German physical variant, verify printed number, expansion, language, edition, finish and special markers. Where these are not available from an authorized source, leave status unresolved. Use the existing official Cardmarket price guide only after validated exact product identity and market applicability; do not substitute all-language product trends for filtered prices.

Tests: `python3 -m unittest scripts.test_prepare_cardmarket_browser_review scripts.test_cardmarket_offer_median scripts.test_price_identity_validation -v` (20 passing).
