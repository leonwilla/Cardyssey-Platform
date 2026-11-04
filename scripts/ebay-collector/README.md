# Cardyssey eBay collector (Tiny)

The tested `anniversary_batch.py` source is stored here so collector fixes survive resets and can be reviewed in GitHub. `scripts/price_set_jobs.py` syncs it to `/home/tv/cardyssey-ebay-collector/anniversary_batch.py` **only before a set run starts and when no worker is active**. No credentials or browser profiles are committed.

Run regression tests against the live collector dependencies:

```bash
cd /home/tv/cardyssey-ebay-collector
python3 -m unittest test_anniversary_batch -v
```

Do not loosen language, condition, print-variant or 30-day-sale requirements simply to increase hit rate. `NO_MATCHING_SALES_30D` indicates no accepted matching sale under these checks, not that no listing exists.

`ebay_sold.py` now captures only allowlisted public eBay image thumbnails, stores `image_verified=false`, and leaves every result subject to independent print/condition checks. The admin monitor exposes sample images for review. An image must never override identity filters until a separate validated matching pipeline is available.

## Image identity audit

`image-compare.mjs` computes an edge-based image similarity between each publicly available listing thumbnail and the German TCGdex card scan. It also checks both neighboring printed cards as negative controls. For an automatic **art-only** positive, score must be >= 0.88 and the margin against distractors >= 0.15. It does not identify physical foil, condition or sale validity. A title explicitly naming a conflicting printed number cannot be overridden. Only previously eligible sale records with a confirmed language, Near Mint, and known print variant can be imported. No full-frame resemblance alone authorizes importing prices.

## Persistent sales and rolling prices

`scripts/ebay-collector/price_history.py` stores every verified sold listing as a dated record in `ebay_sold_history`, with assumed-vs-confirmed print and condition flags. A Near Mint quote uses the smallest window containing three or more matching sales: 30d, 90d, 183d, 365d, then 2+ years. If only one or two sales exist, their median is still shown with `low_sample=true`. eBay sale prices are stored as observations, while quote cache base values are divided by 0.92 for the API's Near Mint factor.

`scripts/ebay-collector/reprice_history.py` runs daily at 03:30 via the enabled `cardyssey-ebay-reprice.timer` on the Tiny. It performs no network calls to eBay, so price windows advance independently of new scraping.

Recent complete eBay search reports are reused for up to 24 hours, preserving legitimate sold evidence and recalculating historic results without another browser request. eBay's own sold-listing history limits what can be recovered retrospectively; long-term charts accumulate from the date collection began.

## Automatic incremental refresh (5 monitored German sets)

`cardyssey-ebay-weekly.timer` checks hourly whether one of `30th`, `30th-c`,
`mep`, `sv02`, `sv01` is due, with a **seven-day** interval. The scheduler
launches **one** `price_set_jobs.py start SET --incremental` at a time,
never competing with a manual or active scraper. The current full set run
is not interrupted. A short-term retry on upstream errors does not refresh
cards already successfully checked within the past seven days.

Each card uses `ebay_scan_checkpoint` (or an earlier **fully successful**
sold-page report with a full-history age policy) as the latest completed
search time. The requested eBay search is sorted by recent sold end date;
`--sold-since` uses **two days of overlap**, deduplicates sold item IDs in
Postgres, and excludes older listings from the newly collected report.
The collector stops reading pages at a dated/sorted old-sale boundary. A
missing boundary, undated/out-of-order page, blocked browser, or reached
five-page cap is **incomplete** and cannot advance the cursor. This can
mean a card takes a later retry rather than quietly missing a sale.

A full manual run is still possible from the admin price monitor. Check
`systemctl --user list-timers` and `journalctl --user -u
cardyssey-ebay-weekly.service` for schedule status; existing historical
sale rows are never deleted by an incremental refresh.

## Admin price-review queue (enabled, without auto-hiding)

`ebay_card_review` records a manual state (`AUTO`, `NO_VERIFIED_SALE`,
`OFFER_REVIEW`), a refresh interval of 7/14/30 days, and an optional note.
The admin view offers these controls through the authenticated
`/api/admin/price-review` route. This classification does not touch sale
history or prices and currently does **not** hide priced cards.

Multi-selection eBay listings are stored separately in `ebay_offer_reference`
with `MULTI_SELECT_UNVERIFIED_CARD`. Their displayed prices and listing-wide
sale counters are **never** treated as sold prices of a specific physical
print. The backfill importer reads archived search reports once and the
collector records new candidates as it runs. Selection listings cannot
influence eBay medians until individual sale-and-print evidence exists.

The monitor presents actual Near Mint eBay median prices with the API's
0.92 factor applied rather than mistakenly displaying the Mint base value.

## Sold-choice purchase-history identity audit

For eBay multiple-choice/selection listings, the collector opens the existing
buyer-privacy-safe eBay `bin/purchaseHistory?item=...` page **using the existing
serial Selenium browser**, and only reads its purchase history table. No eBay
buyer usernames, cookies or entire pages are saved. A shared per-listing
`ebay_purchase_history_check` cache prevents repeated browser fetches for
cards appearing in the same listing; completed checks are refreshed weekly,
blocked/unavailable checks may retry after one day.

A purchase-history row is importable only when the specific purchased **print
name and exact numerator/denominator**, a **visible EUR unit price**, quantity,
purchase date, set and German language agree. Price text such as "Als
Aktionsangebot verkauft" never becomes an invented price; listing-level
asking prices and total-sold counters are ignored. Sale IDs are deterministic
and duplicate-protected. Quantity is retained for audit but does not
multiply a single observed transaction into fabricated sales. Condition
and Normal print can still be *assumed* under the documented policy; explicit
Reverse and other mismatches stay separate.

When a search for card A exposes an itemized purchase of card B, the collector
may also import the evidenced sale for card B in the **same verified set**,
without waiting for B's name to appear in eBay's search title. Every
cross-card import records its target and status in the original card's search
audit. Successful imports are visible in the shared history and current median.

In the Admin price monitor, "Prüfbedarf" filters cards needing human review,
and individual offer references show checked history variants, sold-price text,
status and a link to eBay's purchase history. Explicit admin review flags and
7/14/30 day snoozes remain independent from sale-price data. Automatic hiding
of cards with prices remains **disabled** until the initial data-quality audit.

If eBay blocks purchase history or omits a paid amount, the listing remains
a reference only. It is not a price. Weekly and manual full runs share the same
one-browser lock and preserve historical observations.

## Acquisition source routing and repeatable human corrections

German cards marked exactly `Häufig` or `Ungewöhnlich` use the existing
variant-matched TCGdex/Cardmarket price route. They are excluded from the
normal eBay review queue and skipped by automatic eBay set scans, including
weekly incremental runs. Rarer, illustration, holo-rare, EX/ultra, and promo
cards remain eBay eligible. Existing historical eBay transactions are kept,
and an authorized manual eBay test remains possible. No PriceCharting values
are chosen as a fallback for bulk cards.

`ebay_listing_feedback` stores admin decisions by card ID + sold listing ID,
including the exact listing title and optional explanation. It **never** edits
existing transaction/price rows or teaches the parser automatically. The
structured examples are meant to be grouped into parser rule changes and
regression tests, to prevent an overly broad correction from breaking
unrelated cards. Valid categories: wrong card, valid specific sale,
selection listing, wrong print, unknown paid price, or other.
