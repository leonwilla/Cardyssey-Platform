#!/usr/bin/env python3
import json,re,statistics,subprocess,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-western-safe"}

def get(url,timeout=30,auth=True):
    headers=H if auth else {"Accept":"application/json","User-Agent":"Cardyssey-western-safe"}
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as r:
        return json.load(r)

def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()

def q(v): return str(v).replace("'","''")
def norm(v): return re.sub(r"[^a-z0-9]+","",str(v or "").lower())
def num(v):
    s=str(v or "").strip().lower().split("/",1)[0].strip()
    return str(int(s)) if s.isdigit() else s

SET_CODE={
    "bwp":"bwbsp",
    "tk-xy-b":"bisharp",
    "tk-xy-w":"wigglytuff",
    "mep":"mep",
}
TCGCSV_GROUP={
    "bwp":1407,
    "tk-xy-b":1533,
    "tk-xy-w":1533,
    "mep":24451,
}

expansions=[e for e in get(f"{BASE}/expansions") if int(e.get("game_id") or 0)==5]
by_code={str(e.get("code") or "").lower():e for e in expansions}

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,v.value::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='en' AND p.resolution_status='NO_PRICE'
  AND c.set_id IN ('bwp','tk-xy-b','tk-xy-w','mep')
  AND v.value->>'id'=p.variant_id
ORDER BY c.set_id,c.local_id""")

rows=[]
for line in raw.splitlines():
    z=line.split("\t",6)
    if len(z)!=7: continue
    cid,setid,lid,name,vid,legacy,vjson=z
    try: v=json.loads(vjson)
    except Exception: continue
    if v.get("stamps") or v.get("subtype") or v.get("foil"): continue
    if str(v.get("size") or "standard").lower()!="standard": continue
    e=by_code.get(SET_CODE.get(setid,""))
    if not e: continue
    rows.append({
        "card_id":cid,"set_id":setid,"local_id":lid,"name":name,
        "variant_id":vid,"legacy":legacy,"expansion_id":int(e["id"])
    })
print(f"western_safe_candidates={len(rows)}",flush=True)

blueprints={}
for eid in sorted({r["expansion_id"] for r in rows}):
    blueprints[eid]=get(f"{BASE}/blueprints/export?expansion_id={eid}")

resolved=[]
for r in rows:
    cand=[]
    for b in blueprints[r["expansion_id"]]:
        if num((b.get("fixed_properties") or {}).get("collector_number"))!=num(r["local_id"]): continue
        rarity=str((b.get("fixed_properties") or {}).get("pokemon_rarity") or "").lower()
        if r["set_id"]=="mep" and "oversized" in rarity: continue
        cand.append(b)
    if len(cand)>1:
        exact=[b for b in cand if norm(b.get("name"))==norm(r["name"])]
        if len(exact)==1: cand=exact
    if len(cand)!=1: continue
    b=cand[0]
    resolved.append({
        **r,
        "blueprint_id":int(b["id"]),
        "tcg_player_id":int(b["tcg_player_id"]) if b.get("tcg_player_id") is not None else None,
    })
print(f"western_safe_resolved={len(resolved)}",flush=True)

market={}
for eid in sorted({r["expansion_id"] for r in resolved}):
    market[eid]=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)

updates=[]
for r in resolved:
    nm=[]; sp=[]
    for p in market[r["expansion_id"]].get(str(r["blueprint_id"]),[]):
        if p.get("graded"): continue
        props=p.get("properties_hash") or {}
        lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
        if lang and lang!="en": continue
        rv=next((x for k,x in props.items() if "reverse" in str(k).lower()),None)
        isrev=str(rv).lower() in ("true","1","yes")
        if r["legacy"]=="REVERSE" and not isrev: continue
        if r["legacy"]!="REVERSE" and isrev: continue
        price=p.get("price") or {}; cents=price.get("cents")
        if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR": continue
        try: unit=float(cents)/100/max(1,int(p.get("bundle_size") or 1))
        except Exception: continue
        cond=str(props.get("condition") or "").strip().lower()
        if cond in ("near mint","mint","nm"): nm.append(unit)
        elif cond=="slightly played": sp.append(unit)
    vals=nm; factor=NM_FACTOR; source="CARDTRADER_MARKETPLACE"; label="NM"
    if not vals and len(sp)>=3:
        vals=sp; factor=0.80; source="CARDTRADER_SP_INFERRED"; label="SP_INFERRED"
    if vals:
        vals.sort(); sample=vals[:min(7,len(vals))]
        listing=round(statistics.median(sample),4)
        base=round(listing/factor,4)
        updates.append((r,base,source,f"CardTrader western safe blueprint {r['blueprint_id']}; condition={label}; listings={len(vals)}"))

already={(r["card_id"],r["variant_id"]) for r,_,_,_ in updates}
try:
    usd_eur=float(get("https://api.frankfurter.dev/v2/rate/USD/EUR",auth=False).get("rate"))
except Exception:
    usd_eur=0.0

price_cache={}
for gid in sorted(set(TCGCSV_GROUP.values())):
    try:
        entries=get(f"https://tcgcsv.com/tcgplayer/3/{gid}/prices",auth=False).get("results") or []
    except Exception:
        entries=[]
    by_product={}
    for e in entries:
        try: pid=int(e.get("productId") or 0)
        except Exception: continue
        by_product.setdefault(pid,[]).append(e)
    price_cache[gid]=by_product

for r in resolved:
    if (r["card_id"],r["variant_id"]) in already or not r["tcg_player_id"] or usd_eur<=0: continue
    gid=TCGCSV_GROUP.get(r["set_id"])
    expected={"NORMAL":"normal","HOLO":"holofoil","REVERSE":"reverseholofoil"}.get(r["legacy"])
    cand=[e for e in price_cache.get(gid,{}).get(r["tcg_player_id"],[]) if norm(e.get("subTypeName"))==expected]
    if len(cand)!=1: continue
    usd=cand[0].get("marketPrice")
    if not isinstance(usd,(int,float)) or usd<=0: usd=cand[0].get("midPrice")
    if not isinstance(usd,(int,float)) or usd<=0: continue
    base=round(float(usd)*usd_eur/NM_FACTOR,4)
    updates.append((r,base,"TCGCSV_TCGPLAYER",f"TCGplayer exact product {r['tcg_player_id']} via CardTrader blueprint {r['blueprint_id']}"))

print(f"western_safe_updates={len(updates)}",flush=True)
if updates:
    sql=["BEGIN;"]
    for r,base,source,detail in updates:
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='en' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','en','{q(r['variant_id'])}','{source}',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"western_safe_applied={len(updates)}",flush=True)
