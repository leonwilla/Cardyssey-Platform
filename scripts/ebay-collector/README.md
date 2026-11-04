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
