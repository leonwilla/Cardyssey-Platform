#!/usr/bin/env python3
"""Prioritize DE/EN browser work while retaining feed-only catalog variants."""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse
import csv
import json
import os
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

from cardmarket_browser_queue import browser_scan_tier, human_confirmed_print_keys

def db_rows(language='de'):
    if language not in ('de','en'):raise ValueError('Invalid language')
    sql = """SELECT json_agg(json_build_object(
        'card_id',p.card_id,'variant_id',p.variant_id,
        'status',p.resolution_status,'price',p.base_eur,'source',p.source))
    FROM tcg_price_cache p
    WHERE p.language_code='{language}'""".format(language=language)
    result = subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
         "-At","-c",sql], capture_output=True,text=True,check=True)
    return json.loads(result.stdout.strip() or "[]", parse_float=Decimal) or []

def prioritize(rows, cache, confirmed_keys=()):
    lookup = {(r["card_id"], r["variant_id"]): r for r in cache}
    for row in rows:
        key = (row["cardyssey_karte"], row["variante_id"])
        state = lookup.get(key, {})
        value = Decimal(str(state.get("price") or 0))
        missing = state.get("status") != "PRICE_FOUND" or not value.is_finite() or value <= 0
        row["existing_price_eur"] = format(value, "f") if not missing else ""
        row["existing_source"] = str(state.get("source") or "")
        row["needs_price"] = "YES" if missing else "NO"
        row["scan_tier"] = browser_scan_tier(row, key in confirmed_keys)
        # The weekly guide comparison re-establishes safe delta skips.
        row["delta_browser_skip"] = "NO"
        row["delta_reason"] = ""
    rows.sort(key=lambda r:(r["scan_tier"],r.get("prioritaet",""),
                            r.get("set_id",""),r["cardyssey_karte"],r["variante_id"]))
    return rows

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--queue",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument('--language',choices=('de','en'),default='de')
    args=parser.parse_args()
    with args.queue.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    confirmed_keys=human_confirmed_print_keys(args.queue.parent,args.language)
    prioritized=prioritize(rows,db_rows(args.language),confirmed_keys)
    if len(prioritized)!=len(rows):raise ValueError("lost queue rows")
    unique={(r["cardyssey_karte"],r["variante_id"]) for r in prioritized}
    if len(unique)!=len(rows):raise ValueError("duplicate variant key")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8-sig", newline="", dir=args.output.parent, delete=False
    ) as f:
        tmp = Path(f.name)
        try:
            writer = csv.DictWriter(f, fieldnames=prioritized[0].keys())
            writer.writeheader()
            writer.writerows(prioritized)
            f.close()
            os.replace(tmp, args.output)
        finally:
            tmp.unlink(missing_ok=True)
    print(json.dumps({"rows":len(prioritized),
                      "missing_first":sum(x["needs_price"]=="YES" for x in prioritized),
                      "browser_eligible":sum(x["scan_tier"]!=4 for x in prioritized),
                      "feed_only":sum(x["scan_tier"]==4 for x in prioritized),
                      "already_priced":sum(x["needs_price"]=="NO" for x in prioritized),
                      "first_cards":[x["cardyssey_karte"] for x in prioritized[:27]]},
                     ensure_ascii=False))
if __name__=="__main__":main()
