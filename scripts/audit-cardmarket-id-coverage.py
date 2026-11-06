#!/usr/bin/env python3
"""Audits offline Cardmarket IDs against the official feed; never changes prices."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

URL="https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json"
CACHE=Path("/home/tv/.local/state/cardyssey-queue/price-feeds")/(hashlib.sha256(URL.encode()).hexdigest()+".json")
QUEUE=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
OUT=Path("/home/tv/cardshop/reports")
OUT.mkdir(parents=True,exist_ok=True)
feed=json.loads(CACHE.read_text())
products={str(p["idProduct"]):p for p in feed["products"]}
summary={"feed_date":feed.get("createdAt"),"official_product_count":len(products),"languages":{}}
for lang in ("de","en"):
    counts=Counter()
    exceptions=[]
    with (QUEUE/f"queue-{lang}.csv").open(encoding="utf-8-sig",newline="") as src:
        for r in csv.DictReader(src):
            counts["variants"]+=1
            ids=sorted({x.strip() for x in r["cardmarket_ids"].split(",") if x.strip().isdigit()})
            if not ids:
                counts["no_candidate"]+=1
                status="NO_CANDIDATE"
            elif len(ids)>1:
                counts["multiple_candidates"]+=1
                status="MULTIPLE_CANDIDATES"
            elif ids[0] not in products:
                counts["candidate_not_in_official_catalog"]+=1
                status="NOT_IN_OFFICIAL_CATALOG"
            else:
                counts["one_candidate_in_official_catalog"]+=1
                status="ONE_OFFICIAL_PRODUCT_CANDIDATE"
                if r["candidate_status"]=="SINGLE_SET_PRODUCT":
                    counts["verified_set_candidate"]+=1
                elif r["candidate_status"]=="NO_CATALOG_CANDIDATE":
                    counts["source_card_id_candidate"]+=1
            if status!="ONE_OFFICIAL_PRODUCT_CANDIDATE":
                exceptions.append({"language":lang,"card_id":r["cardyssey_karte"],
                  "variant_id":r["variante_id"],"set_id":r["set_id"],
                  "number":r["kartennummer"],"name":r["kartenname_suche"],
                  "status":status,"candidate_ids":",".join(ids),
                  "candidate_product_names":" | ".join(products[x].get("name","") for x in ids[:5] if x in products)})
    summary["languages"][lang]=dict(counts)
    with (OUT/f"cardmarket-id-exceptions-{lang}.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["language","card_id","variant_id","set_id","number","name","status","candidate_ids","candidate_product_names"])
        w.writeheader();w.writerows(exceptions)
path=OUT/"cardmarket-id-coverage.json"
path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
