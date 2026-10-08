#!/usr/bin/env python3
import json,re,statistics,subprocess,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip()
        break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-ja-promos"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:
        return json.load(r)

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True,
    ).stdout.strip()

def q(v): return str(v).replace("'","''")
def num(v):
    s=str(v or "").strip().lower().split("/",1)[0].strip()
    return str(int(s)) if s.isdigit() else re.sub(r"^0+(?=\d)","",s)

SET_CODE={"M-P":"mp-promo","SV-P":"promosv"}

expansions=[e for e in get(f"{BASE}/expansions") if int(e.get("game_id") or 0)==5]
by_code={str(e.get("code") or "").lower():e for e in expansions}

rows=[]
raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,v.value::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND c.set_id IN ('M-P','SV-P')
  AND v.value->>'id'=p.variant_id
ORDER BY c.set_id,c.local_id,p.variant_id""")

for line in raw.splitlines():
    z=line.split("\t",6)
    if len(z)!=7: continue
    cid,setid,lid,name,vid,legacy,vjson=z
    try:v=json.loads(vjson)
    except Exception: continue
    if legacy not in ("NORMAL","HOLO"): continue
    if v.get("foil") or v.get("stamps") or v.get("subtype"): continue
    if str(v.get("size") or "standard").lower()!="standard": continue
    e=by_code.get(SET_CODE[setid])
    if not e: continue
    rows.append({
        "card_id":cid,"set_id":setid,"local_id":lid,"name":name,
        "variant_id":vid,"legacy":legacy,"expansion_id":int(e["id"]),
    })

print(f"ja_promo_candidates={len(rows)}",flush=True)

indexes={}
markets={}
for eid in sorted({r["expansion_id"] for r in rows}):
    bps=get(f"{BASE}/blueprints/export?expansion_id={eid}",30)
    idx={}
    for b in bps:
        n=num((b.get("fixed_properties") or {}).get("collector_number"))
        if n:
            idx.setdefault(n,[]).append(b)
    indexes[eid]=idx
    markets[eid]=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)

resolved=[]
ambiguous=0
for r in rows:
    cand=indexes.get(r["expansion_id"],{}).get(num(r["local_id"]),[])
    if len(cand)>1:
        # Prefer the unique blueprint whose version explicitly names the same promo number.
        exact=[b for b in cand if re.search(rf"\b0*{re.escape(num(r['local_id']))}\s*/",str(b.get("version") or ""),re.I)]
        if len(exact)==1: cand=exact
    if len(cand)!=1:
        if len(cand)>1: ambiguous+=1
        continue
    b=cand[0]
    cmids=[]
    for value in b.get("card_market_ids") or []:
        try: cmids.append(int(value))
        except (TypeError,ValueError): pass
    resolved.append({
        **r,
        "blueprint_id":int(b["id"]),
        "cardmarket_id":cmids[0] if len(cmids)==1 else None,
    })

print(f"ja_promo_resolved={len(resolved)} ambiguous={ambiguous}",flush=True)

identity_rows=[r for r in resolved if r["cardmarket_id"] is not None]
if identity_rows:
    vals=[
        f"('{q(r['card_id'])}','ja','{q(r['variant_id'])}',{r['cardmarket_id']},"
        f"{r['blueprint_id']},{r['expansion_id']},'ja-promo')"
        for r in identity_rows
    ]
    db(
        "INSERT INTO cardtrader_variant_identity_cache"
        "(card_id,language_code,variant_id,cardmarket_product_id,blueprint_id,expansion_id,method) VALUES "
        + ",".join(vals)
        + " ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET "
          "cardmarket_product_id=EXCLUDED.cardmarket_product_id,"
          "blueprint_id=EXCLUDED.blueprint_id,"
          "expansion_id=EXCLUDED.expansion_id,"
          "method=EXCLUDED.method,updated_at=NOW()"
    )
print(f"ja_promo_identities={len(identity_rows)}",flush=True)

updates=[]
reasons={"no_products":0,"graded":0,"language":0,"reverse":0,"condition":0,"price":0}
for r in resolved:
    products=markets[r["expansion_id"]].get(str(r["blueprint_id"]),[]) if isinstance(markets[r["expansion_id"]],dict) else []
    if not products: reasons["no_products"]+=1
    nm=[]; sp=[]
    for p in products:
        if p.get("graded"):
            reasons["graded"]+=1; continue
        props=p.get("properties_hash") or {}
        lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
        if lang and lang!="jp":
            reasons["language"]+=1; continue
        rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
        if str(rv).lower() in ("true","1","yes"):
            reasons["reverse"]+=1; continue
        price=p.get("price") or {}; cents=price.get("cents")
        if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
            reasons["price"]+=1; continue
        try:unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
        except Exception:
            reasons["price"]+=1; continue
        cond=str(props.get("condition") or "").strip().lower()
        if cond in ("near mint","mint","nm"): nm.append(unit)
        elif cond=="slightly played": sp.append(unit)
        else: reasons["condition"]+=1

    vals=nm; factor=NM_FACTOR; source="CARDTRADER_MARKETPLACE"; label="NM"
    if not vals and len(sp)>=3:
        vals=sp; factor=0.80; source="CARDTRADER_SP_INFERRED"; label="SP_INFERRED"
    if vals:
        vals.sort(); sample=vals[:min(7,len(vals))]
        listing=round(statistics.median(sample),4)
        base=round(listing/factor,4)
        detail=f"CardTrader Japanese promo {r['set_id']} blueprint {r['blueprint_id']}; condition={label}; listings={len(vals)}"
        updates.append((r,base,source,detail))

print("ja_promo_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"ja_promo_updates={len(updates)}",flush=True)

if updates:
    sql=["BEGIN;"]
    for r,base,source,detail in updates:
        sql.append(
            f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),"
            f"resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' "
            f"WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['variant_id'])}' "
            f"AND resolution_status='NO_PRICE';"
        )
        sql.append(
            f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) "
            f"VALUES('{q(r['card_id'])}','ja','{q(r['variant_id'])}','{source}',{base:.4f},NOW());"
        )
    sql.append("COMMIT;")
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
        input="\n".join(sql),text=True,check=True,
    )
    print(f"ja_promo_applied={len(updates)}",flush=True)
