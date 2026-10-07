#!/usr/bin/env python3
import json,re,statistics,subprocess,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-zhtw-specials"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:
        return json.load(r)

def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()

def q(v): return str(v).replace("'","''")
def num(v):
    s=str(v or "").strip().lower().split("/",1)[0].strip()
    return str(int(s)) if s.isdigit() else re.sub(r"^0+(?=\d)","",s)

expansions=[e for e in get(f"{BASE}/expansions") if int(e.get("game_id") or 0)==5]
by_code={str(e.get("code") or "").lower():e for e in expansions}

cases=[
    ("SV8a","masterball","m-sv8a","blueprint"),
    ("S11a","pokeball","s11a","reverse-flag"),
    ("S9a","pokeball","s9a","reverse-flag"),
]
updates=[]
reasons={"unmapped":0,"no_products":0,"condition":0,"language":0,"reverse":0,"price":0}

for setid,foil,code,mode in cases:
    e=by_code.get(code)
    if not e: continue
    bps=get(f"{BASE}/blueprints/export?expansion_id={e['id']}")
    idx={}
    for b in bps:
        n=num((b.get("fixed_properties") or {}).get("collector_number"))
        if not n:
            m=re.search(r"([A-Za-z]*\d+[A-Za-z]*)\s*/\s*\d+",str(b.get("version") or ""))
            n=num(m.group(1)) if m else ""
        if n: idx.setdefault(n,[]).append(b)
    payload=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":e["id"]}),40)

    raw=db(f"""SELECT c.card_id,c.local_id,c.name,p.variant_id
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='zh-tw' AND p.resolution_status='NO_PRICE'
  AND c.set_id='{setid}' AND p.legacy_variant='REVERSE'
  AND v.value->>'id'=p.variant_id
  AND LOWER(COALESCE(v.value->>'foil',''))='{foil}'
ORDER BY c.local_id""")
    resolved=0
    before=len(updates)
    for line in raw.splitlines():
        z=line.split("\t",3)
        if len(z)!=4: continue
        cid,lid,name,vid=z
        cand=idx.get(num(lid),[])
        if len(cand)!=1:
            reasons["unmapped"]+=1
            continue
        b=cand[0]; resolved+=1
        nm=[]; sp=[]
        products=payload.get(str(b["id"]),[]) if isinstance(payload,dict) else []
        if not products: reasons["no_products"]+=1
        for p in products:
            if p.get("graded"): continue
            props=p.get("properties_hash") or {}
            lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
            if lang!="zh-tw":
                reasons["language"]+=1; continue
            if mode=="reverse-flag":
                rv=next((x for k,x in props.items() if "reverse" in str(k).lower()),None)
                if str(rv).lower() not in ("true","1","yes"):
                    reasons["reverse"]+=1; continue
            price=p.get("price") or {}; cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
                reasons["price"]+=1; continue
            try: unit=float(cents)/100/max(1,int(p.get("bundle_size") or 1))
            except Exception: reasons["price"]+=1; continue
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
            detail=f"CardTrader zh-TW {setid} {foil} blueprint {b['id']}; condition={label}; listings={len(vals)}"
            updates.append((cid,vid,base,source,detail))
    print(f"zhtw_special_set={setid} resolved={resolved} updates={len(updates)-before}",flush=True)

# Traditional-Chinese SV-P promos live in CardTrader's dedicated products expansion.
promo_exp=next((e for e in expansions if str(e.get("code") or "").lower()=="cn-zh-p"),None)
if promo_exp:
    bps=get(f"{BASE}/blueprints/export?expansion_id={promo_exp['id']}")
    idx={}
    for b in bps:
        n=num((b.get("fixed_properties") or {}).get("collector_number"))
        if n: idx.setdefault(n,[]).append(b)
    payload=get(f"{BASE}/marketplace/products?expansion_id={promo_exp['id']}",40)
    raw=db("""SELECT c.card_id,c.local_id,c.name,p.variant_id
FROM tcg_price_cache p JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
WHERE p.language_code='zh-tw' AND p.resolution_status='NO_PRICE' AND c.set_id='SV-P'
ORDER BY c.local_id""")
    before=len(updates); resolved=0
    for line in raw.splitlines():
        cid,lid,name,vid=line.split("\t",3)
        cand=idx.get(num(lid),[])
        if len(cand)!=1: continue
        b=cand[0]; resolved+=1
        nm=[];sp=[]
        for p in payload.get(str(b["id"]),[]) if isinstance(payload,dict) else []:
            if p.get("graded"): continue
            props=p.get("properties_hash") or {}
            price=p.get("price") or {}; cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR": continue
            try: unit=float(cents)/100/max(1,int(p.get("bundle_size") or 1))
            except Exception: continue
            cond=str(props.get("condition") or "").strip().lower()
            if cond in ("near mint","mint","nm"): nm.append(unit)
            elif cond=="slightly played": sp.append(unit)
        vals=nm;factor=NM_FACTOR;source="CARDTRADER_MARKETPLACE";label="NM"
        if not vals and len(sp)>=3:
            vals=sp;factor=0.80;source="CARDTRADER_SP_INFERRED";label="SP_INFERRED"
        if vals:
            vals.sort();sample=vals[:min(7,len(vals))]
            listing=round(statistics.median(sample),4);base=round(listing/factor,4)
            detail=f"CardTrader Traditional Chinese promo blueprint {b['id']}; condition={label}; listings={len(vals)}"
            updates.append((cid,vid,base,source,detail))
    print(f"zhtw_special_set=SV-P resolved={resolved} updates={len(updates)-before}",flush=True)

print("zhtw_special_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"zhtw_special_updates={len(updates)}",flush=True)
if updates:
    sql=["BEGIN;"]
    for cid,vid,base,source,detail in updates:
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(cid)}' AND language_code='zh-tw' AND variant_id='{q(vid)}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(cid)}','zh-tw','{q(vid)}','{source}',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"zhtw_special_applied={len(updates)}",flush=True)
