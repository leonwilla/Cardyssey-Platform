#!/usr/bin/env python3
"""Backfill remaining English physical variant prices from TCGCSV/TCGplayer.

Processes only NO_PRICE cache rows. Matching is fail-closed by set, exact card
number/name, edition stamp and TCGplayer price subtype.
"""
import json, math, re, subprocess, time, requests, urllib.parse

USD_TO_EUR=0.88739
UA={"User-Agent":"Cardyssey/0.2 price-backfill"}

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def q(s): return str(s).replace("'","''")
def norm(s): return re.sub(r"[^a-z0-9]+","",str(s or "").lower())

def card_num(s):
    s=urllib.parse.unquote(str(s or "")).strip().split("/")[0].strip()
    if s in ("?","!"): return s
    n=norm(s)
    if n.isdigit(): return n.lstrip("0") or "0"
    m=re.fullmatch(r"([a-z]+)0*([0-9]+)",n)
    if m: return f"{m.group(1)}{int(m.group(2))}"
    return n

def numeric_tail(s):
    n=card_num(s)
    m=re.search(r"([0-9]+)$",n)
    return str(int(m.group(1))) if m else ""

def product_num(product):
    for x in product.get("extendedData") or []:
        if str(x.get("name") or "").lower()=="number":
            return card_num(x.get("value"))
    return ""

def name_key(s):
    s=re.sub(r"\s*\([^)]*\)\s*$","",str(s or ""))
    # TCGplayer commonly appends collector numbers such as
    # "- 107a/122" or "- SWSH296". Number matching already establishes
    # identity, so remove that decoration before name disambiguation.
    s=re.sub(r"\s*-\s*[A-Za-z0-9?!._-]+(?:/[A-Za-z0-9?!._-]+)?\s*$","",s)
    return norm(s)

def first_edition(v):
    stamps=" ".join(str(x).lower() for x in (v.get("stamps") or []))
    return "1st" in stamps or "first" in stamps or "auflage" in stamps or re.search(r"(^|\s)1\.",stamps)

def subtype_matches(subtype,legacy,v):
    s=str(subtype or "").lower()
    if first_edition(v):
        if "1st edition" not in s: return False
    elif "1st edition" in s:
        return False
    legacy=legacy.upper()
    if legacy=="REVERSE": return "reverse" in s
    if legacy=="HOLO": return "holo" in s and "reverse" not in s
    if legacy=="NORMAL": return "holo" not in s and "reverse" not in s
    if legacy=="FIRST_EDITION": return "1st edition" in s
    return False



def product_printing_matches(name, legacy):
    text=str(name or "").lower()
    legacy=legacy.upper()
    if "reverse holofoil" in text or "reverse holo" in text:
        kind="REVERSE"
    elif "non-holo" in text or "non holo" in text:
        kind="NORMAL"
    elif "holofoil" in text or re.search(r"\(holo\)", text):
        kind="HOLO"
    else:
        return False
    return kind == legacy

def set_key(name):
    value=str(name or "").lower()
    value=re.sub(r"^(ex|sm|xy)\s*[-:]\s*","",value)
    value=re.sub(r"^swsh\d*\s*[:\-]\s*","",value)
    value=re.sub(r"^sv\d*(?:\.\d+)?\s*[:\-]\s*","",value)
    value=re.sub(r"^me\d*\s*[:\-]\s*","",value)
    value=value.replace("base set","")
    return norm(value)

rows=db("""
SELECT p.card_id,c.set_id,c.local_id,c.name,
       COALESCE(e.name,c.name) AS en_name,
       COALESCE(es.name,ds.name,'') AS en_set_name,
       p.variant_id,p.legacy_variant,c.variants::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c
  ON c.card_id=p.card_id AND c.language_code=p.language_code
LEFT JOIN catalog_cards_mirror e
  ON e.language_code='en' AND e.set_id=c.set_id AND e.local_id=c.local_id
LEFT JOIN catalog_sets_mirror es
  ON es.language_code='en' AND es.set_id=c.set_id
LEFT JOIN catalog_sets_mirror ds
  ON ds.language_code='en' AND ds.set_id=c.set_id
WHERE p.language_code='en'
  AND p.resolution_status='NO_PRICE'
  AND NOT (c.set_id ~ '^(A[0-9]|B[0-9])' OR c.set_id='P-A')
ORDER BY c.set_id,c.card_id,p.variant_id
""").splitlines()

