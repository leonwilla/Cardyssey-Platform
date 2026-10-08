#!/usr/bin/env python3
import concurrent.futures, json, re, statistics, subprocess, urllib.parse, urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"; NM_FACTOR=0.92
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="): TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-special-cardtrader"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:return json.load(r)
def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v):return str(v).replace("'","''")
def norm(v):return re.sub(r"[^a-z0-9]+","",str(v or "").lower())
def num(v):
    s=str(v or "").strip().lower().split("/",1)[0].strip()
    if s.isdigit():return str(int(s))
    m=re.fullmatch(r"0*(\d+)([a-z]+)",s)
    return str(int(m.group(1)))+m.group(2) if m else s

def event_tags_from_stamps(stamps):
    raw={norm(x) for x in stamps}
    recognized=set()
    unknown=set()
    for tag in raw:
        if re.fullmatch(r"worlds20\d\d",tag):
            continue
        if tag in {"staff","mitarbeiter"}: recognized.add("staff")
        elif tag=="topthirtytwo": recognized.add("topthirtytwo")
        elif tag=="topsixteen": recognized.add("topsixteen")
        elif tag=="quarterfinalist": recognized.add("quarterfinalist")
        elif tag=="semifinalist": recognized.add("semifinalist")
        elif tag=="finalist": recognized.add("finalist")
        else: unknown.add(tag)
    return recognized,unknown

def event_tags_from_version(version):
    v=norm(version)
    tags=set()
    if "staff" in v:tags.add("staff")
    if "topthirtytwo" in v:tags.add("topthirtytwo")
    if "topsixteen" in v:tags.add("topsixteen")
    if "quarterfinalist" in v:tags.add("quarterfinalist")
    if "semifinalist" in v:tags.add("semifinalist")
    if "finalist" in v and "semifinalist" not in v and "quarterfinalist" not in v:tags.add("finalist")
    return tags

exp=[x for x in get(f"{BASE}/expansions") if int(x.get("game_id") or 0)==5]
by_code={};by_name={}
for e in exp:
    if norm(e.get("code")):by_code.setdefault(norm(e.get("code")),[]).append(e)
    if norm(e.get("name")):by_name.setdefault(norm(e.get("name")),[]).append(e)

