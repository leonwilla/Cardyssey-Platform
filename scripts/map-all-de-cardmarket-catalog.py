#!/usr/bin/env python3
"""Catalog-wide German Cardmarket product crosswalk (no unverified price writes).

Batch-match distinct cards against the official product feed and validated
expansion mappings. Store candidates separately from exact print identity.
"""
import argparse
import collections
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from price_feed_client import fetch_json
from price_identity_validation import split_by_verified_expansion
from importlib.machinery import SourceFileLoader

PRODUCT_URL="https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json"
PRICE_URL="https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"
ROOT=Path(__file__).resolve().parent

def db(sql):
    proc=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-X","-v","ON_ERROR_STOP=1",
                         "-U","cardyssey","-d","cardyssey","-At"],
                        input=sql,text=True,capture_output=True,check=True,timeout=120)
    return proc.stdout.strip()

def quote(x):
    return "'"+str(x).replace("'","''")+"'"

def sem_name(v):
    import re
    s=str(v or "").lower().replace("’","'").replace("☆"," gold star ").replace("★"," gold star ")
    s=re.sub(r"δ\s*delta\s*species"," delta species ",s)
    s=s.replace("δ"," delta species ")
    s=re.sub(r"\bgold\s+star\b","goldstar",s)
    s=re.sub(r"\bdelta\s+species\b","deltaspecies",s)
    s=re.sub(r"\[[^\]]*\]","",s)
    s=re.sub(r"\s*\([^)]*\)\s*$","",s)
    return re.sub(r"[^a-z0-9]+","",s)

def calculate_set_map(en_cards,products):
    names=collections.defaultdict(list)
    for card in en_cards:
        key=sem_name(card.get("name"))
        if key:names[card["set_id"]].append(key)
    by_exp=collections.defaultdict(collections.Counter)
    for product in products:
        name=sem_name(product.get("name"))
        if name:by_exp[str(product.get("idExpansion"))][name]+=1
    maps={}
    for sid,card_names in names.items():
        wanted=collections.Counter(card_names)
        scored=[]
        for exp,available in by_exp.items():
            count=sum(min(n,available.get(name,0)) for name,n in wanted.items())
            if count:scored.append((count,count/max(1,len(card_names)),exp))
        scored.sort(reverse=True)
        if not scored:continue
        first=scored[0]
        second=scored[1] if len(scored)>1 else (0,0,None)
        if first[1]>=0.90 and (first[0]-second[0]>=3 or first[1]>=0.98):
            maps[sid]=first[2]
    return maps

def candidates_for_card(card,by_exp_name,set_map):
    eid=set_map.get(card["set_id"])
    if eid is None:return [],"SET_NOT_VERIFIED"
    names=by_exp_name.get((eid,sem_name(card.get("english_name"))),[])
    if not names:return [],"NAME_NOT_FOUND_IN_VERIFIED_SET"
    ids=sorted({str(p["idProduct"]) for p in names})
    return ids,"SINGLE_SET_PRODUCT" if len(ids)==1 else "MULTIPLE_SET_PRODUCTS"

def collect():
    products=fetch_json(PRODUCT_URL).get("products") or []
    price_rows=fetch_json(PRICE_URL).get("priceGuides") or []
    priced_ids={str(p.get("idProduct")) for p in price_rows}
    data=db("""SELECT COALESCE(jsonb_agg(to_jsonb(x)),'[]'::jsonb) FROM (
        SELECT card_id,set_id,local_id,name
        FROM catalog_cards_mirror WHERE language_code='en') x;""")
    en=json.loads(data)
    data=db("""SELECT COALESCE(jsonb_agg(to_jsonb(x)),'[]'::jsonb) FROM (
        SELECT d.card_id,d.set_id,d.local_id,d.name AS german_name,
            COALESCE(e.name,d.name) AS english_name,
            jsonb_array_length(d.variants) AS variant_count
        FROM catalog_cards_mirror d
        LEFT JOIN catalog_cards_mirror e ON e.language_code='en'
          AND e.set_id=d.set_id AND e.local_id=d.local_id
        WHERE d.language_code='de') x;""")
    de=json.loads(data)
    set_map=calculate_set_map(en,products)
    # Exact, manually confirmed SET-level corrections override fuzzy name
    # overlap. Never turn a set override into a verified foil/print mapping.
    override_file=ROOT.parent/'config/cardmarket-verified-set-overrides.json'
    if override_file.is_file():
        overrides=json.loads(override_file.read_text(encoding='utf-8'))
        known_expansions={str(p.get('idExpansion')) for p in products}
        for set_id,evidence in overrides.items():
            eid=str(evidence.get('expansionId') or '')
            if eid not in known_expansions:raise RuntimeError('Missing verified Cardmarket expansion for '+set_id)
            set_map[set_id]=eid
    names=collections.defaultdict(list)
    for p in products:
        key=sem_name(p.get("name"))
        if key:names[(str(p.get("idExpansion")),key)].append(p)
    rows=[]
    for card in de:
        ids,status=candidates_for_card(card,names,set_map)
        rows.append({"card_id":card["card_id"],"set_id":card["set_id"],
                     "local_id":card["local_id"],"english_name":card["english_name"],
                     "variant_count":card["variant_count"],"set_expansion":set_map.get(card["set_id"]),
                     "product_ids":ids,"with_guide":sum(x in priced_ids for x in ids),
                     "status":status})
    return rows,{"sets_matched":len(set_map),"feed_products":len(products),
                 "guide_products":len(priced_ids)}

