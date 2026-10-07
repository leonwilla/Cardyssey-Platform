#!/usr/bin/env python3
import concurrent.futures,json,re,statistics,subprocess,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
TCGDEX="https://api.tcgdex.net/v2/ja/cards"
NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-ja-dex"}

def get(url,timeout=30,auth=True):
    headers=H if auth else {"Accept":"application/json","User-Agent":"Cardyssey-ja-dex"}
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as r:
        return json.load(r)

def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()

def q(v): return str(v).replace("'","''")

SET_CODE={
    "PMCG1":"1ep",
    "PMCG2":"jun",
    "PMCG3":"myf",
    "PMCG4":"rog",
    "PMCG5":"gls",
    "PMCG6":"gcd",
    "neo1":"gstnw",
    "neo2":"ctr",
    "neo3":"awl",
    "neo4":"del",
}
exps=[e for e in get(f"{BASE}/expansions") if int(e.get("game_id") or 0)==5]
by_code={str(e.get("code") or "").lower():e for e in exps}

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,v.value::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND c.set_id IN ('PMCG1','PMCG2','PMCG3','PMCG4','PMCG5','PMCG6','neo1','neo2','neo3','neo4')
  AND v.value->>'id'=p.variant_id
ORDER BY c.set_id,c.local_id,p.variant_id""")

rows=[]
for line in raw.splitlines():
    z=line.split("\t",6)
    if len(z)!=7: continue
    cid,setid,lid,name,vid,legacy,vjson=z
    try:v=json.loads(vjson)
    except Exception:continue
    if v.get("foil") or v.get("stamps") or str(v.get("size") or "standard").lower()!="standard": continue
    subtype=str(v.get("subtype") or "").lower()
    code=SET_CODE[setid]
    if setid=="PMCG1" and subtype=="no-rarity":
        code="1epnr"
    elif setid=="PMCG1" and subtype:
        continue
    e=by_code.get(code)
    if not e: continue
    rows.append({
        "card_id":cid,"set_id":setid,"local_id":lid,"name":name,
        "variant_id":vid,"legacy":legacy,"subtype":subtype,
        "expansion_id":int(e["id"]),"expansion_code":code,
    })

print(f"ja_dex_candidates={len(rows)}",flush=True)

cards=sorted({r["card_id"] for r in rows})
def load_dex(cid):
    try:
        data=get(f"{TCGDEX}/{urllib.parse.quote(cid)}",15,False)
        ids=data.get("dexId") or []
        return cid,ids[0] if len(ids)==1 else None
    except Exception:
        return cid,None

dex={}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    for i,(cid,did) in enumerate(pool.map(load_dex,cards),1):
        dex[cid]=did
        if i%100==0 or i==len(cards):
            print(f"ja_dex_identity={i}/{len(cards)}",flush=True)

blueprints={}
markets={}
for eid in sorted({r["expansion_id"] for r in rows}):
    blueprints[eid]=get(f"{BASE}/blueprints/export?expansion_id={eid}",30)
    markets[eid]=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)

indexes={}
for eid,bps in blueprints.items():
    idx={}
    for b in bps:
        version=str(b.get("version") or "")
        m=re.search(r"\bNo\.\s*0*(\d+)\b",version,re.I)
        if not m: continue
        did=int(m.group(1))
        rarity=str((b.get("fixed_properties") or {}).get("pokemon_rarity") or "").lower()
        version_lower=version.lower()
        holo=("holo" in rarity) or ("shiny" in rarity) or ("holo" in version_lower)
        idx.setdefault((did,holo),[]).append(b)
    indexes[eid]=idx

resolved=[]
ambiguous=0
for r in rows:
    did=dex.get(r["card_id"])
    if did is None: continue
    cand=indexes.get(r["expansion_id"],{}).get((int(did),r["legacy"]=="HOLO"),[])
    if len(cand)!=1:
        if len(cand)>1: ambiguous+=1
        continue
    blueprint=cand[0]
    cmids=[]
    for value in blueprint.get("card_market_ids") or []:
        try: cmids.append(int(value))
        except (TypeError,ValueError): pass
    resolved.append({
        **r,
        "dex_id":int(did),
        "blueprint_id":int(blueprint["id"]),
        "cardmarket_id":cmids[0] if len(cmids)==1 else None,
    })

print(f"ja_dex_resolved={len(resolved)} ambiguous={ambiguous}",flush=True)
for sid in SET_CODE:
    print(f"ja_dex_set={sid} resolved={sum(1 for r in resolved if r['set_id']==sid)}",flush=True)

identity_rows=[r for r in resolved if r["cardmarket_id"] is not None]
if identity_rows:
    values=[]
    for r in identity_rows:
        values.append(
            f"('{q(r['card_id'])}','ja','{q(r['variant_id'])}',"
            f"{r['cardmarket_id']},{r['blueprint_id']},{r['expansion_id']},'ja-dex')"
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
print(f"ja_dex_variant_identities={len(identity_rows)}",flush=True)

updates=[]
reasons={"no_products":0,"language":0,"condition":0,"reverse":0,"price":0}
for r in resolved:
    products=markets[r["expansion_id"]].get(str(r["blueprint_id"]),[]) if isinstance(markets[r["expansion_id"]],dict) else []
    if not products: reasons["no_products"]+=1
    nm=[];sp=[]
    for p in products:
        if p.get("graded"): continue
        props=p.get("properties_hash") or {}
        lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
        if lang and lang!="jp": reasons["language"]+=1; continue
        rv=next((x for k,x in props.items() if "reverse" in str(k).lower()),None)
        if str(rv).lower() in ("true","1","yes"): reasons["reverse"]+=1; continue
        price=p.get("price") or {}; cents=price.get("cents")
        if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
            reasons["price"]+=1; continue
        try:unit=float(cents)/100/max(1,int(p.get("bundle_size") or 1))
        except Exception:reasons["price"]+=1;continue
        cond=str(props.get("condition") or "").strip().lower()
        if cond in ("near mint","mint","nm"):nm.append(unit)
        elif cond=="slightly played":sp.append(unit)
        else:reasons["condition"]+=1
    vals=nm;factor=NM_FACTOR;source="CARDTRADER_MARKETPLACE";label="NM"
    if not vals and len(sp)>=3:
        vals=sp;factor=0.80;source="CARDTRADER_SP_INFERRED";label="SP_INFERRED"
    if vals:
        vals.sort();sample=vals[:min(7,len(vals))]
        listing=round(statistics.median(sample),4)
        base=round(listing/factor,4)
        detail=f"CardTrader Japanese dex match {r['set_id']} dex={r['dex_id']} blueprint {r['blueprint_id']}; condition={label}; listings={len(vals)}"
        updates.append((r,base,source,detail))

print("ja_dex_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"ja_dex_updates={len(updates)}",flush=True)
if updates:
    sql=["BEGIN;"]
    for r,base,source,detail in updates:
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','ja','{q(r['variant_id'])}','{source}',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"ja_dex_applied={len(updates)}",flush=True)
