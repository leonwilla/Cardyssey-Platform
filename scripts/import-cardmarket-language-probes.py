#!/usr/bin/env python3
"""Stage language-filtered Cardmarket asking quotes without publishing them.

Input MUST be produced by verify-cardmarket-language-browser-smoke.py.
No tcg_price_cache, routing or collection writes occur here.
"""
import argparse
import json
import subprocess
from decimal import Decimal
from pathlib import Path

ROOT=Path("/home/tv/cardshop")
DEFAULT=ROOT/"reports/cardmarket-language-smoke-results.json"

def clean(rows):
    result=[]
    for row in rows:
        product=str(row.get("product_id") or "")
        lang=row.get("language")
        basis=row.get("basis")
        lo=Decimal(str(row.get("lowest_ask_eur")))
        entry=Decimal(str(row.get("entry_five_median_eur")))
        seen=int(row.get("visible_offers",0))
        validated=int(row.get("verified_sample_rows",0))
        if not product.isdigit() or lang not in ("de","en"):
            raise ValueError("invalid product identity or language")
        if basis!="active_asking_5_lowest_visible_offers_NOT_SOLD_OR_NM_ONLY":
            raise ValueError("unverified price basis")
        if row.get("printing_verified") is not False or row.get("market_wide") is not False:
            raise ValueError("unsafe printing/market flag")
        if validated<5 or seen<validated or lo<=0 or entry<=0:
            raise ValueError("insufficient eligible offers")
        result.append({"product_id":product,"language":lang,"low":str(lo),
                       "entry5":str(entry),"validated":validated,"visible":seen})
    if not result:raise ValueError("empty result")
    if len({(x["product_id"],x["language"]) for x in result})!=len(result):
        raise ValueError("duplicate product-language pair")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=DEFAULT)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    rows=clean(json.loads(args.input.read_text(encoding="utf-8")))
    if args.apply:
        quoted=json.dumps(rows,separators=(",",":")).replace("'","''")
        sql="""WITH incoming AS (
            SELECT x->>'product_id' product_id,x->>'language' language_code,
                   (x->>'low')::numeric low,(x->>'entry5')::numeric entry5,
                   (x->>'validated')::int verified_preview_rows,
                   (x->>'visible')::int visible_offers
            FROM jsonb_array_elements('"""+quoted+"""'::jsonb) x
          )
          INSERT INTO cardmarket_language_offer_samples
            (product_id,language_code,lowest_ask_eur,entry_five_median_eur,
             verified_preview_rows,visible_offers,source_note)
          SELECT product_id,language_code,low,entry5,verified_preview_rows,visible_offers,
                 'Six-card-side browser probe, language + minCondition=2, printing unverified'
          FROM incoming
          ON CONFLICT(product_id,language_code,minimum_condition,sample_date) DO UPDATE SET
            captured_at=NOW(),lowest_ask_eur=EXCLUDED.lowest_ask_eur,
            entry_five_median_eur=EXCLUDED.entry_five_median_eur,
            verified_preview_rows=EXCLUDED.verified_preview_rows,
            visible_offers=EXCLUDED.visible_offers,
            source_note=EXCLUDED.source_note;"""
        subprocess.run(["docker","exec","cardyssey-db","psql","-X","-q","-v","ON_ERROR_STOP=1",
                        "-U","cardyssey","-d","cardyssey","-c",sql],
                       check=True,capture_output=True,text=True)
    print(json.dumps({"validated_records":len(rows),"product_ids":len(set(x["product_id"] for x in rows)),
                      "languages":["de","en"],"staged":args.apply,
                      "published_to_card_cache":False},ensure_ascii=False))

if __name__=="__main__":main()
