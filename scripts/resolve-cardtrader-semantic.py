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
    resolved.append({**r,"blueprint_id":int(b["id"]),"blueprint_name":str(b.get("name") or ""),"cardmarket_id":cmids[0] if len(cmids)==1 else None})
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

langmap={"de":"de","en":"en","ja":"jp","zh-cn":"zh-CN","zh-tw":"zh-TW"}
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
        values=[]
        for p in products:
            if p.get("graded"): reason_totals["graded"]+=1; continue
            props=p.get("properties_hash") or {}
            cond=str(props.get("condition") or "").strip().lower()
            if cond not in ("near mint","mint","nm"): reason_totals["condition"]+=1; continue
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
            values.append(unit)
        if values:
            values.sort(); sample=values[:min(7,len(values))]
            listing=round(statistics.median(sample),4); base=round(listing/NM_FACTOR,4)
            updates.append((r,base,listing,len(values)))
    print(f"semantic_market={gi}/{len(groups)} updates={len(updates)}",flush=True)

print("semantic_reasons="+json.dumps(reason_totals,separators=(",",":")),flush=True)
print(f"semantic_price_updates={len(updates)}",flush=True)
if updates:
    sql=["BEGIN;"]
    for r,base,listing,count in updates:
        detail=f"CardTrader semantic blueprint {r['blueprint_id']}; median cheapest NM EUR {listing:.4f}; listings {count}"
        sql.append(f"UPDATE tcg_price_cache SET source='CARDTRADER_MARKETPLACE',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='{q(r['language'])}' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','{q(r['language'])}','{q(r['variant_id'])}','CARDTRADER_MARKETPLACE',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"semantic_applied={len(updates)}",flush=True)
