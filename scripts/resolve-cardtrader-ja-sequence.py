#!/usr/bin/env python3
import json,statistics,subprocess,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-ja-sequence"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:
        return json.load(r)
def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v): return str(v).replace("'","''")

SET_CODE={
    "PMCG2":"jun",
    "PMCG4":"rog",
    "PMCG5":"gls",
    "PMCG6":"gcd",
    "neo1":"gstnw",
    "neo2":"ctr",
    "neo3":"awl",
}
expansions=[e for e in get(f"{BASE}/expansions") if int(e.get("game_id") or 0)==5]
by_code={str(e.get("code") or "").lower():e for e in expansions}

updates=[]
reason_totals={"no_products":0,"graded":0,"condition":0,"language":0,"reverse":0,"price":0}
for setid,code in SET_CODE.items():
    e=by_code[code]
    eid=int(e["id"])
    bps=get(f"{BASE}/blueprints/export?expansion_id={eid}",30)
    raw=db(f"""SELECT c.card_id,c.local_id,c.name,p.variant_id,p.legacy_variant
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND c.set_id='{setid}'
ORDER BY c.local_id::int""")
    rows=[]
    for line in raw.splitlines():
        z=line.split("\t",4)
        if len(z)!=5: continue
        cid,local_id,name,vid,legacy=z
        if not local_id.isdigit() or legacy not in ("NORMAL","HOLO"): continue
        pos=int(local_id)
        if pos<1 or pos>len(bps): continue
        bp=bps[pos-1]
        rarity=str((bp.get("fixed_properties") or {}).get("pokemon_rarity") or "").lower()
        if ("holo" in rarity)!=(legacy=="HOLO"): continue
        cmids=[]
        for value in bp.get("card_market_ids") or []:
            try: cmids.append(int(value))
            except (TypeError,ValueError): pass
        rows.append({
            "card_id":cid,"local_id":local_id,"name":name,
            "variant_id":vid,"legacy":legacy,
            "blueprint_id":int(bp["id"]),
            "blueprint_name":str(bp.get("name") or ""),
            "cardmarket_id":cmids[0] if len(cmids)==1 else None,
        })
    print(f"sequence_set={setid} resolved={len(rows)} expansion={eid}",flush=True)

    identity_rows=[r for r in rows if r["cardmarket_id"] is not None]
    if identity_rows:
        values=[]
        for r in identity_rows:
            values.append(
                f"('{q(r['card_id'])}','ja','{q(r['variant_id'])}',"
                f"{r['cardmarket_id']},{r['blueprint_id']},{eid},'ja-sequence')"
            )
        db(
            "INSERT INTO cardtrader_variant_identity_cache"
            "(card_id,language_code,variant_id,cardmarket_product_id,blueprint_id,expansion_id,method) VALUES "
            + ",".join(values)
            + " ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET "
              "cardmarket_product_id=EXCLUDED.cardmarket_product_id,"
              "blueprint_id=EXCLUDED.blueprint_id,"
              "expansion_id=EXCLUDED.expansion_id,"
              "method=EXCLUDED.method,updated_at=NOW()"
        )
    print(f"sequence_set={setid} variant_identities={len(identity_rows)}",flush=True)

    payload=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)
    before=len(updates)
    for r in rows:
        products=payload.get(str(r["blueprint_id"]),[]) if isinstance(payload,dict) else []
        if not products: reason_totals["no_products"]+=1
        nm_values=[]
        sp_values=[]
        for p in products:
            if p.get("graded"): reason_totals["graded"]+=1; continue
            props=p.get("properties_hash") or {}
            lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
            if lang and lang!="jp": reason_totals["language"]+=1; continue
            rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
            if str(rv).lower() in ("true","1","yes"): reason_totals["reverse"]+=1; continue
            price=p.get("price") or {}; cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
                reason_totals["price"]+=1; continue
            try: unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
            except Exception: reason_totals["price"]+=1; continue
            cond=str(props.get("condition") or "").strip().lower()
            if cond in ("near mint","mint","nm"):
                nm_values.append(unit)
            elif cond=="slightly played":
                sp_values.append(unit)
            else:
                reason_totals["condition"]+=1
        values=nm_values
        factor=NM_FACTOR
        source="CARDTRADER_MARKETPLACE"
        condition_label="NM"
        if not values and len(sp_values)>=3:
            values=sp_values
            factor=0.80
            source="CARDTRADER_SP_INFERRED"
            condition_label="SP_INFERRED"
        if values:
            values.sort(); sample=values[:min(7,len(values))]
            listing=round(statistics.median(sample),4)
            base=round(listing/factor,4)
            updates.append((setid,r,base,listing,len(values),source,condition_label))
    print(f"sequence_set={setid} updates={len(updates)-before}",flush=True)

print("sequence_reasons="+json.dumps(reason_totals,separators=(",",":")),flush=True)
print(f"sequence_updates={len(updates)}",flush=True)

if updates:
    sql=["BEGIN;"]
    for setid,r,base,listing,count,source,condition_label in updates:
        detail=f"CardTrader Japanese sequence {setid} blueprint {r['blueprint_id']}; condition={condition_label}; median listing EUR {listing:.4f}; listings {count}"
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','ja','{q(r['variant_id'])}','{source}',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"sequence_applied={len(updates)}",flush=True)
