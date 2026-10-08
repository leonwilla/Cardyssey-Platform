#!/usr/bin/env python3
import json,statistics,subprocess,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
EXPANSION_ID=1970
NM_FACTOR=0.92
ROOT=Path(__file__).resolve().parent
MAP=ROOT/"pmcg1-art-identities.json"
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-pmcg1-art"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:
        return json.load(r)
def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v): return str(v).replace("'","''")

if not TOKEN or not MAP.exists():
    raise SystemExit(0)
rows=json.loads(MAP.read_text())
open_raw=db("""SELECT card_id,variant_id FROM tcg_price_cache
WHERE language_code='ja' AND resolution_status='NO_PRICE'""")
open_keys={tuple(x.split("\t",1)) for x in open_raw.splitlines() if "\t" in x}
rows=[r for r in rows if (r["card_id"],r["variant_id"]) in open_keys]
print(f"pmcg1_art_open={len(rows)}",flush=True)
if not rows: raise SystemExit(0)

bps=get(f"{BASE}/blueprints/export?expansion_id={EXPANSION_ID}",30)
by_id={int(b["id"]):b for b in bps}
payload=get(f"{BASE}/marketplace/products?expansion_id={EXPANSION_ID}",40)

updates=[]
identity=[]
reasons={"no_products":0,"language":0,"edition":0,"reverse":0,"condition":0}
for r in rows:
    b=by_id.get(int(r["blueprint_id"]))
    if not b: continue
    cmids=[]
    for x in b.get("card_market_ids") or []:
        try: cmids.append(int(x))
        except (TypeError,ValueError): pass
    if len(cmids)==1:
        identity.append((r,cmids[0]))
    products=payload.get(str(r["blueprint_id"]),[]) if isinstance(payload,dict) else []
    if not products: reasons["no_products"]+=1
    nm=[];sp=[]
    for p in products:
        if p.get("graded"): continue
        props=p.get("properties_hash") or {}
        lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
        if lang and lang!="jp":
            reasons["language"]+=1; continue
        if str(props.get("first_edition")).lower() in ("true","1","yes"):
            reasons["edition"]+=1; continue
        rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
        if str(rv).lower() in ("true","1","yes"):
            reasons["reverse"]+=1; continue
        price=p.get("price") or {}; cents=price.get("cents")
        if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
            continue
        try: unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
        except Exception: continue
        cond=str(props.get("condition") or "").strip().lower()
        if cond in ("near mint","mint","nm"): nm.append(unit)
        elif cond=="slightly played": sp.append(unit)
        else: reasons["condition"]+=1
    vals=nm; factor=NM_FACTOR; source="CARDTRADER_MARKETPLACE"; label="NM"
    if not vals and len(sp)>=3:
        vals=sp; factor=0.80; source="CARDTRADER_SP_INFERRED"; label="SP_INFERRED"
    if vals:
        vals.sort(); listing=statistics.median(vals[:min(7,len(vals))])
        base=round(listing/factor,4)
        detail=f"CardTrader PMCG1 exact artwork blueprint {r['blueprint_id']}; condition={label}; listings={len(vals)}; art_distance={r['distance']}; art_margin={r['margin']}"
        updates.append((r,base,source,detail))

print("pmcg1_art_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"pmcg1_art_updates={len(updates)} identities={len(identity)}",flush=True)

if identity:
    vals=[f"('{q(r['card_id'])}','ja','{q(r['variant_id'])}',{cmid},{r['blueprint_id']},{EXPANSION_ID},'pmcg1-art-exact')" for r,cmid in identity]
    db("INSERT INTO cardtrader_variant_identity_cache(card_id,language_code,variant_id,cardmarket_product_id,blueprint_id,expansion_id,method) VALUES "+",".join(vals)+" ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET cardmarket_product_id=EXCLUDED.cardmarket_product_id,blueprint_id=EXCLUDED.blueprint_id,expansion_id=EXCLUDED.expansion_id,method=EXCLUDED.method,updated_at=NOW()")

if updates:
    sql=["BEGIN;"]
    for r,base,source,detail in updates:
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','ja','{q(r['variant_id'])}','{source}',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"pmcg1_art_applied={len(updates)}",flush=True)
