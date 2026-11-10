# Cardmarket Open Source Research — 2026-11-09

Goal: automate card/set identity for Cardyssey Pokémon DE/EN without an official
Cardmarket API key and without asking the owner to assign cards by hand.

## Verified GitHub repositories

- `DrankRock/CMScrape-console` (`README.md`, `run.py`): accepts a **list of
  already known product URLs**, parses product stats/images and CSV. This is
  **not** a card/set matcher and not a source of correct physical print IDs.
  It starts a FlareSolverr container; we do not install it or implement any
  challenge bypass. Our legitimate browser remains paused upon Cloudflare.
- `lupzn/cardmarket-stock-exporter` (`README.md`, `popup.js`, `CHANGELOG.md`):
  extracts idProduct, article ID, a set code, collector number and attributes
  from a logged-in user's **own stock listings**. Most useful lessons are
  preserving attributes separately, safely separating sets/collector numbers,
  splitting by offer filters and NEVER reusing inherited `?language=...&
  isReverseHolo=...` query parameters from account preferences. It is not an
  all-card identity service. We independently implemented clean canonical URL
  reuse; no third-party extension has been installed in the user's profile.
- `Git-Romer/pokecollector` (`README.md`): uses TCGdex and card price links.
  Cardyssey *already* mirrors TCGdex, so another manager is not an independent
  authority for the exact promo or holo physical printing.
- `TomasPereiraa/Pokemon-Card-Tracking` (`readme.md`, `scraper.py`): CSV with
  **existing URLs**, SeleniumBase scraping for card price trends and PSA. It
  does not map unknown Cardyssey cards to exact Cardmarket print IDs. It uses
  anti-bot browser features; do not deploy these to evade the provider.
- `andli/pymkm` and `Cardmonitor/cardmarket-api`: official Cardmarket API
  wrappers, not useful without valid API credentials; no key is available.
- `lupzn/cardmarket-stock`: separate alleged repository does not exist at the
  URL supplied. Its features are present in `cardmarket-stock-exporter`.

## Important corrections to pasted generic scraping advice

- Converting card/set names to hyphenated URLs is **not reliable identity**.
  There are set-localized slugs, V1/V2/V3 product versions, multiple reprints,
  promo numbers and foil-language differences. A returned HTTP 200 can be a
  redirect, a login page or an interstitial, not proof of a correct card.
- `idProduct` uniquely identifies a Cardmarket **product**, but a single
  product page may host different language, foil, stamp, condition and seller
  attributes. `idArticle` identifies one seller's article, not a catalog card.
- Trust the official Cardmarket singles feed `idProduct` and `idExpansion`
  (already available locally), Cardyssey's printed collector number and the
  real destination product page's `input[name=idProduct]`. Never promote a
  source-only print candidate to a verified language/NM/physical-print price.

## Implemented: direct idProduct lookup with safe search fallback

- Existing `scripts/cardmarket-enrich-queue-hints.py` now exports
  `catalog_expansion_id` alongside `catalog_singleton_id` for the two language
  queues. 19,604 DE and 19,520 EN variants have this independently
  catalog-derived SINGLETON hint. These are **candidates**, not confirmed
  special prints or prices.
- The Windows Edge collector tries `https://www.cardmarket.com/Pokemon/Products?
  idProduct=...` **before translated-name search**, using the user's existing
  signed-in session. On November 9, the separate Edge tab probe returned
  `idProduct=275420` for Pikachu WP1 and `273703` for Machomei BS8 with the
  correct product page/number. The redirect may contain inherited account
  filters; the collector drops all query parameters before reusing it.
- A direct product hit is accepted only if the browser's `input[name=idProduct]`
  agrees with the catalog ID, the destination is Cardmarket Singles, its final
  collector number agrees with Cardyssey, and an existing verified set-slug
  guard (where available) also agrees. This is **card/set evidence only**;
  special-print status stays `PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED`.
  Standard normal/holo/reverse prints continue into the existing language/NM
  offer-filter pipeline (never an automatic price import from an unfiltered
  product page). A confirmed catalog card ID is not proof of hidden stamps.
- If the provider does not support the redirect, the scanner disables this
  optimization for the **rest of that batch**, uses the existing text search
  and preserves progress. A Cloudflare challenge still causes an explicit
  BLOCKED pause, not a bypass. This prevents repeated failed redirect attempts.
- The admin groups these results as **PREISPRUEFUNG** when basic variant
  filters can check the print later, or **DRUCKPRUEFUNG** when a special
  stamp/foil/subtype is not shown by simple filters. Do not ask the owner to
  reassign an already identified card/set.

