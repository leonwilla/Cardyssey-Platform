#!/usr/bin/env python3
"""Admin-only interface for Cardmarket print review; no price publication."""
import argparse
import json
import hashlib
from pathlib import Path
import re
import subprocess
import sys
ALLOWED_LANG={"de","en"}
ALLOWED_STATUS={"CONFIRMED_PRINT","NO_MATCH","DEFERRED"}
def pg(sql):
    proc=subprocess.run(["docker","exec","cardyssey-db","psql","-X","-qAt",
          "-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey","-c",sql],
          capture_output=True,text=True)
    if proc.returncode:raise RuntimeError(proc.stderr[-500:])
    return proc.stdout.strip()
def quote(t):return "'"+str(t).replace("'","''")+"'"
def emit(obj):print(json.dumps(obj,ensure_ascii=False))
def list_cases(data):
    lang=data.get("language","de")
    if lang not in ALLOWED_LANG:raise ValueError("language")
    try:page=max(0,min(5000,int(data.get("page",0))))
    except (ValueError,TypeError):raise ValueError("page")
    term=str(data.get("search") or "").strip()[:90]
    where=f"r.language_code={quote(lang)}"
    if term:
        t=quote("%"+term.replace("%","\\%").replace("_","\\_")+"%")
        where+=f" AND (r.card_name ILIKE {t} OR r.card_id ILIKE {t} OR r.set_id ILIKE {t} OR r.printed_number ILIKE {t})"
    status=str(data.get("status") or "PENDING_REVIEW")
    if status not in ALLOWED_STATUS|{"PENDING_REVIEW","ALL"}:raise ValueError("status")
    if status!="ALL":where+=f" AND r.status={quote(status)}"
    sql=f"""SELECT json_build_object('total',(SELECT count(*) FROM cardmarket_print_identity_review r WHERE {where}),
'items',COALESCE((SELECT json_agg(x) FROM (
 SELECT r.language_code AS language,r.card_id,r.variant_id,r.set_id,r.card_name,
 r.printed_number,r.print_type,r.foil,r.subtype,r.stamps,
 r.candidate_ids,r.matched_set_ids,r.product_names,r.provider_expansion_id,
 r.classification,r.status,r.selected_product_id,r.reviewer_note,c.image_source_url AS card_image_url
 FROM cardmarket_print_identity_review r
 LEFT JOIN catalog_cards_mirror c ON c.language_code=r.language_code AND c.card_id=r.card_id
 WHERE {where}
 ORDER BY CASE WHEN jsonb_array_length(r.matched_set_ids)>0 THEN 0 ELSE 1 END,
 r.set_id,r.printed_number,r.card_id,r.variant_id
 LIMIT 50 OFFSET {page*50}) x),'[]'::json))::text"""
    result=json.loads(pg(sql))
    url="https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"
    cache=Path("/home/tv/.local/state/cardyssey-queue/price-feeds")/(hashlib.sha256(url.encode()).hexdigest()+".json")
    if cache.exists():
        guide=json.loads(cache.read_text(encoding="utf-8"))
        reference={str(p["idProduct"]):p for p in guide.get("priceGuides") or []}
        result["guide_date"]=guide.get("createdAt")
        for row in result.get("items") or []:
            row["reference_values"]={pid:{
              "avg30":reference[pid].get("avg30"),
              "avg30_holo":reference[pid].get("avg30-holo"),
              "trend":reference[pid].get("trend"),
              "trend_holo":reference[pid].get("trend-holo")
            } for pid in (row.get("matched_set_ids") or [])[:15] if pid in reference}
    emit(result)
def update_case(data):
    lang=data.get("language")
    card=data.get("cardId")
    variant=data.get("variantId")
    status=data.get("status")
    pid=str(data.get("productId") or "")
    note=str(data.get("note") or "").strip()
    acknowledged=data.get("exactPrintConfirmed") is True
    if lang not in ALLOWED_LANG or status not in ALLOWED_STATUS or not card or not variant:
        raise ValueError("invalid identity or status")
    if len(card)>128 or len(variant)>128 or len(note)>500:
        raise ValueError("input length")
    if status=="CONFIRMED_PRINT" and (not acknowledged or not re.fullmatch("[0-9]{3,12}",pid)):
        raise ValueError("confirm exact print and select matching product")
    if status!="CONFIRMED_PRINT":pid=""
    # DB WHERE only allows candidate IDs belonging to checked set; no guide price writes.
    sql=f"""UPDATE cardmarket_print_identity_review SET
       status={quote(status)}, selected_product_id={quote(pid) if pid else 'NULL'},
       reviewer_note={quote(note)},reviewed_at=NOW()
     WHERE language_code={quote(lang)} AND card_id={quote(card)}
       AND variant_id={quote(variant)} AND status IN ('PENDING_REVIEW','DEFERRED')
       AND ({quote(status)}<>'CONFIRMED_PRINT' OR
         (matched_set_ids ? {quote(pid)} AND candidate_ids ? {quote(pid)}))
     RETURNING card_id;"""
    result=pg(sql)
    if result!=card:raise ValueError("case not found, already reviewed, or product not matched to set")
    emit({"ok":True,"cardId":card,"status":status})
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--action",choices=["list","review"],required=True)
    opt=a.parse_args()
    try:
        data=json.load(sys.stdin)
        if not isinstance(data,dict):raise ValueError("payload")
        if opt.action=="list":list_cases(data)
        else:update_case(data)
    except (ValueError,TypeError,json.JSONDecodeError) as e:
        emit({"error":str(e)[:250]});sys.exit(2)
    except (OSError,RuntimeError) as e:
        print(str(e)[:500],file=sys.stderr);sys.exit(3)
if __name__=="__main__":main()