raw=db("""SELECT p.card_id,p.language_code,p.variant_id,p.legacy_variant,c.local_id,c.name,c.variants::text,
COALESCE(s.printed_code,''),COALESCE(es.name,s.name,''),COALESCE(s.name,''),c.set_id
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
LEFT JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
LEFT JOIN catalog_sets_mirror es ON es.language_code='en' AND es.set_id=c.set_id
WHERE p.resolution_status='NO_PRICE' AND c.language_code IN ('de','en')
ORDER BY c.language_code,c.set_id,c.card_id,p.variant_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t",10)
    if len(z)!=11:continue
    cid,lang,vid,legacy,local_id,name,vjson,code,enname,setname,setid=z
    try:variants=json.loads(vjson or "[]")
    except Exception:continue
    variant=next((x for x in variants if str(x.get("id") or "")==vid),None)
    if not variant:continue
    stamps=variant.get("stamps") or []
    tags,unknown=event_tags_from_stamps(stamps)
    # Only special-event rows. Unknown stamp labels are allowed only when the
    # exact label is later present in the CardTrader blueprint name/version.
    if not tags and not unknown and not any(re.fullmatch(r"worlds-20\d\d",str(x or "").lower()) for x in stamps):continue
    matches=[]
    if norm(code) and norm(code) in by_code:matches+=by_code[norm(code)]
    if norm(enname) and norm(enname) in by_name:matches+=by_name[norm(enname)]
    if norm(setname) and norm(setname) in by_name:matches+=by_name[norm(setname)]
    uniq={e["id"]:e for e in matches}
    if len(uniq)!=1:continue
    e=next(iter(uniq.values()))
    rows.append({"card_id":cid,"language":lang,"variant_id":vid,"legacy":legacy,"local_id":local_id,"name":name,"tags":tags,"unknown_tags":unknown,"set_id":setid,"expansion_id":int(e["id"])})
print(f"special_candidates={len(rows)}",flush=True)

eids=sorted({r["expansion_id"] for r in rows})
blueprints={}
def load_bp(eid):
    try:return eid,get(f"{BASE}/blueprints/export?expansion_id={eid}",30)
    except Exception:return eid,[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for eid,bps in pool.map(load_bp,eids):blueprints[eid]=bps

resolved=[]
for r in rows:
    cand=[]
    for b in blueprints.get(r["expansion_id"],[]):
        bp_num=num((b.get("fixed_properties") or {}).get("collector_number"))
        target_num=num(r["local_id"])
        if bp_num!=target_num:
            # Some stamped products (for example My First Battle) use deck
            # letters instead of collector numbers in CardTrader. Permit a
            # mismatch only when exact stamp token(s) and card name identify
            # the blueprint; uniqueness is still required below.
            if not (
                r["unknown_tags"]
                and norm(r["name"]) in norm(b.get("name"))
            ):
                continue
        if event_tags_from_version(b.get("version"))!=r["tags"]:continue
        blueprint_text=norm(str(b.get("name") or "")+" "+str(b.get("version") or ""))
        if r["unknown_tags"] and not all(tag in blueprint_text for tag in r["unknown_tags"]):
            continue
        cand.append(b)
    if len(cand)>1:
        exact=[b for b in cand if norm(b.get("name"))==norm(r["name"])]
        if len(exact)==1:cand=exact
    if len(cand)!=1:continue
    b=cand[0]
    cmids=[]
    for value in b.get("card_market_ids") or []:
        try: cmids.append(int(value))
        except (TypeError,ValueError): pass
    resolved.append({
        **r,
        "blueprint_id":int(b["id"]),
        "version":str(b.get("version") or ""),
        "cardmarket_id":cmids[0] if len(cmids)==1 else None,
        "tcg_player_id":(
            int(b["tcg_player_id"])
            if b.get("tcg_player_id") is not None
            else None
        ),
    })
print(f"special_resolved={len(resolved)} de={sum(1 for r in resolved if r['language']=='de')} en={sum(1 for r in resolved if r['language']=='en')}",flush=True)
identity_rows=[r for r in resolved if r["cardmarket_id"] is not None]
if identity_rows:
    vals=[
        f"('{q(r['card_id'])}','{q(r['language'])}','{q(r['variant_id'])}',"
        f"{r['cardmarket_id']},{r['blueprint_id']},{r['expansion_id']},'western-special')"
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
print(f"special_variant_identities={len(identity_rows)}",flush=True)

langmap={"de":"de","en":"en"}
groups={}
for r in resolved:groups.setdefault(r["expansion_id"],[]).append(r)
updates=[]
reasons={"no_products":0,"condition":0,"language":0,"price":0}
for gi,(eid,group) in enumerate(sorted(groups.items()),1):
    try:payload=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)
    except Exception:continue
    for r in group:
        products=payload.get(str(r["blueprint_id"]),[]) if isinstance(payload,dict) else []
        if not products:reasons["no_products"]+=1
        nm_values=[]
        sp_values=[]
        for p in products:
            if p.get("graded"):continue
            props=p.get("properties_hash") or {}
            actual=str(props.get("pokemon_language") or props.get("language") or "").strip()
            if actual and actual.lower()!=langmap[r["language"]].lower():reasons["language"]+=1;continue
            price=p.get("price") or {};cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
                reasons["price"]+=1;continue
            try:unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
            except Exception:continue
            cond=str(props.get("condition") or "").strip().lower()
            if cond in ("near mint","mint","nm"):
                nm_values.append(unit)
            elif cond=="slightly played":
                sp_values.append(unit)
            else:
                reasons["condition"]+=1
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
            values.sort();sample=values[:min(7,len(values))]
            listing=round(statistics.median(sample),4);base=round(listing/factor,4)
            updates.append((r,base,listing,len(values),source,condition_label))
    print(f"special_market={gi}/{len(groups)} updates={len(updates)}",flush=True)
print("special_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"special_price_updates={len(updates)}",flush=True)

# CardTrader can identify rare event printings even when its own marketplace is
# empty. Reuse that exact blueprint -> TCGplayer product identity against the
# free TCGCSV feed for English copies only.
TCGCSV_GROUPS={
    "dpp":1421,
    "np":1423,
    "bwp":1407,
    "basep":1418,
    "mfb":23330,
}
tcg_updates=[]
already={(r["card_id"],r["language"],r["variant_id"]) for r,_,_,_,_,_ in updates}

def public_json(url):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"Cardyssey-special-tcgcsv"})
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
        try:pid=int(entry.get("productId") or 0)
        except (TypeError,ValueError):continue
        by_product.setdefault(pid,[]).append(entry)
    for r in items:
        key=(r["card_id"],r["language"],r["variant_id"])
        if key in already or usd_eur<=0:
            continue
        expected={"NORMAL":"normal","HOLO":"holofoil","REVERSE":"reverseholofoil"}.get(r["legacy"])
        product_entries=by_product.get(r["tcg_player_id"],[])
        candidates=[
            e for e in product_entries
            if norm(e.get("subTypeName"))==expected
        ]
        # For an exact special-printing blueprint, TCGplayer sometimes exposes
        # only one market subtype even when our catalog labels the physical
        # print differently. A single product price is still unambiguous.
        if len(candidates)==1:
            entry=candidates[0]
        elif len(candidates)==0 and len(product_entries)==1:
            entry=product_entries[0]
        else:
            continue
        usd=entry.get("marketPrice")
        if not isinstance(usd,(int,float)) or usd<=0:
            usd=entry.get("midPrice")
        if not isinstance(usd,(int,float)) or usd<=0:
            continue
        base=round((float(usd)*usd_eur)/NM_FACTOR,4)
        tcg_updates.append((r,base,str(entry.get("subTypeName") or "")))

print(f"special_tcgcsv_updates={len(tcg_updates)}",flush=True)

if updates or tcg_updates:
    sql=["BEGIN;"]
    for r,base,listing,count,source,condition_label in updates:
        detail=f"CardTrader special blueprint {r['blueprint_id']}; {r['version']}; condition={condition_label}; median listing EUR {listing:.4f}; listings {count}"
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='{q(r['language'])}' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','{q(r['language'])}','{q(r['variant_id'])}','{source}',{base:.4f},NOW());")
    for r,base,subtype in tcg_updates:
        detail=f"TCGplayer product {r['tcg_player_id']}; {subtype}; via CardTrader special blueprint {r['blueprint_id']}"
        sql.append(f"UPDATE tcg_price_cache SET source='TCGCSV_TCGPLAYER',base_eur={base:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='{q(r['language'])}' AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','{q(r['language'])}','{q(r['variant_id'])}','TCGCSV_TCGPLAYER',{base:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"special_applied_cardtrader={len(updates)}",flush=True)
    print(f"special_applied_tcgcsv={len(tcg_updates)}",flush=True)
