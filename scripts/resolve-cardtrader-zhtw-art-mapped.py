#!/usr/bin/env python3
"""Price conservative Traditional-Chinese cards from audited art identities.

The mapping file is generated once from local card artwork and contains only
high-confidence matches to an exact Japanese source printing. Runtime pricing
does not use image matching: it resolves that exact Japanese set/number to a
CardTrader blueprint and accepts only Traditional-Chinese marketplace listings.
"""
import json,re,statistics,subprocess,urllib.parse,urllib.request
from pathlib import Path

BASE="https://api.cardtrader.com/api/v2"
NM_FACTOR=0.92
SP_FACTOR=0.80
ROOT=Path(__file__).resolve().parent
MAPPING_FILE=ROOT/"zhtw-art-identities.json"
SOURCE_BLUEPRINT_FILE=ROOT/"zhtw-source-blueprints.json"
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip()
        break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-zhtw-art-map"}

def get(url,timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url,headers=H),timeout=timeout) as r:
        return json.load(r)

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True,
    ).stdout.strip()

def q(v): return str(v).replace("'","''")

def num(v):
    s=str(v or "").strip().lower().split("/",1)[0].strip()
    if s.isdigit(): return str(int(s))
    return re.sub(r"^0+(?=\d)","",s)

if not TOKEN:
    print("zhtw_art_disabled=no_token",flush=True)
    raise SystemExit(0)
if not MAPPING_FILE.exists():
    print("zhtw_art_disabled=no_mapping",flush=True)
    raise SystemExit(0)

mappings=json.loads(MAPPING_FILE.read_text())
source_blueprints=(
    json.loads(SOURCE_BLUEPRINT_FILE.read_text())
    if SOURCE_BLUEPRINT_FILE.exists()
    else {}
)
print(
    f"zhtw_art_mappings={len(mappings)} source_blueprints={len(source_blueprints)}",
    flush=True,
)

# Only keep mappings whose exact target variant is still unresolved.
open_raw=db("""SELECT card_id,variant_id
FROM tcg_price_cache
WHERE language_code='zh-tw' AND resolution_status='NO_PRICE'""")
open_keys={tuple(x.split("\t",1)) for x in open_raw.splitlines() if "\t" in x}
rows=[m for m in mappings if (m["card_id"],m["variant_id"]) in open_keys]
print(f"zhtw_art_open={len(rows)}",flush=True)
if not rows:
    raise SystemExit(0)

expansions=[e for e in get(f"{BASE}/expansions") if int(e.get("game_id") or 0)==5]
by_code={str(e.get("code") or "").lower():e for e in expansions}

# Exact source set/collector-number -> one CardTrader blueprint.
SOURCE_CODE_ALIASES={"S3a":"ls3","S5I":"s5l","SGI":"sgl"}
source_sets=sorted({m["source_set"] for m in rows})
blueprints={}
indexes={}
for sid in source_sets:
    # Aggregated Japanese starter-deck sets such as SA/SCS are split across
    # several CardTrader expansions and are resolved per exact source artwork.
    if sid in ("SA","SCS"):
        continue
    source_code=SOURCE_CODE_ALIASES.get(sid,sid)
    exp=by_code.get(str(source_code).lower())
    if not exp:
        print(f"zhtw_art_missing_expansion={sid}",flush=True)
        continue
    eid=int(exp["id"])
    bps=get(f"{BASE}/blueprints/export?expansion_id={eid}",30)
    blueprints[sid]=(eid,bps)
    idx={}
    for b in bps:
        n=num((b.get("fixed_properties") or {}).get("collector_number"))
        if not n:
            mt=re.search(r"([A-Za-z]*\d+[A-Za-z]*)\s*/\s*\d+",str(b.get("version") or ""))
            n=num(mt.group(1)) if mt else ""
        if n:
            idx.setdefault(n,[]).append(b)
    indexes[sid]=idx

resolved=[]
ambiguous=0
for m in rows:
    source_override=source_blueprints.get(str(m.get("source_card_id") or ""))
    if source_override:
        resolved.append({
            **m,
            "blueprint_id":int(source_override["blueprint_id"]),
            "expansion_id":int(source_override["expansion_id"]),
        })
        continue
    cand=indexes.get(m["source_set"],{}).get(num(m["source_local_id"]),[])
    if len(cand)!=1:
        if len(cand)>1: ambiguous+=1
        continue
    b=cand[0]
    eid=blueprints[m["source_set"]][0]
    resolved.append({**m,"blueprint_id":int(b["id"]),"expansion_id":eid})

print(f"zhtw_art_resolved={len(resolved)} ambiguous={ambiguous}",flush=True)