targets=[]
for line in rows:
    parts=line.split("\t",8)
    if len(parts)!=9: continue
    cid,sid,local_id,de_name,en_name,set_name,vid,legacy,variants_json=parts
    variants=json.loads(variants_json or "[]")
    vm=next((v for v in variants if str(v.get("id") or "")==vid),None)
    if vm is None: continue
    targets.append({
        "card_id":cid,"set_id":sid,"local_id":local_id,"en_name":en_name,
        "set_name":set_name,"variant_id":vid,"legacy":legacy,"variant":vm,
    })
print("target_variant_rows",len(targets),flush=True)

groups=requests.get("https://tcgcsv.com/tcgplayer/3/groups",headers=UA,timeout=30).json().get("results") or []
by_key={}
for g in groups:
    by_key.setdefault(set_key(g.get("name")),[]).append(g)

# Ambiguous/non-literal catalogue names.
ALIASES={
    "basep":1418, "dpp":1421, "mep":24451, "svp":22872,
    "swshp":2545, "smp":1861, "xyp":1451, "bwp":1407, "hsp":1453,
    "sma":2594,
    "dp1":1430,
    "ex1":1393,
    "ex3":1376,
    "ex7":1428,
    "np":1423, "xya": 1938,
    "bog":1455,
    "miscp":2374,
    "tk-hs-g":1540,
    "tk-xy-latio":1536,
    "tk-xy-w":1533,
    "tk-xy-n":1532,
    "tk-xy-su":1796,
}

set_to_gid={}
unmapped_sets={}
for t in targets:
    sid=t["set_id"]
    if sid in set_to_gid or sid in unmapped_sets: continue
    if sid in ALIASES:
        set_to_gid[sid]=ALIASES[sid]; continue
    key=set_key(t["set_name"])
    candidates=by_key.get(key,[])
    if len(candidates)==1:
        set_to_gid[sid]=int(candidates[0]["groupId"])
    else:
        # Secondary exact containment after stripping era prefixes.
        matches=[g for g in groups if key and (key in set_key(g.get("name")) or set_key(g.get("name")) in key)]
        # Avoid dangerously broad matches.
        unique={int(g["groupId"]):g for g in matches if len(set_key(g.get("name")))>=4}
        if len(unique)==1:
            set_to_gid[sid]=next(iter(unique))
        else:
            unmapped_sets[sid]=(t["set_name"],[(g["groupId"],g["name"]) for g in list(unique.values())[:5]])

print("mapped_sets",len(set_to_gid),"unmapped_sets",len(unmapped_sets),flush=True)
for sid,info in sorted(unmapped_sets.items()):
    print("unmapped_set",sid,info,flush=True)

by_group={}
for t in targets:
    gid=set_to_gid.get(t["set_id"])
    if gid: by_group.setdefault(gid,[]).append(t)

