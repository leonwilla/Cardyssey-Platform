#!/usr/bin/env python3
"""Audit all German physical variants against the official Cardmarket price guide.

Bulk stage only: catalogue-level asking/trend data is never an independently
verified German/NM/edition/stamp-specific price. Preserve production values.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse,collections,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
from price_feed_client import fetch_json

URL="https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"

def db(sql):
    p=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-X","-v","ON_ERROR_STOP=1",
                      "-U","cardyssey","-d","cardyssey","-At"],input=sql,
                     capture_output=True,text=True,check=True,timeout=120)
    return p.stdout.strip()

def quote(v):
    return "'"+str(v).replace("'","''")+"'"

DDL="""
CREATE TABLE IF NOT EXISTS cardmarket_de_variant_price_audit (
 card_id text NOT NULL,
 variant_id text NOT NULL,
 product_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
 selected_product_id text,
 status text NOT NULL,
 guide_key text,
 guide_value_eur numeric(14,4),
 prior_source text,
 prior_value_eur numeric(14,4),
 is_special boolean NOT NULL DEFAULT FALSE,
 checked_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(card_id,variant_id)
);
CREATE INDEX IF NOT EXISTS cardmarket_de_variant_price_audit_status
 ON cardmarket_de_variant_price_audit(status,checked_at);
"""

def select_value(guide,is_holo):
    keys=("trend-holo","avg7-holo","avg30-holo","avg-holo") if is_holo else ("trend","avg7","avg30","avg")
    for key in keys:
        value=guide.get(key)
        try:
            price=float(value)
            if 0<price<1e7:return key,round(price,4)
        except (ValueError,TypeError):pass
    return None,None

def calculate(rows,prices):
    results=[]
    for row in rows:
        candidates=row.get("product_ids") or []
        variant=row.get("variant") or {}
        special=bool(variant.get("foil") or variant.get("stamps") or variant.get("subtype"))
        foil=(str(variant.get("type") or "").lower() in ("holo","reverse") or
              str(variant.get("legacyVariant") or row.get("legacy_variant") or "").upper() in ("HOLO","REVERSE") or
              bool(variant.get("foil")))
        status="NO_VERIFIED_EXPANSION_OR_NAME"
        selected=None
        key=None
        value=None
        if len(candidates)>1:
            status="MULTIPLE_PRODUCT_CANDIDATES"
        elif len(candidates)==1:
            selected=str(candidates[0])
            guide=prices.get(selected)
            if guide is None:status="PRODUCT_HAS_NO_GUIDE"
            else:
                key,value=select_value(guide,foil)
                if value is None:status="GUIDE_VALUE_MISSING_FOR_PRINT"
                elif special:status="SPECIAL_PRINT_IDENTITY_UNVERIFIED"
                elif foil and row.get("variant_count",0)>1:
                    status="HOLO_REVERSE_SPLIT_UNVERIFIED"
                else:status="GUIDE_CANDIDATE_NOT_LANGUAGE_NM_VERIFIED"
        results.append(dict(card_id=row["card_id"],variant_id=row["variant_id"],
                            product_ids=candidates,selected_product_id=selected,
                            status=status,guide_key=key,guide_value_eur=value,
                            prior_source=row.get("source"),prior_value_eur=row.get("price"),
                            is_special=special))
    return results

def apply(results):
    db(DDL)
    for i in range(0,len(results),400):
        payload=quote(json.dumps(results[i:i+400],ensure_ascii=False,separators=(",",":")))
        db(f"""
WITH incoming AS (SELECT jsonb_array_elements({payload}::jsonb) AS x),
fields AS (
 SELECT x->>'card_id' AS card_id,x->>'variant_id' AS variant_id,
 x->'product_ids' AS product_ids,x->>'selected_product_id' AS selected_product_id,
 x->>'status' AS status,x->>'guide_key' AS guide_key,
 (x->>'guide_value_eur')::numeric AS guide_value_eur,
 x->>'prior_source' AS prior_source,(x->>'prior_value_eur')::numeric AS prior_value_eur,
 (x->>'is_special')::boolean AS is_special FROM incoming)
INSERT INTO cardmarket_de_variant_price_audit
(card_id,variant_id,product_ids,selected_product_id,status,guide_key,
 guide_value_eur,prior_source,prior_value_eur,is_special)
SELECT card_id,variant_id,product_ids,selected_product_id,status,guide_key,
 guide_value_eur,prior_source,prior_value_eur,is_special FROM fields
ON CONFLICT(card_id,variant_id) DO UPDATE SET
 product_ids=EXCLUDED.product_ids,selected_product_id=EXCLUDED.selected_product_id,
 status=EXCLUDED.status,guide_key=EXCLUDED.guide_key,
 guide_value_eur=EXCLUDED.guide_value_eur,prior_source=EXCLUDED.prior_source,
 prior_value_eur=EXCLUDED.prior_value_eur,is_special=EXCLUDED.is_special,
 checked_at=NOW();""")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    p.add_argument("--report",type=Path,default=Path("/tmp/cardyssey-de-full-price-audit.json"))
    args=p.parse_args()
    guide=fetch_json(URL)
    prices={str(g.get("idProduct")):g for g in guide.get("priceGuides") or []}
    query="""
SELECT COALESCE(jsonb_agg(to_jsonb(x)), '[]'::jsonb) FROM (
 SELECT p.card_id,p.variant_id,p.legacy_variant,p.source,p.base_eur AS price,
        COALESCE(link.provider_product_ids,'[]'::jsonb) AS product_ids,
        jsonb_array_length(c.variants) AS variant_count,
        COALESCE((SELECT v FROM jsonb_array_elements(c.variants) AS v
            WHERE v->>'id'=p.variant_id LIMIT 1),'{}'::jsonb) AS variant
 FROM tcg_price_cache p
 JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
 LEFT JOIN cardmarket_catalog_link_candidates link ON link.card_id=p.card_id
  AND link.language_code=p.language_code
 WHERE p.language_code='de'
) x;"""
    rows=json.loads(db(query))
    result=calculate(rows,prices)
    if args.apply:apply(result)
    counts=dict(collections.Counter(x["status"] for x in result))
    report={"checked_at":datetime.now(timezone.utc).isoformat(),
            "variants":len(result),"guide_products":len(prices),
            "statuses":counts,"candidate_with_price":sum(x["guide_value_eur"] is not None for x in result),
            "production_prices_changed":0,
            "warning":"Official guide is not filtered by German NM nor print-specific; candidate pricing staged only."}
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
