#!/usr/bin/env python3
"""Refresh public Cardmarket catalog and Cardyssey review worklist weekly.

Does not modify published prices, route mappings, or human confirmations.
Price guide weekly refresh remains a separate, existing job.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from price_feed_client import fetch_json

ROOT=Path("/home/tv/cardshop")
BASE=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
PRODUCT_URL="https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json"
PRICE_URL="https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"
def run(*args):
    p=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(str(args[:2])+": "+p.stderr[-1000:]+p.stdout[-300:])
    return p.stdout.strip()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    products=fetch_json(PRODUCT_URL,max_age=20*3600)
    prices=fetch_json(PRICE_URL,max_age=20*3600)
    if len(products.get("products") or [])<50000 or len(prices.get("priceGuides") or [])<50000:
        raise RuntimeError("Official feed incomplete; previous queues and reviews preserved")
    # Recompute the expansion crosswalk from multiple distinct physical
    # card-product IDs BEFORE queue generation. Never trust name overlaps.
    crosswalk=json.loads(run(ROOT/'scripts/map-all-de-cardmarket-catalog.py',
        *(['--apply'] if a.apply else [])))
    set_audit=json.loads(run(ROOT/'scripts/cardmarket-set-identity-audit.py'))
    report={"set_crosswalk":crosswalk,"set_audit":set_audit,"product_catalog_date":products.get("createdAt"),"guide_date":prices.get("createdAt"),
            "products":len(products["products"]),"guide_items":len(prices["priceGuides"])}
    for lang in ("de","en"):
        result=run(ROOT/"scripts/export-cardmarket-full-queue.py","--language",lang,"--output",BASE/f"queue-{lang}.csv")
        report[lang]=json.loads(result)
        # Critical: exporter emits needs_price=YES as a placeholder. Never
        # feed that unprioritized raw CSV to the browser scanner again.
        report[lang]['prioritization']=json.loads(run(
            ROOT/'scripts/prioritize-cardmarket-scan-queue.py',
            '--language',lang,'--queue',BASE/f'queue-{lang}.csv',
            '--output',BASE/f'queue-{lang}.csv'))
    result=run(ROOT/"scripts/build-cardmarket-identity-worklist.py")
    report["worklist"]=json.loads(result)
    # Set-verified catalog singleton hints reduce costly translated-name
    # searches. These are CANDIDATES only, never print-verified prices.
    for lang in ('de','en'):
        report[lang]['lookup_hints']=json.loads(run(
            ROOT/'scripts/cardmarket-enrich-queue-hints.py','--language',lang))
    report["review_stage"]=json.loads(run(ROOT/"scripts/sync-cardmarket-print-review.py",*(["--apply"] if a.apply else [])))
    # Existing OPEN rows need the exact same per-variant corrections; the
    # review importer only stages complex cases and otherwise leaves old
    # multi-product candidates visible forever.
    report['variant_candidate_reconciliation']=json.loads(run(
        ROOT/'scripts/reconcile-cardmarket-variant-identity-review.py',
        *(['--apply'] if a.apply else [])))
    # Durable exact-card URL leads supplied by the collector owner. Import
    # AFTER regenerating/merging queue columns; do not promote print prices.
    for lang in ('de','en'):
        report[lang]['known_page_hints']=json.loads(run(
            ROOT/'scripts/cardmarket-apply-print-page-hints.py','--language',lang))
    report["mode"]="apply" if a.apply else "dry-run"
    (ROOT/"reports/cardmarket-identity-pipeline-latest.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"mode":report["mode"],"de":report["de"]["variants"],
      "en":report["en"]["variants"],"stage":report["review_stage"]["rows"],
      "catalog_date":report["product_catalog_date"]},ensure_ascii=False))
if __name__=="__main__":
    main()