This is a controlled identity improvement, not a verified 65,647-print
mapping. The full live browser scanner will exercise the new path on its next
batch; the two separate product-URL probes do not validate every expansion,
rare stamp or price listing. Existing manual confirmations, provider routes
and published prices have not been changed by this work.

## 2026-11-10: Cardmarket price-offer pagination diagnostics and fix

Inspecting the active signed-in Edge profile with a temporary independent
browser tab confirmed that the user is signed in, offer rows start at 50,
`#loadMoreButton` is a visible enabled `type=submit` button, and
`#articlePage=1`. The product filter offers language, condition, reverse,
seller country, seller type, reputation and amount (not a price-range filter).

Among 495 DE incomplete price observations since Nov 9 21:00 UTC, 260 had
`LOAD_MORE_DISABLED_OR_LIMIT_REACHED`, 187 hit our artificial
`CARDMARKET_300_CAP`, 40 had `LOAD_MORE_NO_NEW_OFFERS`, and the balance had
other evidence failures. These were *not* caused by an unauthenticated session.

The collector now supports up to 1,200 extracted rows and 24 AJAX pages per
card, instead of artificially declaring all cases at 300 incomplete. If a
load-more call ends without new rows, the scanner waits for 4 stable DOM
checks and requires the actual button to be **removed** (not merely disabled)
before it clears the incomplete pagination reason. A still-visible button,
reached page cap, changed filter, nonunique offer IDs, mismatching offer flags,
expired login or an incomplete scrape still fails closed. The median of the
visible sample remains diagnostic only; a complete market median is not
assigned unless every row passes language, condition, print and completeness
checks. The provider may have independent limits, so this doesn't guarantee
full pagination for all products. The scanner uses the updated script only on
its next launcher batch; the running collector need not be reset.

## 2026-11-10: Felori SVI013 print and V1/V2 reproducible validation

- The user-supplied Cardmarket `Cards/Sprigatito-Scratch-Leafage/Versions`
  belongs to a 21-product reprint family in the official singles feed. It is
  **not** the same physical printing 21 times.
- Independently verified the **same-set** Cardmarket Scarlet Violet product
  pages in the signed-in dedicated Edge browser:
  `Sprigatito-V1-SVI013` product ID `689763`, and `Sprigatito-V2-SVI013`
  product ID `691000`, both from official expansion `5223`, number `013`,
  shared Cardmarket `idMetacard=415179`. The user's Chinese `Gem-Pack-Vol-1`
  page maps to product `806289`, expansion `6001`, a different physical
  expansion; it must never be assigned to DE/EN `sv01-013` just because the
  illustration and metacard are shared.
- `config/cardmarket-verified-set-overrides.json` permanently pins Cardyssey
  `sv01` to Cardmarket `5223` for regular re-runs. A one-time verified-set
  repair re-evaluated all **258 cards**, with 98 single-product, 156 multi-
  product and 4 name-missing cases; DE/EN review candidates updated without
  approving prints or touching human-verified routes and prices.
- The V1 product page has a dedicated *Only Reverse?* control, and the
  `?language=3&minCondition=2&isReverseHolo=N|Y` deep links were validated in
  the persistent browser: the N page is normal product 689763, the Y page
  changes to Felori (Foil) and remains product 689763. Both values still
  require form/offer-attribute verification during the scanner's real price
  pass. `cardmarket-known-print-page-hints.json` specifies this **standard
  offer-filter candidate**, only for normal + ordinary reverse in `sv01-013`.
  The collector resumes language/NM/edition/reverse offer filters rather than
  short-circuiting these into print-review failures. This is explicitly not
  human confirmation of an exact print or its price.
- The *Grass symbol* reverse and the separate Holo curated DE rows retain
  BOTH exact same-set V1/V2 IDs as candidates. We have **not** proved which
  one (if either) represents the physical special printing. They do not get
  the ordinary reverse price, even if a similar-looking Chinese print exists.
- Cardmarket's real V1 and V2 images were observed at
  `https://product-images.s3.cardmarket.com/51/SVI/689763/689763.jpg`
  and `/51/SVI/691000/691000.jpg`. Admin review now displays the two verified
  product-version photos and links side by side as a *comparison*, not proof
  of a physical edition, stamp or foil. This reusable version-photo map can
  be extended when another split product page has been independently checked.
- The existing official-product-family and verified-expansion mapping work
  generically across sets, but a **global V1/V2 means normal/special rule is
  forbidden**. Only positive source evidence may select a product version;
  all other ambiguous prints remain in print review, not guessed prices.