resolved=[]
for idx,(gid,items) in enumerate(sorted(by_group.items()),1):
    pu=f"https://tcgcsv.com/tcgplayer/3/{gid}/products"
    ru=f"https://tcgcsv.com/tcgplayer/3/{gid}/prices"
    pr=requests.get(pu,headers=UA,timeout=30)
    rr=requests.get(ru,headers=UA,timeout=30)
    if pr.status_code!=200 or rr.status_code!=200:
        print("group_http",gid,pr.status_code,rr.status_code,flush=True)
        continue
    products=pr.json().get("results") or []
    prices=rr.json().get("results") or []
    price_by={}
    for x in prices:
        price_by.setdefault(int(x.get("productId") or 0),[]).append(x)
    by_num={}; by_tail={}
    for p in products:
        n=product_num(p)
        if not n: continue
        by_num.setdefault(n,[]).append(p)
        tail=numeric_tail(n)
        if tail: by_tail.setdefault(tail,[]).append(p)

    for t in items:
        key=card_num(t["local_id"])
        candidates=by_num.get(key,[])
        if not candidates and key.isdigit():
            candidates=by_tail.get(key,[])
        if not candidates:
            alt=re.fullmatch(r"([0-9]+)[a-z]+",key)
            if alt:
                base=str(int(alt.group(1)))
                candidates=[p for p in by_tail.get(base,[]) if name_key(p.get("name"))==name_key(t["en_name"])]
        if len(candidates)>1:
            exact=[p for p in candidates if name_key(p.get("name"))==name_key(t["en_name"])]
            candidates=exact
        if len(candidates)>1:
            printing=[
                p for p in candidates
                if product_printing_matches(p.get("name"), t["legacy"])
            ]
            if len(printing)==1:
                candidates=printing
        if len(candidates)>1:
            non_staff=[
                p for p in candidates
                if "[staff]" not in str(p.get("name") or "").lower()
            ]
            if len(non_staff)==1:
                candidates=non_staff
        if len(candidates)!=1:
            continue
        product=candidates[0]
        pprices=price_by.get(int(product["productId"]),[])
        v=t["variant"]; legacy=t["legacy"]
        matches=[x for x in pprices if subtype_matches(x.get("subTypeName"),legacy,v)]
        if len(matches)!=1:
            edition_rows=[]
            for x in pprices:
                st=str(x.get("subTypeName") or "").lower()
                if first_edition(v):
                    if "1st edition" in st: edition_rows.append(x)
                elif "1st edition" not in st:
                    edition_rows.append(x)
            if len(edition_rows)==1:
                matches=edition_rows
            elif legacy.upper()=="NORMAL":
                non_rev=[x for x in edition_rows if "reverse" not in str(x.get("subTypeName") or "").lower()]
                if len(non_rev)==1: matches=non_rev
        if len(matches)!=1:
            continue
        px=matches[0]
        usd=px.get("marketPrice")
        if not isinstance(usd,(int,float)) or not math.isfinite(usd) or usd<=0:
            usd=px.get("midPrice")
        if not isinstance(usd,(int,float)) or not math.isfinite(usd) or usd<=0:
            continue
        eur=round((float(usd)*USD_TO_EUR)/0.90,4)
        resolved.append((
            t["card_id"],t["variant_id"],t["legacy"],eur,
            int(product["productId"]),str(px.get("subTypeName") or "")
        ))
    print(f"group={idx}/{len(by_group)} gid={gid} rows={len(items)} resolved={len(resolved)}",flush=True)
    time.sleep(0.12)

unique={(r[0],r[1]):r for r in resolved}
resolved=list(unique.values())
sql=["BEGIN;"]
for cid,vid,legacy,eur,pid,subtype in resolved:
    detail=q(f"TCGplayer product {pid}; {subtype}")
    sql.append(f"""UPDATE tcg_price_cache SET
source='TCGCSV_TCGPLAYER',base_eur={eur},updated_at=NOW(),resolution_status='PRICE_FOUND',
failure_detail='{detail}',next_attempt_at=NOW()+INTERVAL '7 days'
WHERE card_id='{q(cid)}' AND language_code='en' AND variant_id='{q(vid)}';""")
    sql.append(f"""INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES ('{q(cid)}','en','{q(vid)}','TCGCSV_TCGPLAYER',{eur},NOW());""")
sql.append("COMMIT;")
if resolved:
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
        input="\n".join(sql),text=True,check=True,stdout=subprocess.DEVNULL
    )
print("applied_variant_rows",len(resolved),flush=True)
