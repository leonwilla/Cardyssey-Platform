#!/usr/bin/env python3
import json,re,statistics,subprocess,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-ja-classic"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:
        return json.load(r)
def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v): return str(v).replace("'","''")
def num(v):
    s=str(v or "").strip().lower().split("/",1)[0].strip()
    if s.isdigit(): return str(int(s))
    return re.sub(r"^0+(?=\d)","",s)

SET_CODE={
    "E1":"ec1","E2":"ec2","E3":"ec3","E4":"ec4","E5":"ec5",
    "PCG1":"fol","PCG2":"cbs","PCG3":"rgsb","PCG4":"gsso",
    "PCG5":"mif","PCG6":"hrt","PCG7":"hof","PCG8":"mic","PCG9":"odffe",
}
expansions=[e for e in get(f"{BASE}/expansions") if int(e.get("game_id") or 0)==5]
by_code={str(e.get("code") or "").lower():e for e in expansions}

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,v.value::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND v.value->>'id'=p.variant_id
ORDER BY c.set_id,c.local_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t",6)
    if len(z)!=7: continue
    cid,setid,local_id,name,vid,legacy,vjson=z
    try:v=json.loads(vjson)
    except Exception:continue
    if legacy not in ("NORMAL","HOLO"): continue
    if v.get("foil") or str(v.get("size") or "").lower() not in ("","standard"): continue
    stamps=[str(x).lower() for x in (v.get("stamps") or [])]
    subtype=str(v.get("subtype") or "").lower()

    expected_first=None
    code=SET_CODE.get(setid)
    if any("1st" in x for x in stamps):
        expected_first=True
    elif subtype=="unlimited":
        expected_first=False
    elif setid=="PMCG1" and subtype=="no-rarity":
        code="1epnr"
        expected_first=False
    else:
        continue

    e=by_code.get(str(code or "").lower())
    if not e: continue
    rows.append({
        "card_id":cid,"set_id":setid,"local_id":local_id,"name":name,
        "variant_id":vid,"legacy":legacy,"expected_first":expected_first,
        "expansion_id":int(e["id"]),"expansion_code":code,
    })

print(f"classic_candidates={len(rows)}",flush=True)

blueprints={}
for eid in sorted({r["expansion_id"] for r in rows}):
    try: blueprints[eid]=get(f"{BASE}/blueprints/export?expansion_id={eid}",30)
    except Exception as e:
        print(f"classic_blueprint_error expansion={eid} error={e!r}",flush=True)
        blueprints[eid]=[]

indexes={}
for eid,bps in blueprints.items():
    idx={}
    for b in bps:
        n=num((b.get("fixed_properties") or {}).get("collector_number"))
        if n: idx.setdefault(n,[]).append(b)
    indexes[eid]=idx

resolved=[]
ambiguous=0
for r in rows:
    cand=indexes.get(r["expansion_id"],{}).get(num(r["local_id"]),[])
    if len(cand)!=1:
        if len(cand)>1: ambiguous+=1
        continue
    resolved.append({**r,"blueprint_id":int(cand[0]["id"])})
print(f"classic_resolved={len(resolved)} ambiguous={ambiguous}",flush=True)

updates=[]
reasons={"no_products":0,"graded":0,"condition":0,"language":0,"edition":0,"reverse":0,"price":0}
for gi,eid in enumerate(sorted({r["expansion_id"] for r in resolved}),1):
    try: payload=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)
    except Exception as e:
        print(f"classic_market_error expansion={eid} error={e!r}",flush=True); continue
    for r in [x for x in resolved if x["expansion_id"]==eid]:
        products=payload.get(str(r["blueprint_id"]),[]) if isinstance(payload,dict) else []
        if not products: reasons["no_products"]+=1
        values=[]
        for p in products:
            if p.get("graded"): reasons["graded"]+=1; continue
            props=p.get("properties_hash") or {}
            cond=str(props.get("condition") or "").strip().lower()
            if cond not in ("near mint","mint","nm"): reasons["condition"]+=1; continue
            lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
            if lang and lang!="jp": reasons["language"]+=1; continue
            if r["expansion_code"]!="1epnr":
                edition=props.get("first_edition")
                is_first=str(edition).lower() in ("true","1","yes")
                if is_first != r["expected_first"]: reasons["edition"]+=1; continue
            rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
            if str(rv).lower() in ("true","1","yes"): reasons["reverse"]+=1; continue
            price=p.get("price") or {}; cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
                reasons["price"]+=1; continue
            try: unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
            except Exception: reasons["price"]+=1; continue
            values.append(unit)
        if values:
            values.sort(); sample=values[:min(7,len(values))]
            listing=round(statistics.median(sample),4)
            base=round(listing/NM_FACTOR,4)
            updates.append((r,base,listing,len(values)))
    print(f"classic_market={gi}/{len(set(x['expansion_id'] for x in resolved))} updates={len(updates)}",flush=True)

print("classic_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"classic_updates={len(updates)}",flush=True)

if updates:
    sql=["BEGIN;"]
    for r,base,listing,count in updates:
        detail=f"CardTrader classic {r['expansion_code']} blueprint {r['blueprint_id']}; first_edition={r['expected_first']}; median cheapest NM EUR {listing:.4f}; listings {count}"
        sql.append(f"UPDATE tcg_price_cache SET source='CARDTRADER_MARKETPLACE',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','ja','{q(r['variant_id'])}','CARDTRADER_MARKETPLACE',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"classic_applied={len(updates)}",flush=True)
