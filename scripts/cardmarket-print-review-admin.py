#!/usr/bin/env python3
"""Admin-only interface for Cardmarket print review; no price publication."""
import argparse
import csv
import fcntl
import os
import json
import hashlib
from functools import lru_cache
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

@lru_cache(maxsize=1)
def official_product_details():
    """Official catalog metadata only; none of these fields proves a print/foil."""
    url='https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json'
    cache=Path('/home/tv/.local/state/cardyssey-queue/price-feeds')/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    try:
        data=json.loads(cache.read_text(encoding='utf-8'))
        return {str(x['idProduct']):x for x in data.get('products',[])}
    except (OSError,ValueError,KeyError,TypeError):return {}

def explain_identity(row,products):
    """Only evidence-supported reasons, not guesses based on catalog ID or date."""
    ids=[str(v) for v in (row.get('matched_set_ids') or [])]
    candidates=[]
    for pid in ids:
        raw=products.get(pid,{})
        candidates.append({'id':pid,'name':str(raw.get('name') or 'Name nicht verfügbar'),
            'expansionId':str(raw.get('idExpansion') or ''),
            'metacardId':str(raw.get('idMetacard') or ''),
            'addedAt':str(raw.get('dateAdded') or '')})
    classification=str(row.get('classification') or '')
    special=any([str(row.get('foil') or '').strip(),str(row.get('subtype') or '').strip(),
                str(row.get('stamps') or '').strip() not in ('','[]','null'),
                'REVERSE' in str(row.get('print_type') or '').upper(),
                'HOLO' in str(row.get('print_type') or '').upper()])
    same_metacard=len(candidates)>1 and len({x['metacardId'] for x in candidates})==1 and bool(candidates[0]['metacardId'])
    if len(ids)>1:
        reason=f"{len(ids)} Cardmarket-Produkte gehören zum gleichen geprüften Set."
        if same_metacard: reason+=' Sie teilen sogar dieselbe Metakarten-ID; der Produktfeed nennt keinen belastbaren Druck-Unterschied.'
        else: reason+=' Der Produktfeed löst die Druckvariante nicht eindeutig auf.'
        action='Nicht anhand der ID oder des Aufnahmedatums raten. Erst anhand eindeutiger Produktseiten, Bilder und Kartennummer prüfen; falls dort kein Unterschied erkennbar ist, offenlassen.'
        kind='CATALOG_DUPLICATE'
    elif len(ids)==1 and special:
        reason='Ein Produkt ist dem Set zugeordnet, aber Holo, Reverse, Edition oder Sonderdruck wurde durch die Quelle nicht bestätigt.'
        action='Prüfen, ob genau die angezeigte Druckvariante auf der Cardmarket-Produktseite belegbar ist. Sonst offenlassen.'
        kind='PRINT_UNVERIFIED'
    elif 'SET_NOT_VERIFIED' in classification or 'INFERRED_SET' in classification:
        reason='Das Cardmarket-Set ist noch nicht unabhängig und eindeutig mit dem Cardyssey-Set abgeglichen.'
        action='Setname und Set-Kartennummer abgleichen. Ohne bestätigtes Set keine Produkt-ID zuweisen.'
        kind='SET_UNVERIFIED'
    elif not ids:
        reason='Es liegt kein bestätigter Produktkandidat im richtigen Cardmarket-Set vor.'
        action='Hier gibt es derzeit keine sichere Auswahl; die automatische Suche muss zuerst neue Kandidaten liefern.'
        kind='MISSING_MATCH'
    else:
        reason='Der genaue Kartendruck wurde noch nicht durch eine geeignete Quelle bestätigt.'
        action='Produktseite mit Set, Nummer, Sprache und Druck abgleichen; nur dann bestätigen.'
        kind='PRINT_UNVERIFIED'
    return {'kind':kind,'reason':reason,'action':action,
       'proofAvailable':False, 'sameMetacard':same_metacard,'candidates':candidates}

