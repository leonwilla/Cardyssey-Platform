#!/usr/bin/env python3
"""Audit exact TCGdex variant product IDs against public TCGCSV product/price feeds.

Read-only. Never infer a different product's price based on its name alone.
"""
import argparse
import collections
import json
from pathlib import Path
import requests

HEADERS={"User-Agent":"Cardyssey/1.0 (+https://cardyssey.de)","Accept":"application/json"}
GROUPS={"np":1423,"basep":1418,"dpp":1421,"mep":24451,"ex8":1428}
BASE="https://tcgcsv.com/tcgplayer/3"

def fetch_group(group):
    result={}
    for kind in ("products","prices"):
        response=requests.get(f"{BASE}/{group}/{kind}",headers=HEADERS,timeout=20)
        response.raise_for_status()
        result[kind]=response.json().get("results") or []
    return result

def audit(record, catalogue):
    pid=record.get("exact_variant_provider_ids",{}).get("tcgplayer")
    if pid is None:return dict(status="NO_TCGPLAYER_PRODUCT_ID")
    group=GROUPS.get(record["set_code"])
    if group is None:return dict(status="UNMAPPED_PRODUCT_GROUP",product_id=pid)
    feed=catalogue.get(group)
    if not feed:return dict(status="FEED_UNAVAILABLE",product_id=pid,group=group)
    products=[p for p in feed["products"] if str(p.get("productId"))==str(pid)]
    if len(products)!=1:return dict(status="PRODUCT_NOT_IN_GROUP",product_id=pid,group=group)
    prices=[p for p in feed["prices"] if str(p.get("productId"))==str(pid)]
    usable=[p for p in prices if isinstance(p.get("marketPrice"),(int,float)) and p["marketPrice"]>0]
    return dict(status="EXACT_PRODUCT_MARKET_PRICE_AVAILABLE" if usable else
                "EXACT_PRODUCT_HAS_NO_PUBLIC_MARKET_PRICE",
                product_id=pid,group=group,product_name=products[0].get("name"),
                price_rows=prices)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=Path("/tmp/cardyssey-verified-provider-fallback.json"))
    parser.add_argument("--output",type=Path,default=Path("/tmp/cardyssey-exact-product-price-audit.json"))
    args=parser.parse_args()
    items=json.loads(args.input.read_text())["unresolved"]
    groups=sorted({GROUPS[x["set_code"]] for x in items if
                   x.get("exact_variant_provider_ids",{}).get("tcgplayer") and x["set_code"] in GROUPS})
    feeds={}
    failed={}
    for group in groups:
        try:feeds[group]=fetch_group(group)
        except (requests.RequestException,ValueError) as exc:failed[str(group)]=str(exc)
    audits=[{**{k:x[k] for k in ("language","card_id","variant_id","set_code")},**audit(x,feeds)}
            for x in items if x.get("exact_variant_provider_ids",{}).get("tcgplayer")]
    counts=dict(collections.Counter(x["status"] for x in audits))
    result=dict(source="TCGCSV exact product ID matched to product catalogue",
                warning="Read-only USD provider quotes; cannot be applied without checking subtype, language, condition and print",
                examined=len(audits),groups=groups,feed_failures=failed,counts=counts,results=audits)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(examined=len(audits),counts=counts,feed_failures=failed),ensure_ascii=False))

if __name__=="__main__":main()
