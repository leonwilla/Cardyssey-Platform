#!/usr/bin/env python3
"""Recover actionable Cardmarket verification jobs from a failed browser run.

This is offline: no HTTP or price writes. Exact catalogue product IDs are
*not* evidence of the requested language, near-mint condition or special print.
"""
import argparse
import collections
import csv
import json
from pathlib import Path

def recovery(queue, observations):
    latest={}
    for line in observations:
        try:
            r=json.loads(line)
            if r.get("key"):latest[r["key"]]=r
        except (ValueError,TypeError):
            continue
    result=[]
    stats=collections.Counter()
    for row in queue:
        key=f'{row["cardyssey_karte"]}|{row["variante_id"]}'
        old=latest.get(key,{})
        if old.get("status")!="ERROR":continue
        ids=list(dict.fromkeys(i.strip() for i in row["cardmarket_ids"].split(",") if i.strip().isdigit()))
        stats["failed"]+=1
        if len(ids)==1:
            kind="UNIQUE_CATALOG_PRODUCT_REQUIRES_PRINT_VERIFICATION"
            stats["single_product"]+=1
        elif len(ids)>1:
            kind="AMBIGUOUS_PRODUCTS_REQUIRES_IDENTITY_REVIEW"
            stats["ambiguous_product"]+=1
        else:
            kind="NO_CATALOG_PRODUCT"
            stats["no_product"]+=1
        result.append({
            "key":key,"card_id":row["cardyssey_karte"],
            "variant_id":row["variante_id"],
            "set_id":row["set_id"],"printed_number":row["kartennummer"],
            "english_name":row["kartenname_suche"],
            "product_ids":",".join(ids),"category":kind,
            "special":bool(row["sonderdruck"] or row["foil"] or row["stempel"]),
            "price_source":row["existing_source"],
            "existing_price_eur":row["existing_price_eur"],
            "requires_de_nm_variant_verification":True,
        })
    return result,stats

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",type=Path,required=True)
    p.add_argument("--observations",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    with a.queue.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    recovered,stats=recovery(rows,a.observations.read_text(encoding="utf-8-sig").splitlines())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    temp=a.output.with_suffix(".tmp")
    temp.write_text(json.dumps({"summary":dict(stats),"records":recovered,
      "policy":"No candidate is certified as German NM or exact print by this report; no production prices changed."},
      ensure_ascii=False,indent=2))
    temp.replace(a.output)
    print(json.dumps({"summary":dict(stats),"unique_ids":len({
       r["product_ids"] for r in recovered if r["category"].startswith("UNIQUE")}),
       "output":str(a.output)},ensure_ascii=False))

if __name__=="__main__":main()
