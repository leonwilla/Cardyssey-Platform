#!/usr/bin/env python3
"""Recover German NO_PRICE rows that have one unambiguous physical variant.

For a card with exactly one current TCGdex variant, card-level Cardmarket
pricing is unambiguous even when variants_detailed omits its own pricing block.
This script updates the mirror to the current exact variant and seeds that
single price. Pocket sets are excluded because they are not physical TCG cards.
"""
import concurrent.futures, json, math, subprocess, requests

BASE="https://api.tcgdex.net/v2/de/cards"
POCKET_RE_PREFIXES=("A","B")

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def q(s): return s.replace("'","''")

def legacy(t):
    x=t.lower().replace("-","").replace("_","").replace(" ","")
    if x=="reverse": return "REVERSE"
    if x=="holo": return "HOLO"
    if x in ("firstedition","1stedition"): return "FIRST_EDITION"
    return "NORMAL"

def cm_price(card, typ, foil=None):
    cm=((card.get("pricing") or {}).get("cardmarket") or {})
    if not cm: return None
    t=(typ or "").strip().lower()
    holo=t in ("reverse","holo") or bool((foil or "").strip())
    keys=(["trend-holo","avg7-holo","avg30-holo","avg-holo","low-holo"] if holo else []) + ["trend","avg7","avg30","avg","low"]
    for k in keys:
        x=cm.get(k)
        if isinstance(x,(int,float)) and math.isfinite(x) and x>0:
            return float(x)
    return None

targets=db("""SELECT DISTINCT c.card_id
              FROM tcg_price_cache p
              JOIN catalog_cards_mirror c
                ON c.card_id=p.card_id AND c.language_code=p.language_code
              WHERE p.language_code='de'
                AND p.resolution_status='NO_PRICE'
                AND p.variant_id='generated'
                AND NOT (c.set_id ~ '^(A[0-9]|B[0-9])' OR c.set_id='P-A')
              ORDER BY c.card_id""").splitlines()
print(f"targets={len(targets)}",flush=True)

def fetch(cid):
    r=requests.get(f"{BASE}/{cid}",headers={"User-Agent":"Cardyssey price repair"},timeout=20)
    if r.status_code!=200: return None
    card=r.json()
    variants=[]
    for v in card.get("variants_detailed") or []:
        langs=[str(x).lower() for x in (v.get("languages") or [])]
        if langs and "de" not in langs: continue
        typ=(v.get("type") or "").strip()
        vid=(v.get("variantId") or "").strip()
        if typ and vid:
            variants.append((v,typ,vid))
    if len(variants)!=1:
        return None
    v,typ,vid=variants[0]
    price=cm_price(card,typ,v.get("foil"))
    if price is None:
        return None
    item={
        "id":vid,
        "type":typ,
        "subtype":v.get("subtype"),
        "foil":v.get("foil"),
        "size":v.get("size"),
        "stamps":v.get("stamp") or [],
        "legacyVariant":legacy(typ),
        "tcgDexEur":price,
    }
    return cid,card,item,price

resolved=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    for i,x in enumerate(ex.map(fetch,targets),1):
        if x: resolved.append(x)
        if i%250==0 or i==len(targets):
            print(f"checked={i} resolved={len(resolved)}",flush=True)

sql=["BEGIN;"]
for cid,card,v,price in resolved:
    variants_json=q(json.dumps([v],ensure_ascii=False,separators=(",",":")))
    raw_json=q(json.dumps(card,ensure_ascii=False,separators=(",",":")))
    sql.append(f"""UPDATE catalog_cards_mirror SET
      variants='{variants_json}'::jsonb,
      raw_payload='{raw_json}'::jsonb,
      details_complete=TRUE,
      source_updated_at=NOW(),
      last_seen_at=NOW()
      WHERE language_code='de' AND card_id='{q(cid)}';""")
    sql.append(f"DELETE FROM tcg_price_cache WHERE language_code='de' AND card_id='{q(cid)}' AND variant_id='generated';")
    sql.append(f"""INSERT INTO tcg_price_cache
      (card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
      VALUES ('{q(cid)}','de','{q(v["id"])}','{q(v["legacyVariant"])}','TCGDEX_CATALOG',{price},NOW(),'PRICE_FOUND',NULL,NOW()+INTERVAL '7 days')
      ON CONFLICT (card_id,language_code,variant_id) DO UPDATE SET
      legacy_variant=EXCLUDED.legacy_variant,source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
      updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail=NULL,next_attempt_at=EXCLUDED.next_attempt_at;""")
    sql.append(f"""INSERT INTO tcg_price_history
      (card_id,language_code,variant_id,source,base_eur,captured_at)
      VALUES ('{q(cid)}','de','{q(v["id"])}','TCGDEX_CATALOG',{price},NOW());""")
sql.append("COMMIT;")
if resolved:
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
        input="\n".join(sql),text=True,check=True,stdout=subprocess.DEVNULL
    )
print(f"applied={len(resolved)}",flush=True)
