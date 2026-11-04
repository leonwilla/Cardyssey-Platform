# Cardyssey eBay collector (Tiny)

The tested `anniversary_batch.py` source is stored here so collector fixes survive resets and can be reviewed in GitHub. `scripts/price_set_jobs.py` syncs it to `/home/tv/cardyssey-ebay-collector/anniversary_batch.py` **only before a set run starts and when no worker is active**. No credentials or browser profiles are committed.

Run regression tests against the live collector dependencies:

```bash
cd /home/tv/cardyssey-ebay-collector
python3 -m unittest test_anniversary_batch -v
```

Do not loosen language, condition, print-variant or 30-day-sale requirements simply to increase hit rate. `NO_MATCHING_SALES_30D` indicates no accepted matching sale under these checks, not that no listing exists.

`ebay_sold.py` now captures only allowlisted public eBay image thumbnails, stores `image_verified=false`, and leaves every result subject to independent print/condition checks. The admin monitor exposes sample images for review. An image must never override identity filters until a separate validated matching pipeline is available.
