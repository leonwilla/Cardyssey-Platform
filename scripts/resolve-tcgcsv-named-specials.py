#!/usr/bin/env python3
import json,math,re,subprocess,urllib.request
from pathlib import Path

NM_FACTOR=0.92
GROUPS_BY_SET={
    "ex9":[1410,2374],
    "mep":[24451,2374],
    "mfb":[23330,2374],
    "me01":[24380,2374],
    "ex15":[1411,2374],
    "ex8":[1404,2374],
}
UA={"Accept":"application/json","User-Agent":"Cardyssey-tcgcsv-named-specials"}

def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True,
    ).stdout.strip()
def q(v):return str(v).replace("'","''")
def norm(v):return re.sub(r"[^a-z0-9]+","",str(v or "").lower())
def positive(v):return isinstance(v,(int,float)) and math.isfinite(v) and v>0

rate=get("https://api.frankfurter.dev/v2/rate/USD/EUR").get("rate")
if not positive(rate):
    raise SystemExit("USD/EUR unavailable")
usd_eur=float(rate)

raw=db("""SELECT c.card_id,c.set_id,c.name,p.variant_id,p.legacy_variant,c.variants::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
WHERE p.language_code='en' AND p.resolution_status='NO_PRICE'
  AND c.set_id IN ('ex9','mep','mfb','me01','ex15','ex8')
ORDER BY c.set_id,c.card_id,p.variant_id""")

rows=[]
for line in raw.splitlines():
    z=line.split("\t",5)
    if len(z)!=6:continue
    cid,setid,name,vid,legacy,vjson=z
    try:variants=json.loads(vjson or "[]")
    except Exception:continue
    v=next((x for x in variants if str(x.get("id") or "")==vid),None)
    if not v:continue
    if str(v.get("size") or "standard").lower()!="standard":continue
    stamps=[norm(x) for x in (v.get("stamps") or []) if norm(x)]
    if not stamps:continue
    rows.append({"card_id":cid,"set_id":setid,"name":name,"variant_id":vid,"legacy":legacy,"stamps":stamps})

groups=sorted({gid for r in rows for gid in GROUPS_BY_SET.get(r["set_id"],[])})
products={};prices={}
for gid in groups:
    products[gid]=get(f"https://tcgcsv.com/tcgplayer/3/{gid}/products").get("results") or []
    entries=get(f"https://tcgcsv.com/tcgplayer/3/{gid}/prices").get("results") or []
    by={}
    for e in entries:
        try:pid=int(e.get("productId") or 0)
        except (TypeError,ValueError):continue
        by.setdefault(pid,[]).append(e)
    prices[gid]=by

updates=[]
resolved=0
ambiguous=0
for r in rows:
    candidates=[]
    card_name=norm(r["name"])
    for gid in GROUPS_BY_SET.get(r["set_id"],[]):
        for p in products.get(gid,[]):
            text=norm(p.get("cleanName") or p.get("name"))
            if not card_name or card_name not in text:
                continue
            if not all(tag in text for tag in r["stamps"]):
                continue
            candidates.append((gid,p))
    # Same product can be discovered only once per group; require one exact
    # name+all-stamps match across all curated groups.
    unique={(gid,int(p["productId"])):(gid,p) for gid,p in candidates}
    if len(unique)!=1:
        if len(unique)>1:ambiguous+=1
        continue
    gid,p=next(iter(unique.values()))
    resolved+=1
    entries=prices.get(gid,{}).get(int(p["productId"]),[])
    expected={"NORMAL":"normal","HOLO":"holofoil","REVERSE":"reverseholofoil"}.get(r["legacy"])
    exact=[e for e in entries if norm(e.get("subTypeName"))==expected]
    if len(exact)==1:
        entry=exact[0]
    elif len(entries)==1:
        # The exact named special product has only one market subtype.
        entry=entries[0]
    else:
        continue
    usd=entry.get("marketPrice")
    if not positive(usd):usd=entry.get("midPrice")
    if not positive(usd):continue
    base=round((float(usd)*usd_eur)/NM_FACTOR,4)
    updates.append((r,gid,int(p["productId"]),str(p.get("name") or ""),str(entry.get("subTypeName") or ""),base))

print(f"named_special_candidates={len(rows)} resolved={resolved} ambiguous={ambiguous} updates={len(updates)}",flush=True)
for r,gid,pid,pname,subtype,base in updates:
    print(f"named_special={r['card_id']}:{r['variant_id']} -> {pid} {pname} {subtype} EUR={base:.4f}",flush=True)

if updates:
    sql=["BEGIN;"]
    for r,gid,pid,pname,subtype,base in updates:
        detail=f"TCGplayer exact named special product {pid}; {subtype}; group {gid}; {pname}"
        sql.append(
            f"UPDATE tcg_price_cache SET source='TCGCSV_TCGPLAYER_NAMED_SPECIAL',base_eur={base:.4f},"
            f"updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',"
            f"next_attempt_at=NOW()+INTERVAL '7 days' "
            f"WHERE card_id='{q(r['card_id'])}' AND language_code='en' "
            f"AND variant_id='{q(r['variant_id'])}' AND resolution_status='NO_PRICE';"
        )
        sql.append(
            f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) "
            f"VALUES('{q(r['card_id'])}','en','{q(r['variant_id'])}','TCGCSV_TCGPLAYER_NAMED_SPECIAL',{base:.4f},NOW());"
        )
    sql.append("COMMIT;")
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
        input="\n".join(sql),text=True,check=True,
    )
    print(f"named_special_applied={len(updates)}",flush=True)
