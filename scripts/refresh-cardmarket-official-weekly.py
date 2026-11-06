#!/usr/bin/env python3
"""Weekly refresh of already mapped official Cardmarket guide prices.

No scraping or individual card network calls. Exact existing product IDs only.
DE/EN are Cardyssey catalog language labels, not language-filtered guide prices.
"""
import argparse
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from price_feed_client import fetch_json

PRICE_URL="https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"
DETAIL=re.compile(r"Cardmarket product (\d+); key ([A-Za-z0-9_-]+)")
SAFE_KEYS={"avg30","avg30-holo","trend","trend-holo","avg7","avg7-holo","avg","avg-holo","low","low-holo"}
def db(sql,apply=False):
    cmd=["docker","exec"]+(["-i"] if apply else [])+["cardyssey-db","psql","-X","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey","-At","-c",sql] if not apply else ["docker","exec","-i","cardyssey-db","psql","-X","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey","-q"]
    return subprocess.run(cmd,input=(sql if apply else None),capture_output=True,text=True,check=True).stdout

def sql_quote(s):
    return str(s).replace("'","''")

def value_for(guide,oldkey):
    suffix="-holo" if oldkey.endswith("-holo") else ""
    for key in ("avg30"+suffix,"trend"+suffix,"avg7"+suffix,"avg"+suffix,"low"+suffix):
        v=guide.get(key)
        if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0:
            return round(float(v),4),key
    return None,None

def get_rows(lang):
    q=f"""SELECT json_build_object(
      'card_id',p.card_id,'language',p.language_code,'variant_id',p.variant_id,
      'old_price',p.base_eur,'failure_detail',p.failure_detail,
      'variant',v.value
      )::text
      FROM tcg_price_cache p
      JOIN catalog_cards_mirror c ON c.language_code=p.language_code AND c.card_id=p.card_id
      JOIN LATERAL jsonb_array_elements(c.variants) v(value) ON v.value->>'id'=p.variant_id
      WHERE p.language_code='{lang}' AND p.source='CARDMARKET_OFFICIAL'
      ORDER BY p.card_id,p.variant_id"""
    return [json.loads(x) for x in db(q).splitlines() if x.strip()]

def prepare(rows,guide):
    stats={"source_rows":len(rows),"no_stored_id":0,"not_in_guide":0,"no_valid_price":0,
           "ambiguous_variant":0,"ready":0,"avg30":0,"fallback":0}
    updates=[]
    for row in rows:
        m=DETAIL.search(row["failure_detail"] or "")
        if not m or m.group(2) not in SAFE_KEYS:
            stats["no_stored_id"]+=1;continue
        variant=row["variant"] or {}
        # Do not silently assign a generic guide bucket to a special physical printing.
        if variant.get("foil") or variant.get("stamps") or variant.get("subtype"):
            stats["ambiguous_variant"]+=1;continue
        item=guide.get(m.group(1))
        if not item:
            stats["not_in_guide"]+=1;continue
        price,key=value_for(item,m.group(2))
        if price is None:
            stats["no_valid_price"]+=1;continue
        stats["ready"]+=1
        stats["avg30" if key.startswith("avg30") else "fallback"]+=1
        updates.append(dict(card_id=row["card_id"],language=row["language"],
                            variant_id=row["variant_id"],product_id=m.group(1),
                            price=price,guide_key=key,old_price=row["old_price"]))
    return updates,stats

def apply_updates(rows,guide_date):
    for start in range(0,len(rows),250):
        chunk=rows[start:start+250]
        literal=sql_quote(json.dumps(chunk,ensure_ascii=False,separators=(",",":")))
        date=sql_quote(guide_date)
        sql=f"""BEGIN;
WITH incoming AS (
 SELECT x->>'card_id' card_id,x->>'language' language_code,x->>'variant_id' variant_id,
        (x->>'price')::numeric price,x->>'product_id' product_id,x->>'guide_key' guide_key
 FROM jsonb_array_elements('{literal}'::jsonb) x
), changed AS (
 UPDATE tcg_price_cache p
 SET base_eur=i.price,updated_at=NOW(),
     resolution_status='PRICE_FOUND',
     failure_detail='Cardmarket product '||i.product_id||'; key '||i.guide_key||
       '; via weekly-official-guide; aggregate not language-filtered NM offer; feed {date}',
     next_attempt_at=NOW()+INTERVAL '7 days'
 FROM incoming i
 WHERE p.card_id=i.card_id AND p.language_code=i.language_code
   AND p.variant_id=i.variant_id AND p.source='CARDMARKET_OFFICIAL'
   AND p.failure_detail LIKE 'Cardmarket product '||i.product_id||';%'
 RETURNING p.card_id,p.language_code,p.variant_id,p.base_eur
)
INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
SELECT card_id,language_code,variant_id,'CARDMARKET_OFFICIAL',base_eur,NOW() FROM changed;
COMMIT;"""
        db(sql,apply=True)

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--language",choices=("de","en","both"),default="both")
    a.add_argument("--apply",action="store_true")
    a.add_argument("--report",type=Path,default=Path("/home/tv/cardshop/reports/cardmarket-weekly-official.json"))
    args=a.parse_args()
    payload=fetch_json(PRICE_URL,max_age=20*3600)
    prices={str(x["idProduct"]):x for x in (payload.get("priceGuides") or [])}
    stamp=str(payload.get("createdAt") or "")
    if len(prices)<50000 or not stamp:
        raise RuntimeError("Official Cardmarket price guide invalid or empty")
    langs=["de","en"] if args.language=="both" else [args.language]
    report={"guide_date":stamp,"products":len(prices),"mode":"apply" if args.apply else "dry-run",
            "language_specific_prices":False,"languages":{}}
    for lang in langs:
        updates,stats=prepare(get_rows(lang),prices)
        report["languages"][lang]=stats
        if args.apply and updates:
            apply_updates(updates,stamp)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.report.with_suffix(".tmp")
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(args.report)
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()
