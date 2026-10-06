#!/usr/bin/env python3
"""Repair stale German NO_VARIANT_MATCH rows from current TCGdex data."""
import concurrent.futures, json, math, subprocess, requests, tempfile, os

BASE="https://api.tcgdex.net/v2/de/cards"

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

def exact_price(v):
    cm=((v.get("pricing") or {}).get("cardmarket") or {})
    t=(v.get("type") or "").strip().lower()
    holo=t in ("reverse","holo") or bool((v.get("foil") or "").strip())
    keys=(["trend-holo","avg7-holo","avg30-holo","avg-holo","low-holo"] if holo else []) + ["trend","avg7","avg30","avg","low"]
    for k in keys:
        x=cm.get(k)
        if isinstance(x,(int,float)) and math.isfinite(x) and x>0:
            return float(x)
    return None

targets=db("""SELECT DISTINCT card_id FROM tcg_price_cache
              WHERE language_code='de' AND resolution_status='NO_VARIANT_MATCH'
              ORDER BY card_id""").splitlines()
print(f"targets={len(targets)}",flush=True)

def fetch(cid):
    r=requests.get(f"{BASE}/{cid}",headers={"User-Agent":"Cardyssey price repair"},timeout=20)
    if r.status_code!=200:
        raise RuntimeError(f"{cid}: HTTP {r.status_code}")
    card=r.json()
    detailed=card.get("variants_detailed") or []
    if not detailed:
        raise RuntimeError(f"{cid}: no variants_detailed")
    variants=[]
    for v in detailed:
        langs=[str(x).lower() for x in (v.get("languages") or [])]
        if langs and "de" not in langs:
            continue
        typ=(v.get("type") or "").strip()
        vid=(v.get("variantId") or "").strip()
        if not typ or not vid:
            raise RuntimeError(f"{cid}: invalid variant")
        variants.append({
            "id":vid,
            "type":typ,
            "subtype":v.get("subtype"),
            "foil":v.get("foil"),
            "size":v.get("size"),
            "stamps":v.get("stamp") or [],
            "legacyVariant":legacy(typ),
            "tcgDexEur":exact_price(v),
        })
    if not variants:
        raise RuntimeError(f"{cid}: no DE variants")
    return cid,card,variants

cards=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    for i,item in enumerate(ex.map(fetch,targets),1):
        cards.append(item)
        if i%25==0 or i==len(targets):
            print(f"verified={i}",flush=True)

sql=["BEGIN;"]
for cid,card,variants in cards:
    variants_json=q(json.dumps(variants,ensure_ascii=False,separators=(",",":")))
    raw_json=q(json.dumps(card,ensure_ascii=False,separators=(",",":")))
    sql.append(f"""UPDATE catalog_cards_mirror
SET variants='{variants_json}'::jsonb,
    raw_payload='{raw_json}'::jsonb,
    details_complete=TRUE,
    source_updated_at=NOW(),
    last_seen_at=NOW()
WHERE language_code='de' AND card_id='{q(cid)}';""")
    sql.append(f"DELETE FROM tcg_price_cache WHERE language_code='de' AND card_id='{q(cid)}';")
    for v in variants:
        price=v["tcgDexEur"]
        status="PRICE_FOUND" if price is not None else "NO_PRICE"
        source="'TCGDEX'" if price is not None else "NULL"
        base="NULL" if price is None else str(price)
        retry="NOW() + INTERVAL '7 days'" if price is not None else "NOW() + INTERVAL '24 hours'"
        sql.append(f"""INSERT INTO tcg_price_cache
(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
VALUES ('{q(cid)}','de','{q(v["id"])}','{q(v["legacyVariant"])}',{source},{base},NOW(),'{status}',NULL,{retry})
ON CONFLICT (card_id,language_code,variant_id) DO UPDATE SET
legacy_variant=EXCLUDED.legacy_variant,source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
updated_at=NOW(),resolution_status=EXCLUDED.resolution_status,failure_detail=NULL,next_attempt_at=EXCLUDED.next_attempt_at;""")
        if price is not None:
            sql.append(f"""INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES ('{q(cid)}','de','{q(v["id"])}','TCGDEX',{price},NOW());""")
sql.append("COMMIT;")
payload="\n".join(sql)
subprocess.run(
    ["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
    input=payload,text=True,check=True,stdout=subprocess.DEVNULL
)
print(f"applied={len(cards)}",flush=True)
