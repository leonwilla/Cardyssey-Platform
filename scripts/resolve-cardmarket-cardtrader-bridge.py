#!/usr/bin/env python3
"""Resolve safe open prices via CardTrader identity -> official Cardmarket price guide."""
import json, math, re, subprocess, requests

PRICE_URL="https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"
UA={"User-Agent":"Cardyssey/0.4 cardmarket-cardtrader-bridge"}

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def q(v): return str(v).replace("'","''")
def positive(v): return isinstance(v,(int,float)) and math.isfinite(v) and v>0

def guide_price(g,legacy):
    keys=("trend-holo","avg7-holo","avg30-holo","avg-holo","low-holo") if legacy in ("HOLO","REVERSE") else ("trend","avg7","avg30","avg","low")
    for key in keys:
        if positive(g.get(key)):
            return float(g[key]),key
    return None,None

raw=db("""SELECT p.card_id,p.language_code,p.variant_id,p.legacy_variant,
       COALESCE(vi.cardmarket_product_id,i.cardmarket_product_id),
       v.value::text,
       CASE WHEN vi.card_id IS NOT NULL THEN 'variant' ELSE 'card' END
FROM tcg_price_cache p
JOIN catalog_cards_mirror c
  ON c.card_id=p.card_id AND c.language_code=p.language_code
LEFT JOIN cardtrader_variant_identity_cache vi
  ON vi.card_id=p.card_id
 AND vi.language_code=p.language_code
 AND vi.variant_id=p.variant_id
LEFT JOIN cardtrader_identity_cache i
  ON i.card_id=p.card_id AND i.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code IN ('ja','zh-cn','zh-tw')
  AND (p.resolution_status='NO_PRICE' OR p.source='CARDMARKET_OFFICIAL_CT_IDENTITY')
  AND COALESCE(vi.cardmarket_product_id,i.cardmarket_product_id) IS NOT NULL
  AND v.value->>'id'=p.variant_id
ORDER BY p.language_code,p.card_id,p.variant_id""")

rows=[]
for line in raw.splitlines():
    z=line.split("\t",6)
    if len(z)!=7: continue
    cid,lang,vid,legacy,pid,vjson,scope=z
    try:v=json.loads(vjson)
    except Exception: continue
    # A card-level identity is safe only for the plain physical printing.
    # Variant-level identities may intentionally describe stamps/subtypes/foils.
    if scope=="card" and (v.get("foil") or v.get("stamps") or v.get("subtype")):
        continue
    if str(v.get("size") or "standard").lower()!="standard": continue
    rows.append((cid,lang,vid,legacy,pid))

response=requests.get(PRICE_URL,headers=UA,timeout=45)
response.raise_for_status()
payload=response.json()
prices={str(x.get("idProduct")):x for x in payload.get("priceGuides") or []}

updates=[]
for cid,lang,vid,legacy,pid in rows:
    guide=prices.get(str(pid))
    if not guide: continue
    value,key=guide_price(guide,legacy)
    if value is None: continue
    updates.append((cid,lang,vid,pid,value,key))

print(
    f"cardmarket_ct_bridge_created={payload.get('createdAt')} "
    f"eligible={len(rows)} updates={len(updates)}",
    flush=True
)
for x in updates[:30]:
    print("bridge",*x,sep="\t",flush=True)

if updates:
    sql=["BEGIN;"]
    for cid,lang,vid,pid,value,key in updates:
        detail=f"CardTrader exact identity -> Cardmarket product {pid}; key {key}"
        sql.append(
            f"UPDATE tcg_price_cache SET source='CARDMARKET_OFFICIAL_CT_IDENTITY',"
            f"base_eur={value:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',"
            f"failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' "
            f"WHERE card_id='{q(cid)}' AND language_code='{q(lang)}' "
            f"AND variant_id='{q(vid)}';"
        )
        sql.append(
            f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) "
            f"VALUES('{q(cid)}','{q(lang)}','{q(vid)}','CARDMARKET_OFFICIAL_CT_IDENTITY',{value:.4f},NOW());"
        )
    sql.append("COMMIT;")
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
        input="\n".join(sql),text=True,check=True
    )
    print(f"cardmarket_ct_bridge_applied={len(updates)}",flush=True)

# Repair only obvious single-listing CardTrader outliers when the exact
# Cardmarket identity has a much lower official guide value.
outlier_raw=db("""SELECT p.card_id,p.language_code,p.variant_id,p.legacy_variant,
       p.base_eur,p.failure_detail,i.cardmarket_product_id
FROM tcg_price_cache p
JOIN cardtrader_identity_cache i
  ON i.card_id=p.card_id AND i.language_code=p.language_code
WHERE p.language_code IN ('ja','zh-cn','zh-tw')
  AND p.source='CARDTRADER_MARKETPLACE'
  AND p.base_eur > 500
  AND i.cardmarket_product_id IS NOT NULL""")

repairs=[]
for line in outlier_raw.splitlines():
    z=line.split("\t",6)
    if len(z)!=7: continue
    cid,lang,vid,legacy,current,detail,pid=z
    match=re.search(r"listings[= ](\d+)",detail or "")
    listing_count=int(match.group(1)) if match else 0
    if listing_count!=1: continue
    guide=prices.get(str(pid))
    if not guide: continue
    value,key=guide_price(guide,legacy)
    if value is None: continue
    current=float(current)
    if current > 500 and current >= value*20:
        repairs.append((cid,lang,vid,pid,current,value,key))

print(f"cardmarket_ct_outlier_repairs={len(repairs)}",flush=True)
if repairs:
    sql=["BEGIN;"]
    for cid,lang,vid,pid,current,value,key in repairs:
        detail=(
            f"CardTrader single-listing outlier {current:.4f} EUR replaced by "
            f"Cardmarket product {pid}; key {key}"
        )
        sql.append(
            f"UPDATE tcg_price_cache SET source='CARDMARKET_OFFICIAL_CT_IDENTITY',"
            f"base_eur={value:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',"
            f"failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' "
            f"WHERE card_id='{q(cid)}' AND language_code='{q(lang)}' "
            f"AND variant_id='{q(vid)}';"
        )
        sql.append(
            f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) "
            f"VALUES('{q(cid)}','{q(lang)}','{q(vid)}','CARDMARKET_OFFICIAL_CT_IDENTITY',{value:.4f},NOW());"
        )
    sql.append("COMMIT;")
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
        input="\n".join(sql),text=True,check=True
    )
    print(f"cardmarket_ct_outlier_applied={len(repairs)}",flush=True)
