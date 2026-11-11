#!/usr/bin/env python3
"""Refresh public Cardmarket catalog and Cardyssey review worklist weekly.

Does not modify published prices, route mappings, or human confirmations.
Price guide weekly refresh remains a separate, existing job.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
from cardmarket_game_profile import load_game_profile
from cardmarket_delta_scan import lock_queue_active
from datetime import datetime,timezone
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from price_feed_client import fetch_json

ROOT=Path("/home/tv/cardshop")
BASE=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
GAME=load_game_profile()
PRODUCT_URL=GAME["product_url"]
PRICE_URL=GAME["price_url"]
def run(*args):
    p=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(str(args[:2])+": "+p.stderr[-1000:]+p.stdout[-300:])
    return p.stdout.strip()
def preserve_manual_scan_requests(current_path,previous):
    """Carry forward manually requested scan timestamps after queue export.

    The re-export derives manual flags from currently verified DB routes,
    while the browser queue can contain newer one-time recheck requests.
    Without this preservation a weekly refresh silently drops those requests.
    Only the request timestamp is restored, never a card/price/product mapping.
    """
    if not previous:return {"preserved":0,"oldRequests":0,"unmatched":0}
    with current_path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);headers=reader.fieldnames;rows=list(reader)
    present=set();changed=0
    for row in rows:
        key=(row['cardyssey_karte'],row['variante_id'])
        present.add(key)
        old=previous.get(key)
        if not old:continue
        new=row.get('manual_scan_requested_at') or ''
        old_time=timestamp(old);new_time=timestamp(new)
        if old_time and (not new_time or old_time>new_time):
            row['manual_scan_requested_at']=old
            changed+=1
    vanished=set(previous)-present
    if vanished:raise RuntimeError('Weekly regeneration would lose '+str(len(vanished))+' manually requested variants')
    buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=headers)
    w.writeheader();w.writerows(rows)
    fd,tmp=tempfile.mkstemp(prefix='cm-restore-manual-',suffix='.csv.tmp',dir=current_path.parent)
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(buf.getvalue().encode('utf-8-sig'));out.flush();os.fsync(out.fileno())
        os.replace(tmp,current_path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return {"preserved":changed,"oldRequests":len(previous),"unmatched":0}

def timestamp(value):
    if not value:return None
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:return None

def collect_manual_scan_requests(queue):
    if not queue.exists():return {}
    with queue.open(encoding='utf-8-sig',newline='') as f:
        return {(r['cardyssey_karte'],r['variante_id']):r['manual_scan_requested_at']
             for r in csv.DictReader(f) if r.get('manual_scan_requested_at')}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    # This job rewrites both existing Windows CSV queues. Refuse while a
    # collector is actively writing/reading them; NEVER interrupt the scan.
    lock_queue_active(BASE,datetime.now(timezone.utc))
    earlier_manual={lang:collect_manual_scan_requests(BASE/f'queue-{lang}.csv') for lang in ('de','en')}
    products=fetch_json(PRODUCT_URL,max_age=20*3600)
    prices=fetch_json(PRICE_URL,max_age=20*3600)
    if len(products.get("products") or [])<50000 or len(prices.get("priceGuides") or [])<50000:
        raise RuntimeError("Official feed incomplete; previous queues and reviews preserved")
    # Recompute the expansion crosswalk from multiple distinct physical
    # card-product IDs BEFORE queue generation. Never trust name overlaps.
    crosswalk=json.loads(run(ROOT/'scripts/cardmarket/core/map-all-de-cardmarket-catalog.py',
        *(['--apply'] if a.apply else [])))
    set_audit=json.loads(run(ROOT/'scripts/cardmarket/core/cardmarket-set-identity-audit.py'))
    report={"set_crosswalk":crosswalk,"set_audit":set_audit,"product_catalog_date":products.get("createdAt"),"guide_date":prices.get("createdAt"),
            "products":len(products["products"]),"guide_items":len(prices["priceGuides"])}
    for lang in ("de","en"):
        result=run(ROOT/"scripts/cardmarket/core/export-cardmarket-full-queue.py","--language",lang,"--output",BASE/f"queue-{lang}.csv")
        report[lang]=json.loads(result)
        report[lang]['manualRequestCarryForward']=preserve_manual_scan_requests(
            BASE/f'queue-{lang}.csv',earlier_manual[lang])
        # Critical: exporter emits needs_price=YES as a placeholder. Never
        # feed that unprioritized raw CSV to the browser scanner again.
        report[lang]['prioritization']=json.loads(run(
            ROOT/'scripts/cardmarket/core/prioritize-cardmarket-scan-queue.py',
            '--language',lang,'--queue',BASE/f'queue-{lang}.csv',
            '--output',BASE/f'queue-{lang}.csv'))
    result=run(ROOT/"scripts/cardmarket/core/build-cardmarket-identity-worklist.py")
    report["worklist"]=json.loads(result)
    # Set-verified catalog singleton hints reduce costly translated-name
    # searches. These are CANDIDATES only, never print-verified prices.
    for lang in ('de','en'):
        report[lang]['lookup_hints']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket-enrich-queue-hints.py','--language',lang))
    report["review_stage"]=json.loads(run(ROOT/"scripts/cardmarket/core/sync-cardmarket-print-review.py",*(["--apply"] if a.apply else [])))
    # Existing OPEN rows need the exact same per-variant corrections; the
    # review importer only stages complex cases and otherwise leaves old
    # multi-product candidates visible forever.
    report['variant_candidate_reconciliation']=json.loads(run(
        ROOT/'scripts/cardmarket/core/reconcile-cardmarket-variant-identity-review.py',
        *(['--apply'] if a.apply else [])))
    # The generic exporter intentionally does not promote ambiguous print
    # product IDs. Restore all *independently verified* set-local candidate
    # lists after regeneration; never change a human-approved print or price.
    overrides=json.loads((ROOT/'config/cardmarket-verified-set-overrides.json').read_text(encoding='utf-8'))
    report['verified_expansion_repairs']={}
    for set_id in sorted(overrides):
        report['verified_expansion_repairs'][set_id]=json.loads(run(
            ROOT/'scripts/cardmarket/core/repair-cardmarket-verified-expansions.py','--set',set_id,
            *(['--apply'] if a.apply else [])))
    # Durable exact-card URL leads supplied by the collector owner. Import
    # AFTER regenerating/merging queue columns; do not promote print prices.
    for lang in ('de','en'):
        report[lang]['known_page_hints']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket-apply-print-page-hints.py','--language',lang))
    # Weekly S3 delta gate: applies only after complete queue regeneration
    # and human-approved identity validation; a guide timestamp is NOT a new
    # DE/EN variant price. First run stores a baseline, no speculative skip.
    if a.apply:
        report['delta_scan']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket_delta_scan.py','--apply'))
    # Compact read-only artifacts for safe browser scoring and guide
    # diagnostics; neither may assign prints or write price caches.
    if a.apply:
        report['observed_set_guards']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket-build-observed-set-guards.py',
            '--output',BASE/'observed-set-url-guards.json'))
        report['product_guide_diagnostics']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket-build-guide-diagnostics.py',
            '--output',BASE/'cardmarket-guide-diagnostic.json'))
    if a.apply:
        report['verified_print_mapping_cache']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket-sync-print-mapping-cache.py','--apply'))
        report['metacard_candidate_index']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket-build-metacard-family-index.py',
            '--output',BASE/'cardmarket-metacard-family-index.json'))
        report['cross_language_page_candidates']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket-build-cross-language-page-cache.py',
            '--output',BASE/'cardmarket-cross-language-page-cache.json'))
        # The main queue can be regenerated after a catalog refresh; put
        # exact-print review first again without modifying card/price data.
        report['recovery_priority']=json.loads(run(
            ROOT/'scripts/cardmarket/core/cardmarket-prioritize-recovery-queue.py','--apply'))
    report["mode"]="apply" if a.apply else "dry-run"
    (ROOT/"reports/cardmarket-identity-pipeline-latest.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"mode":report["mode"],"de":report["de"]["variants"],
      "en":report["en"]["variants"],"stage":report["review_stage"]["rows"],
      "catalog_date":report["product_catalog_date"]},ensure_ascii=False))
if __name__=="__main__":
    main()
