#!/usr/bin/env python3
import json,re,statistics,subprocess,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"; NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="): TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-ja-reverse"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:return json.load(r)
def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v):return str(v).replace("'","''")
def normnum(v):
    s=str(v or "").strip().lower().split("/",1)[0].strip()
    if s.isdigit():return str(int(s))
    return re.sub(r"^0+(?=\d)","",s)

exps=[x for x in get(f"{BASE}/expansions") if int(x.get("game_id") or 0)==5]
by_code={str(x.get("code") or "").lower():x for x in exps}

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,v.value->>'foil'
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND v.value->>'id'=p.variant_id
  AND LOWER(COALESCE(v.value->>'foil','')) IN ('masterball','pokeball')
ORDER BY c.set_id,c.local_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t",5)
    if len(z)!=6:continue
    cid,setid,local_id,name,vid,foil=z
    prefix="m-" if foil.lower()=="masterball" else "p-"
    code=(prefix+setid).lower()
    exp=by_code.get(code)
    require_reverse_flag=False
    if (
        exp is None
        and foil.lower()=="pokeball"
        and setid in {"S11a","S9a"}
    ):
        exp=by_code.get(setid.lower())
        require_reverse_flag=True
    if not exp:continue
    rows.append({
        "card_id":cid,
        "set_id":setid,
        "local_id":local_id,
        "name":name,
        "variant_id":vid,
        "foil":foil.lower(),
        "expansion_id":int(exp["id"]),
        "expansion_code":exp["code"],
        "require_reverse_flag":require_reverse_flag,
    })
print(f"ja_reverse_candidates={len(rows)}",flush=True)

resolved=[]
payload_by_exp={}
for eid in sorted({r["expansion_id"] for r in rows}):
    bps=get(f"{BASE}/blueprints/export?expansion_id={eid}")
    idx={}
    for b in bps:
        n=normnum((b.get("fixed_properties") or {}).get("collector_number"))
        if n:idx.setdefault(n,[]).append(b)
    for r in [x for x in rows if x["expansion_id"]==eid]:
        cand=idx.get(normnum(r["local_id"]),[])
        if len(cand)!=1:continue
        resolved.append({**r,"blueprint_id":int(cand[0]["id"])})
print(f"ja_reverse_resolved={len(resolved)}",flush=True)

updates=[]; reasons={"no_products":0,"condition":0,"language":0,"price":0}
for eid in sorted({r["expansion_id"] for r in resolved}):
    payload=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)
    group=[r for r in resolved if r["expansion_id"]==eid]
    for r in group:
        products=payload.get(str(r["blueprint_id"]),[]) if isinstance(payload,dict) else []
        if not products:reasons["no_products"]+=1
        values=[]
        for p in products:
            if p.get("graded"):continue
            props=p.get("properties_hash") or {}
            cond=str(props.get("condition") or "").strip().lower()
            if cond not in ("near mint","mint","nm"):reasons["condition"]+=1;continue
            lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
            if lang and lang!="jp":reasons["language"]+=1;continue
            price=p.get("price") or {}; cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
                reasons["price"]+=1;continue
            try:unit=float(cents)/100/max(1,int(p.get("bundle_size") or 1))
            except Exception:continue
            values.append(unit)
        if values:
            values.sort();sample=values[:min(7,len(values))]
            listing=round(statistics.median(sample),4);base=round(listing/NM_FACTOR,4)
            updates.append((r,base,listing,len(values)))
    print(f"ja_reverse_expansion={eid} updates={len(updates)}",flush=True)

print("ja_reverse_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"ja_reverse_updates={len(updates)}",flush=True)
if updates:
    sql=["BEGIN;"]
    for r,base,listing,count in updates:
        detail=f"CardTrader {r['foil']} reverse blueprint {r['blueprint_id']}; median cheapest NM EUR {listing:.4f}; listings {count}"
        sql.append(f"UPDATE tcg_price_cache SET source='CARDTRADER_MARKETPLACE',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','ja','{q(r['variant_id'])}','CARDTRADER_MARKETPLACE',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"ja_reverse_applied={len(updates)}",flush=True)
