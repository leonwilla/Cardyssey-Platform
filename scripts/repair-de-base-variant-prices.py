#!/usr/bin/env python3
"""Recover German base-variant prices from card-level TCGdex Cardmarket data.

Safe rule: only apply the card-level price when the current card has exactly
one unembellished physical variant (no stamp, no foil, no subtype). Special
printings stay unpriced instead of inheriting a potentially wrong value.
"""
import concurrent.futures, math, subprocess, requests

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

def top_price(card, typ):
    cm=((card.get("pricing") or {}).get("cardmarket") or {})
    if not cm: return None
    holo=(typ or "").strip().lower() in ("holo","reverse")
    keys=(["trend-holo","avg1-holo","avg7-holo","avg30-holo","avg-holo","low-holo"] if holo else []) + ["trend","avg1","avg7","avg30","avg","low"]
    for k in keys:
        x=cm.get(k)
        if isinstance(x,(int,float)) and math.isfinite(x) and x>0:
            return float(x)
    return None

targets=db("""SELECT DISTINCT c.card_id
              FROM tcg_price_cache p
              JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
              WHERE p.language_code='de'
                AND p.resolution_status='NO_PRICE'
                AND NOT (c.set_id ~ '^(A[0-9]|B[0-9])' OR c.set_id='P-A')
              ORDER BY c.card_id""").splitlines()
print(f"targets={len(targets)}",flush=True)

def fetch(cid):
    r=requests.get(f"{BASE}/{cid}",headers={"User-Agent":"Cardyssey price repair"},timeout=20)
    if r.status_code!=200: return None
    card=r.json()
    detailed=card.get("variants_detailed") or []
    plain=[]
    for v in detailed:
        langs=[str(x).lower() for x in (v.get("languages") or [])]
        if langs and "de" not in langs: continue
        if (v.get("stamp") or []) or (v.get("foil") or "").strip() or (v.get("subtype") or "").strip():
            continue
        typ=(v.get("type") or "").strip()
        vid=(v.get("variantId") or "").strip()
        if typ and vid:
            plain.append((typ,vid))
    if len(plain)!=1: return None
    typ,vid=plain[0]
    price=top_price(card,typ)
    if price is None: return None
    return cid,vid,legacy(typ),price

resolved=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    for i,x in enumerate(ex.map(fetch,targets),1):
        if x: resolved.append(x)
        if i%250==0 or i==len(targets):
            print(f"checked={i} resolved={len(resolved)}",flush=True)

sql=["BEGIN;"]
for cid,vid,family,price in resolved:
    sql.append(f"""UPDATE tcg_price_cache SET
      legacy_variant='{family}',
      source='TCGDEX_CATALOG',
      base_eur={price},
      updated_at=NOW(),
      resolution_status='PRICE_FOUND',
      failure_detail=NULL,
      next_attempt_at=NOW()+INTERVAL '7 days'
      WHERE language_code='de' AND card_id='{q(cid)}' AND variant_id='{q(vid)}';""")
    sql.append(f"""INSERT INTO tcg_price_history
      (card_id,language_code,variant_id,source,base_eur,captured_at)
      VALUES ('{q(cid)}','de','{q(vid)}','TCGDEX_CATALOG',{price},NOW());""")
sql.append("COMMIT;")
if resolved:
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
        input="\n".join(sql),text=True,check=True,stdout=subprocess.DEVNULL
    )
print(f"applied={len(resolved)}",flush=True)
