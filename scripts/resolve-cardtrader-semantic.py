#!/usr/bin/env python3
import concurrent.futures, json, re, statistics, subprocess, urllib.parse, urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"; NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="): TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-semantic-cardtrader"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r: return json.load(r)
def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v): return str(v).replace("'","''")
def norm(v): return re.sub(r"[^a-z0-9]+","",str(v or "").lower())
def num(v):
    s=str(v or "").strip().lower()
    s=s.split("/",1)[0].strip()
    s=re.sub(r"\s+","",s)
    if s.isdigit(): return str(int(s))
    m=re.fullmatch(r"0*(\d+)([a-z]+)",s)
    return (str(int(m.group(1)))+m.group(2)) if m else s

exp=[x for x in get(f"{BASE}/expansions") if int(x.get("game_id") or 0)==5]
by_code={}; by_name={}
for e in exp:
    if norm(e.get("code")): by_code.setdefault(norm(e.get("code")),[]).append(e)
    if norm(e.get("name")): by_name.setdefault(norm(e.get("name")),[]).append(e)

raw=db("""SELECT p.card_id,p.language_code,p.variant_id,p.legacy_variant,c.local_id,c.name,c.variants::text,
COALESCE(s.printed_code,''),COALESCE(es.name,s.name,''),COALESCE(s.name,''),c.set_id
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
LEFT JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
LEFT JOIN catalog_sets_mirror es ON es.language_code='en' AND es.set_id=c.set_id
WHERE p.resolution_status='NO_PRICE' AND c.language_code IN ('de','en','ja','zh-cn','zh-tw')
  AND NOT EXISTS (
    SELECT 1 FROM price_source_routing rt
    WHERE rt.language_code=p.language_code AND rt.card_id=p.card_id
      AND rt.variant_id=p.variant_id
      AND rt.verification_state='VERIFIED_PRODUCT_ID'
      AND rt.primary_provider<>'CARDTRADER'
  )

ORDER BY c.language_code,c.set_id,c.card_id,p.variant_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t",10)
    if len(z)!=11: continue
    cid,lang,vid,legacy,local_id,name,vjson,code,enname,setname,setid=z
    try: variants=json.loads(vjson or "[]")
    except Exception: continue
    v=next((x for x in variants if str(x.get("id") or "")==vid),None)
    if not v or v.get("stamps") or v.get("subtype") or v.get("foil") or str(v.get("size") or "").lower() not in ("","standard"): continue
    if legacy not in ("NORMAL","HOLO","REVERSE"): continue
    matches=[]
    if norm(code) and norm(code) in by_code: matches+=by_code[norm(code)]
    if norm(enname) and norm(enname) in by_name: matches+=by_name[norm(enname)]
    if norm(setname) and norm(setname) in by_name: matches+=by_name[norm(setname)]
    if lang in ("ja","zh-cn","zh-tw") and norm(setid) and norm(setid) in by_code:
        matches+=by_code[norm(setid)]
    uniq={e["id"]:e for e in matches}
    if len(uniq)!=1: continue
    e=next(iter(uniq.values()))
    rows.append({"card_id":cid,"language":lang,"variant_id":vid,"legacy":legacy,"local_id":local_id,"name":name,"set_id":setid,"expansion_id":int(e["id"]),"expansion_name":e["name"]})
print(f"semantic_set_candidates={len(rows)}",flush=True)

eids=sorted({r["expansion_id"] for r in rows})
def load_bp(eid):
    try: return eid,get(f"{BASE}/blueprints/export?expansion_id={eid}",30)
    except Exception as e: print(f"blueprint_error expansion={eid} error={e!r}",flush=True); return eid,[]
blueprints={}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    for eid,bps in pool.map(load_bp,eids): blueprints[eid]=bps
print(f"semantic_expansions_loaded={len(blueprints)}",flush=True)

langmap={"de":"de","en":"en","ja":"jp","zh-cn":"zh-CN","zh-tw":"zh-TW"}
supported_languages={}
expansion_by_id={int(e["id"]):e for e in exp}
for eid,bps in blueprints.items():
    values=set()
    for b in bps:
        for prop in b.get("editable_properties") or []:
            if prop.get("name")=="pokemon_language":
                values.update(str(x) for x in prop.get("possible_values") or [])
    expansion=expansion_by_id.get(eid,{})
    expansion_name=str(expansion.get("name") or "").lower()
    expansion_code=str(expansion.get("code") or "").lower()
    if "simplified chinese" in expansion_name or expansion_code=="csmpic":
        values.add("zh-CN")
    if "traditional chinese" in expansion_name:
        values.add("zh-TW")
    supported_languages[eid]=values

rows=[
    r for r in rows
    if langmap.get(r["language"]) in supported_languages.get(r["expansion_id"],set())
]
print(f"semantic_language_supported={len(rows)}",flush=True)

indexes={}
for eid,bps in blueprints.items():
    idx={}
    for b in bps:
        n=num((b.get("fixed_properties") or {}).get("collector_number"))
        if not n:
            m=re.search(r"([A-Za-z]*\d+[A-Za-z]*)\s*/\s*\d+",str(b.get("version") or ""))
            n=num(m.group(1)) if m else ""
        if n: idx.setdefault(n,[]).append(b)
    indexes[eid]=idx

resolved=[]
ambiguous=0
for r in rows:
    cand=indexes.get(r["expansion_id"],{}).get(num(r["local_id"]),[])
    if len(cand)>1:
        exact=[b for b in cand if norm(b.get("name"))==norm(r["name"])]
        if len(exact)==1: cand=exact
    if len(cand)!=1:
        if len(cand)>1: ambiguous+=1
        continue
    b=cand[0]
    cmids=[]
    for x in b.get("card_market_ids") or []:
        try: cmids.append(int(x))
        except Exception: pass
    resolved.append({
        **r,
        "blueprint_id":int(b["id"]),
        "blueprint_name":str(b.get("name") or ""),
        "cardmarket_id":cmids[0] if len(cmids)==1 else None,
        "tcg_player_id":(
            int(b["tcg_player_id"])
            if b.get("tcg_player_id") is not None
            else None
        ),
    })
print(f"semantic_blueprints_resolved={len(resolved)} ambiguous={ambiguous}",flush=True)
for lang in ["de","en","ja","zh-cn","zh-tw"]:
    print(f"semantic_lang={lang} resolved={sum(1 for r in resolved if r['language']==lang)}",flush=True)

cache={}
for r in resolved:
    cache[(r["card_id"],r["language"])]=r
if cache:
    vals=[]
    for (cid,lang),r in cache.items():
        cm="NULL" if r["cardmarket_id"] is None else str(r["cardmarket_id"])
        vals.append(f"('{q(cid)}','{q(lang)}',{cm},{r['blueprint_id']},{r['expansion_id']})")
    db("INSERT INTO cardtrader_identity_cache(card_id,language_code,cardmarket_product_id,blueprint_id,expansion_id) VALUES "+",".join(vals)+
       " ON CONFLICT(card_id,language_code) DO UPDATE SET cardmarket_product_id=COALESCE(EXCLUDED.cardmarket_product_id,cardtrader_identity_cache.cardmarket_product_id),blueprint_id=EXCLUDED.blueprint_id,expansion_id=EXCLUDED.expansion_id,updated_at=NOW()")

groups={}
for r in resolved: groups.setdefault(r["expansion_id"],[]).append(r)
updates=[]
reason_totals={"no_products":0,"graded":0,"condition":0,"language":0,"reverse":0,"price":0}
for gi,(eid,group) in enumerate(sorted(groups.items()),1):
    try: payload=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)
    except Exception as e:
        print(f"market_error expansion={eid} error={e!r}",flush=True); continue
    for r in group:
        products=payload.get(str(r["blueprint_id"]),[]) if isinstance(payload,dict) else []
        if not products: reason_totals["no_products"]+=1
        nm_values=[]
        sp_values=[]
        for p in products:
            if p.get("graded"): reason_totals["graded"]+=1; continue
            props=p.get("properties_hash") or {}
            actual=str(props.get("pokemon_language") or props.get("language") or "").strip()
            expected=langmap.get(r["language"],"")
            if actual and expected and actual.lower()!=expected.lower(): reason_totals["language"]+=1; continue
            rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
            isrev=str(rv).lower() in ("true","1","yes")
            if r["legacy"]=="REVERSE" and not isrev: reason_totals["reverse"]+=1; continue
            if r["legacy"]!="REVERSE" and isrev: reason_totals["reverse"]+=1; continue
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
        if (
            not values
            and r["language"] in ("ja","zh-cn","zh-tw")
            and len(sp_values)>=3
        ):
            values=sp_values
            factor=0.80
            source="CARDTRADER_SP_INFERRED"
            condition_label="SP_INFERRED"
        if values:
            values.sort(); sample=values[:min(7,len(values))]
            listing=round(statistics.median(sample),4); base=round(listing/factor,4)
            updates.append((r,base,listing,len(values),source,condition_label))
    print(f"semantic_market={gi}/{len(groups)} updates={len(updates)}",flush=True)

print("semantic_reasons="+json.dumps(reason_totals,separators=(",",":")),flush=True)
print(f"semantic_price_updates={len(updates)}",flush=True)

# English fallback: exact CardTrader blueprint identities often expose the
# TCGplayer product id even when CardTrader has no current marketplace listing.
# Reuse that exact id against the free TCGCSV feed.
TCGCSV_GROUPS={
    "dpp":1421,
    "mep":24451,
    "bwp":1407,
    "basep":1418,
    "tk-xy-b":1533,
    "tk-xy-w":1533,
}
tcg_updates=[]
already={(r["card_id"],r["language"],r["variant_id"]) for r,_,_,_,_,_ in updates}

def public_json(url):
    req=urllib.request.Request(
        url,
        headers={"Accept":"application/json","User-Agent":"Cardyssey-semantic-tcgcsv"},
    )
    with urllib.request.urlopen(req,timeout=20) as response:
        return json.load(response)

try:
    usd_eur=float(public_json("https://api.frankfurter.dev/v2/rate/USD/EUR").get("rate"))
except Exception:
    usd_eur=0.0

price_groups={}
for r in resolved:
    gid=TCGCSV_GROUPS.get(r["set_id"])
    if r["language"]!="en" or gid is None or r["tcg_player_id"] is None:
        continue
    price_groups.setdefault(gid,[]).append(r)

for gid,items in price_groups.items():
    try:
        entries=public_json(f"https://tcgcsv.com/tcgplayer/3/{gid}/prices").get("results") or []
    except Exception:
        continue
    by_product={}
    for entry in entries:
        try: pid=int(entry.get("productId") or 0)
        except (TypeError,ValueError): continue
        by_product.setdefault(pid,[]).append(entry)
    for r in items:
        key=(r["card_id"],r["language"],r["variant_id"])
        if key in already or usd_eur<=0:
            continue
        expected={
            "NORMAL":"normal",
            "HOLO":"holofoil",
            "REVERSE":"reverseholofoil",
        }.get(r["legacy"])
        candidates=[
            e for e in by_product.get(r["tcg_player_id"],[])
            if norm(e.get("subTypeName"))==expected
        ]
        if len(candidates)!=1:
            continue
        entry=candidates[0]
        usd=entry.get("marketPrice")
        if not isinstance(usd,(int,float)) or usd<=0:
            usd=entry.get("midPrice")
        if not isinstance(usd,(int,float)) or usd<=0:
            continue
        base=round((float(usd)*usd_eur)/NM_FACTOR,4)
        tcg_updates.append((r,base,str(entry.get("subTypeName") or "")))

print(f"semantic_tcgcsv_updates={len(tcg_updates)}",flush=True)

if updates or tcg_updates:
    sql=["BEGIN;"]
    for r,base,listing,count,source,condition_label in updates:
        detail=f"CardTrader semantic blueprint {r['blueprint_id']}; condition={condition_label}; median listing EUR {listing:.4f}; listings {count}"
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='{q(r['language'])}' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','{q(r['language'])}','{q(r['variant_id'])}','{source}',{base:.4f},NOW());")
    for r,base,subtype in tcg_updates:
        detail=f"TCGplayer product {r['tcg_player_id']}; {subtype}; via CardTrader semantic blueprint {r['blueprint_id']}"
        sql.append(f"UPDATE tcg_price_cache SET source='TCGCSV_TCGPLAYER',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='{q(r['language'])}' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','{q(r['language'])}','{q(r['variant_id'])}','TCGCSV_TCGPLAYER',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"semantic_applied_cardtrader={len(updates)}",flush=True)
    print(f"semantic_applied_tcgcsv={len(tcg_updates)}",flush=True)