def sync_queue_identity(language, card_id, variant_id, product_id, base=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')):
    """Make confirmed DB identity visible to next CSV-based browser run.

    Atomic replacement keeps ongoing scans reading their original complete CSV.
    Unverified price data is never changed.
    """
    if language not in ALLOWED_LANG:return False
    path=base/f'queue-{language}.csv'
    if not path.is_file():return False
    lock=base/f'queue-{language}.review.lock'
    with lock.open('a') as lk:
        fcntl.flock(lk,fcntl.LOCK_EX)
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            fields=reader.fieldnames
            rows=list(reader)
        if not fields or 'routing_state' not in fields:return False
        updated=0
        for row in rows:
            if row.get('cardyssey_karte')!=card_id or row.get('variante_id')!=variant_id:continue
            if row.get('cardmarket_ids')!=product_id:
                row['known_url']=''  # Never retain a URL for a different printing.
            row['cardmarket_ids']=product_id
            row['routing_state']='VERIFIED_PRODUCT_ID'
            updated+=1
        if updated!=1:return False
        tmp=path.with_suffix(path.suffix+'.review.tmp')
        try:
            with tmp.open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            os.replace(tmp,path)
        finally:tmp.unlink(missing_ok=True)
        return True
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
    products=official_product_details()
    for row in result.get('items') or []:
        row['diagnosis']=explain_identity(row,products)
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
    # Single SQL statement: the human-confirmed card/print identity is kept
    # in the review table AND assigned to source routing for future scans.
    # Never write a price here. Preserve a different already-verified provider.
    sql=f"""WITH reviewed AS (
      UPDATE cardmarket_print_identity_review SET
        status={quote(status)}, selected_product_id={quote(pid) if pid else 'NULL'},
        reviewer_note={quote(note)},reviewed_at=NOW()
      WHERE language_code={quote(lang)} AND card_id={quote(card)}
        AND variant_id={quote(variant)} AND status IN ('PENDING_REVIEW','DEFERRED')
        AND ({quote(status)}<>'CONFIRMED_PRINT' OR
          (matched_set_ids ? {quote(pid)} AND candidate_ids ? {quote(pid)}))
      RETURNING language_code,card_id,variant_id,selected_product_id
    ), mapped AS (
      INSERT INTO price_source_routing
        (language_code,card_id,variant_id,primary_provider,provider_product_id,
         source_evidence,verification_state,fallback_provider,refresh_days,next_attempt_at)
      SELECT language_code,card_id,variant_id,'CARDMARKET',selected_product_id,
        'Human confirmed exact set, number, language, edition, foil and stamp',
        'VERIFIED_PRODUCT_ID','TCGDEX',7,NOW()
      FROM reviewed WHERE selected_product_id IS NOT NULL
      ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET
        primary_provider='CARDMARKET',
        provider_product_id=EXCLUDED.provider_product_id,
        provider_product_url=CASE
          WHEN price_source_routing.provider_product_id=EXCLUDED.provider_product_id
           AND price_source_routing.primary_provider='CARDMARKET'
          THEN price_source_routing.provider_product_url ELSE NULL END,
        source_evidence=EXCLUDED.source_evidence,
        verification_state='VERIFIED_PRODUCT_ID',
        next_attempt_at=NOW(),updated_at=NOW()
      WHERE price_source_routing.verification_state<>'VERIFIED_PRODUCT_ID'
        OR (price_source_routing.primary_provider='CARDMARKET'
            AND price_source_routing.provider_product_id=EXCLUDED.provider_product_id)
      RETURNING card_id
    )
    SELECT (SELECT COUNT(*) FROM reviewed)::int || ':' ||
           (SELECT COUNT(*) FROM mapped)::int;"""
    result=pg(sql)
    if not result.startswith('1:'):raise ValueError("case not found, already reviewed, or product not matched to set")
    routed=result.endswith(':1') if status=='CONFIRMED_PRINT' else False
    if status=='CONFIRMED_PRINT' and not routed:
        # A different verified primary price source is deliberately preserved.
        emit({"ok":True,"cardId":card,"status":status,
              "sourceRoutingUpdated":False,"routingNote":"Existing verified provider preserved"})
        return
    queue_updated=False
    if routed:
        try:queue_updated=sync_queue_identity(lang,card,variant,pid)
        except (OSError,ValueError):pass  # DB confirmation remains durable; next queue export repairs CSV.
    emit({"ok":True,"cardId":card,"status":status,
          "sourceRoutingUpdated":routed,"scanQueueUpdated":queue_updated})
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