DDL="""
CREATE TABLE IF NOT EXISTS cardmarket_catalog_link_candidates (
  language_code text NOT NULL DEFAULT 'de',
  card_id text NOT NULL,
  set_id text NOT NULL,
  printed_number text,
  english_name text,
  provider_expansion_id text,
  provider_product_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  candidate_status text NOT NULL,
  priceguide_candidate_count integer NOT NULL DEFAULT 0,
  catalog_variant_count integer NOT NULL DEFAULT 0,
  checked_at timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY(language_code,card_id)
);
CREATE INDEX IF NOT EXISTS cardmarket_catalog_link_candidates_status_idx
 ON cardmarket_catalog_link_candidates(candidate_status,checked_at);
"""

def apply(rows):
    db(DDL)
    for i in range(0,len(rows),400):
        records=[{"language_code":"de","card_id":r["card_id"],"set_id":r["set_id"],
                  "printed_number":r["local_id"],"english_name":r["english_name"],
                  "provider_expansion_id":r["set_expansion"],"provider_product_ids":r["product_ids"],
                  "candidate_status":r["status"],"priceguide_candidate_count":r["with_guide"],
                  "catalog_variant_count":r["variant_count"]} for r in rows[i:i+400]]
        data=quote(json.dumps(records,ensure_ascii=False,separators=(",",":")))
        sql=f"""
WITH data AS (SELECT jsonb_array_elements({data}::jsonb) AS x),
fields AS (
 SELECT x->>'language_code' AS language_code,x->>'card_id' AS card_id,
 x->>'set_id' AS set_id,x->>'printed_number' AS printed_number,
 x->>'english_name' AS english_name,
 x->>'provider_expansion_id' AS provider_expansion_id,
 x->'provider_product_ids' AS provider_product_ids,
 x->>'candidate_status' AS candidate_status,
 (x->>'priceguide_candidate_count')::integer AS priceguide_candidate_count,
 (x->>'catalog_variant_count')::integer AS catalog_variant_count FROM data)
INSERT INTO cardmarket_catalog_link_candidates
(language_code,card_id,set_id,printed_number,english_name,provider_expansion_id,
 provider_product_ids,candidate_status,priceguide_candidate_count,catalog_variant_count)
SELECT language_code,card_id,set_id,printed_number,english_name,
 provider_expansion_id,provider_product_ids,candidate_status,
 priceguide_candidate_count,catalog_variant_count FROM fields
ON CONFLICT(language_code,card_id) DO UPDATE SET
 set_id=EXCLUDED.set_id, printed_number=EXCLUDED.printed_number,
 english_name=EXCLUDED.english_name,provider_expansion_id=EXCLUDED.provider_expansion_id,
 provider_product_ids=EXCLUDED.provider_product_ids,candidate_status=EXCLUDED.candidate_status,
 priceguide_candidate_count=EXCLUDED.priceguide_candidate_count,
 catalog_variant_count=EXCLUDED.catalog_variant_count,checked_at=NOW();
"""
        db(sql)
    # Stage a unique product bucket as SOURCE_ONLY. This is a product pointer,
    # NOT verified condition/foil/stamp identity and cannot publish a price.
    # Existing verified routes or TCGplayer routes are left untouched.
    db('''
INSERT INTO price_source_routing
(language_code,card_id,variant_id,primary_provider,provider_product_id,
 source_evidence,verification_state,refresh_days,fallback_provider,
 next_attempt_at)
SELECT p.language_code,p.card_id,p.variant_id,'CARDMARKET',
       link.provider_product_ids->>0,
       'Official catalogue: unique name within high-confidence expansion; print unverified',
       'SOURCE_ONLY',
       CASE WHEN p.resolution_status<>'PRICE_FOUND' OR p.base_eur>=20 THEN 7
            WHEN c.rarity IN ('Häufig','Ungewöhnlich') THEN 30
            ELSE 14 END,
       CASE WHEN p.source IN ('TCGCSV_TCGPLAYER','TCGDEX_TCGPLAYER')
            THEN p.source ELSE 'TCGDEX' END,
       NOW()
FROM cardmarket_catalog_link_candidates link
JOIN tcg_price_cache p ON p.card_id=link.card_id AND p.language_code=link.language_code
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
WHERE link.language_code='de' AND link.candidate_status='SINGLE_SET_PRODUCT'
 AND jsonb_array_length(link.provider_product_ids)=1
ON CONFLICT(language_code,card_id,variant_id) DO NOTHING;
''')

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    p.add_argument("--report",type=Path,default=Path("/tmp/cardyssey-all-de-cardmarket-catalog-report.json"))
    args=p.parse_args()
    rows,feed=collect()
    if args.apply:apply(rows)
    counts=dict(collections.Counter(r["status"] for r in rows))
    summary={"checked_at":datetime.now(timezone.utc).isoformat(),
             "applied":args.apply,"distinct_de_cards":len(rows),
             "total_de_variants":sum(r["variant_count"] for r in rows),
             "candidate_statuses":counts,"cards_with_any_candidates":sum(bool(r["product_ids"]) for r in rows),
             "variants_with_any_candidate":sum(r["variant_count"] for r in rows if r["product_ids"]),
             "note":"Catalog matches are candidate product buckets, NOT verified German NM print prices.",
             **feed}
    args.report.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__": main()
