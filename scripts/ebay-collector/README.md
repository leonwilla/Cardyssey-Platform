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
