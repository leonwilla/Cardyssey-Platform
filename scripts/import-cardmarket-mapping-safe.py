#!/usr/bin/env python3
"""Safely stage Cardmarket browser ID/URL observations in existing routing.

Only confirmed browser records with a valid URL and an eligible candidate ID are accepted.
Never writes price values, never promotes candidate evidence to verified variant identity.
Preserves existing verified rows, conflicting IDs, and other primary providers.
"""
import argparse
import csv
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

def valid_url(url, lang):
    try:
        p=urlsplit(url)
        return (p.scheme=="https" and p.netloc=="www.cardmarket.com"
                and p.path.startswith(f"/{lang}/Pokemon/Products/Singles/"))
    except ValueError:
        return False

def load_queue(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return {(r["cardyssey_karte"],r["variante_id"]):r for r in csv.DictReader(f)}

def collect(files, queue, language):
    found={}
    reasons=Counter()
    for path in files:
        with path.open(encoding="utf-8-sig") as f:
            for line in f:
                try:
                    r=json.loads(line)
                    key=(str(r.get("card_id") or ""),str(r.get("variant_id") or ""))
                    q=queue.get(key)
                    pid=str(r.get("product_id") or "")
                    url=str(r.get("url") or "").split("?")[0]
                    if not q:
                        reasons["NOT_IN_QUEUE"]+=1
                        continue
                    if r.get("language",language)!=language or r.get("identity_confirmed") is not True:
                        reasons["UNCONFIRMED"]+=1
                        continue
                    if not pid.isdigit() or not valid_url(url,language):
                        reasons["INVALID_ID_OR_URL"]+=1
                        continue
                    allowed={x.strip() for x in (q.get("cardmarket_ids") or "").split(",")}
                    if pid not in allowed:
                        reasons["ID_NOT_IN_CANDIDATES"]+=1
                        continue
                    if q.get("known_url") and q["known_url"].split("?")[0]!=url:
                        reasons["URL_CONFLICT"]+=1
                        continue
                    found[key]={"language_code":language,"card_id":key[0],"variant_id":key[1],
                                "product_id":pid,"url":url}
                except (json.JSONDecodeError, KeyError, TypeError):
                    reasons["BAD_RECORD"]+=1
    return list(found.values()), reasons

SQL=r"""
WITH incoming AS (
 SELECT item->>'language_code' AS language_code,
        item->>'card_id' AS card_id,
        item->>'variant_id' AS variant_id,
        item->>'product_id' AS product_id,
        item->>'url' AS product_url
 FROM jsonb_array_elements({payload}::jsonb) item
), eligible AS (
 SELECT i.* FROM incoming i
 JOIN catalog_cards_mirror c ON c.language_code=i.language_code AND c.card_id=i.card_id
 WHERE EXISTS (SELECT 1 FROM jsonb_array_elements(c.variants) v
               WHERE v->>'id'=i.variant_id)
)
INSERT INTO price_source_routing
 (language_code,card_id,variant_id,primary_provider,provider_product_id,
  provider_product_url,source_evidence,verification_state)
SELECT language_code,card_id,variant_id,'CARDMARKET',product_id,product_url,
       'Cardmarket browser product ID and URL matched candidate; print and condition NOT verified',
       'SOURCE_ONLY'
FROM eligible
ON CONFLICT (language_code,card_id,variant_id) DO UPDATE
SET provider_product_id=EXCLUDED.provider_product_id,
    provider_product_url=EXCLUDED.provider_product_url,
    source_evidence=EXCLUDED.source_evidence,
    updated_at=NOW()
WHERE price_source_routing.primary_provider='CARDMARKET'
  AND price_source_routing.verification_state='SOURCE_ONLY'
  AND (price_source_routing.provider_product_id IS NULL
       OR price_source_routing.provider_product_id=EXCLUDED.provider_product_id)
  AND (price_source_routing.provider_product_url IS NULL
       OR price_source_routing.provider_product_url=EXCLUDED.provider_product_url);
"""

def apply(rows):
    for i in range(0,len(rows),100):
        payload=json.dumps(rows[i:i+100],ensure_ascii=False,separators=(",",":")).replace("'","''")
        sql="BEGIN;\n"+SQL.format(payload="'"+payload+"'")+"\nCOMMIT;"
        subprocess.run(["docker","exec","-i","cardyssey-db","psql","-X","-q",
                        "-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
                       input=sql,text=True,check=True,stdout=subprocess.DEVNULL)

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--queue",type=Path,required=True)
    a.add_argument("--results",type=Path,nargs="+",required=True)
    a.add_argument("--language",choices=["de","en"],required=True)
    a.add_argument("--apply",action="store_true")
    args=a.parse_args()
    rows,reasons=collect(args.results,load_queue(args.queue),args.language)
    print(json.dumps({"language":args.language,"valid_observations":len(rows),
                      "rejected":dict(reasons),"applied":args.apply},ensure_ascii=False))
    if args.apply and rows:apply(rows)
if __name__=="__main__":
    main()