# Cache blueprint identity only. Do NOT copy the Japanese Cardmarket product id:
# the official Cardmarket guide would then price the Japanese product rather
# than the Traditional-Chinese language listing.
if resolved:
    vals=[
        f"('{q(r['card_id'])}','zh-tw','{q(r['variant_id'])}',NULL,{r['blueprint_id']},{r['expansion_id']},'zhtw-art-exact')"
        for r in resolved
    ]
    db(
        "INSERT INTO cardtrader_variant_identity_cache"
        "(card_id,language_code,variant_id,cardmarket_product_id,blueprint_id,expansion_id,method) VALUES "
        + ",".join(vals)
        + " ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET "
          "cardmarket_product_id=NULL,"
          "blueprint_id=EXCLUDED.blueprint_id,"
          "expansion_id=EXCLUDED.expansion_id,"
          "method=EXCLUDED.method,updated_at=NOW()"
    )

groups={}
for r in resolved:
    groups.setdefault(r["expansion_id"],[]).append(r)

updates=[]
reasons={"no_products":0,"graded":0,"language":0,"reverse":0,"condition":0,"price":0}
for gi,(eid,group) in enumerate(sorted(groups.items()),1):
    try:
        payload=get(f"{BASE}/marketplace/products?"+urllib.parse.urlencode({"expansion_id":eid}),40)
    except Exception as e:
        print(f"zhtw_art_market_error expansion={eid} error={e!r}",flush=True)
        continue
    before=len(updates)
    for r in group:
        products=payload.get(str(r["blueprint_id"]),[]) if isinstance(payload,dict) else []
        if not products: reasons["no_products"]+=1
        nm=[]; sp=[]
        for p in products:
            if p.get("graded"):
                reasons["graded"]+=1
                continue
            props=p.get("properties_hash") or {}
            lang=str(props.get("pokemon_language") or props.get("language") or "").strip().lower()
            if lang!="zh-tw":
                reasons["language"]+=1
                continue
            rv=next((v for k,v in props.items() if "reverse" in str(k).lower()),None)
            if str(rv).lower() in ("true","1","yes"):
                reasons["reverse"]+=1
                continue
            price=p.get("price") or {}
            cents=price.get("cents")
            if not isinstance(cents,(int,float)) or cents<=0 or str(price.get("currency") or "").upper()!="EUR":
                reasons["price"]+=1
                continue
            try:
                unit=float(cents)/100.0/max(1,int(p.get("bundle_size") or 1))
            except Exception:
                reasons["price"]+=1
                continue
            cond=str(props.get("condition") or "").strip().lower()
            if cond in ("near mint","mint","nm"):
                nm.append(unit)
            elif cond=="slightly played":
                sp.append(unit)
            else:
                reasons["condition"]+=1

        vals=nm
        factor=NM_FACTOR
        source="CARDTRADER_MARKETPLACE"
        condition="NM"
        if not vals and len(sp)>=3:
            vals=sp
            factor=SP_FACTOR
            source="CARDTRADER_SP_INFERRED"
            condition="SP_INFERRED"
        if vals:
            vals.sort()
            sample=vals[:min(7,len(vals))]
            listing=round(statistics.median(sample),4)
            base=round(listing/factor,4)
            detail=(
                f"CardTrader zh-TW art identity {r['source_set']}-{r['source_local_id']} "
                f"blueprint {r['blueprint_id']}; condition={condition}; "
                f"listings={len(vals)}; art_distance={r['distance']}; art_margin={r['margin']}"
            )
            updates.append((r,base,source,detail))
    print(
        f"zhtw_art_market={gi}/{len(groups)} "
        f"resolved_group={len(group)} updates_group={len(updates)-before} total_updates={len(updates)}",
        flush=True,
    )

print("zhtw_art_reasons="+json.dumps(reasons,separators=(",",":")),flush=True)
print(f"zhtw_art_updates={len(updates)}",flush=True)

if updates:
    sql=["BEGIN;"]
    for r,base,source,detail in updates:
        sql.append(
            f"UPDATE tcg_price_cache SET source='{source}',base_eur={base:.4f},updated_at=NOW(),"
            f"resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',"
            f"next_attempt_at=NOW()+INTERVAL '7 days' "
            f"WHERE card_id='{q(r['card_id'])}' AND language_code='zh-tw' "
            f"AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';"
        )
        sql.append(
            f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) "
            f"VALUES('{q(r['card_id'])}','zh-tw','{q(r['variant_id'])}','{source}',{base:.4f},NOW());"
        )
    sql.append("COMMIT;")
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
        input="\n".join(sql),text=True,check=True,
    )
    print(f"zhtw_art_applied={len(updates)}",flush=True)
