#!/usr/bin/env python3
"""Backfill remaining German physical prices from TCGCSV/TCGplayer.

TCGCSV republishes TCGplayer's daily group products + market prices. Matching is
fail-closed: exact set mapping, exact local card number, unique product (or exact
English card-name disambiguation), and exact printing family/edition subtype.
"""
import json, math, re, subprocess, time, requests

USD_TO_EUR=0.88739
UA={"User-Agent":"Cardyssey/0.2 price-backfill"}

GROUPS={
"base2":635,"basep":1418,
"bw10":1370,"bw4":1412,"bw5":1386,"bw6":1394,"bw7":1408,"bw8":1413,"bw9":1382,
"dp1":1430,"dp2":1368,"dp3":1380,"dp4":1405,"dp5":1390,"dp6":1417,"dp7":1369,"dpp":1421,
"ex12":1378,"ex13":1379,"ex15":1411,"ex8":1404,"exu":1398,
"g1":1728,"mep":24451,
"sm10":2420,"sm11":2464,"sm115":2480,"sm12":2534,"sm4":2071,"sm5":2178,
"sm6":2209,"sm7":2278,"sm7.5":2295,"sm8":2328,"sm9":2377,"sma":2594,
"svp":22872,"swsh1":2585,"swsh3.5":2685,
"xy1":1387,"xy10":1780,"xy11":1815,"xy12":1842,"xy2":1464,"xy3":1481,
"xy4":1494,"xy5":1509,"xy6":1534,"xy8":1661,"xy9":1701,
}

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def q(s): return s.replace("'","''")

def norm(s): return re.sub(r"[^a-z0-9]+","",str(s or "").lower())

def card_num(s):
    import urllib.parse
    s=urllib.parse.unquote(str(s or "")).strip().split("/")[0].strip()
    if s in ("?","!"):
        return s
    n=norm(s)
    if n.isdigit():
        return n.lstrip("0") or "0"
    m=re.fullmatch(r"([a-z]+)0*([0-9]+)",n)
    if m:
        return f"{m.group(1)}{int(m.group(2))}"
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
    # TCGplayer often appends the card number in parentheses; number matching
    # already handles identity, so remove only that trailing decoration.
    s=re.sub(r"\s*\([^)]*\)\s*$","",str(s or ""))
    return norm(s)

def first_edition(variant):
    stamps=" ".join(str(x).lower() for x in (variant.get("stamps") or []))
    return "1." in stamps or "1st" in stamps or "first" in stamps or "auflage" in stamps

def subtype_matches(subtype, legacy, variant):
    s=str(subtype or "").lower()
    legacy=legacy.upper()
    if first_edition(variant):
        if "1st edition" not in s:
            return False
    else:
        if "1st edition" in s:
            return False

    if legacy=="REVERSE":
        return "reverse" in s
    if legacy=="HOLO":
        return "holo" in s and "reverse" not in s
    if legacy=="NORMAL":
        return "holo" not in s and "reverse" not in s
    if legacy=="FIRST_EDITION":
        return "1st edition" in s
    return False

rows=db("""
WITH target AS (
 SELECT c.card_id,c.set_id,c.local_id,c.name,c.variants,
        e.name AS en_name
 FROM catalog_cards_mirror c
 JOIN catalog_cards_mirror e
   ON e.language_code='en'
  AND e.set_id=c.set_id
  AND e.local_id=c.local_id
 WHERE c.language_code='de'
   AND NOT (c.set_id ~ '^(A[0-9]|B[0-9])' OR c.set_id='P-A')
   AND NOT EXISTS (
     SELECT 1 FROM tcg_price_cache p
     WHERE p.language_code='de'
       AND p.card_id=c.card_id
       AND p.resolution_status='PRICE_FOUND'
   )
)
SELECT card_id,set_id,local_id,name,en_name,variants::text
FROM target ORDER BY set_id,card_id
""").splitlines()

targets=[]
for line in rows:
    parts=line.split("\t",5)
    if len(parts)!=6: continue
    cid,sid,local_id,de_name,en_name,variants_json=parts
    if sid not in GROUPS: continue
    targets.append((cid,sid,local_id,de_name,en_name,json.loads(variants_json or "[]")))

print("target_cards",len(targets),flush=True)

by_group={}
for t in targets:
    by_group.setdefault(GROUPS[t[1]],[]).append(t)

resolved=[]
unmatched=[]
for idx,(gid,cards) in enumerate(sorted(by_group.items()),1):
    products_url=f"https://tcgcsv.com/tcgplayer/3/{gid}/products"
    prices_url=f"https://tcgcsv.com/tcgplayer/3/{gid}/prices"
    pr=requests.get(products_url,headers=UA,timeout=30)
    rr=requests.get(prices_url,headers=UA,timeout=30)
    if pr.status_code!=200 or rr.status_code!=200:
        print("group_http",gid,pr.status_code,rr.status_code,flush=True)
        unmatched.extend((c[0],"group_http") for c in cards)
        continue

    products=pr.json().get("results") or []
    prices=rr.json().get("results") or []
    price_by_product={}
    for x in prices:
        price_by_product.setdefault(int(x.get("productId") or 0),[]).append(x)

    by_number={}
    by_tail={}
    for p in products:
        n=product_num(p)
        if n:
            by_number.setdefault(n,[]).append(p)
            tail=numeric_tail(n)
            if tail:
                by_tail.setdefault(tail,[]).append(p)

    for cid,sid,local_id,de_name,en_name,variants in cards:
        local_key=card_num(local_id)
        candidates=by_number.get(local_key,[])
        if not candidates and local_key.isdigit():
            candidates=by_tail.get(local_key,[])

        # A few official localized alternates use a suffix such as 28a/55a,
        # while TCGplayer keeps the underlying printed number. Only accept the
        # base-number fallback when the exact English card name is unique.
        if not candidates:
            alt=re.fullmatch(r"([0-9]+)[a-z]+",local_key)
            if alt:
                base=str(int(alt.group(1)))
                candidates=[
                    p for p in by_tail.get(base,[])
                    if name_key(p.get("name"))==name_key(en_name)
                ]

        if len(candidates)>1:
            exact=[p for p in candidates if name_key(p.get("name"))==name_key(en_name)]
            candidates=exact
        if len(candidates)!=1:
            unmatched.append((cid,f"product_match:{len(candidates)}"))
            continue
        product=candidates[0]
        pprices=price_by_product.get(int(product["productId"]),[])
        for v in variants:
            vid=str(v.get("id") or "")
            legacy=str(v.get("legacyVariant") or "").upper()
            if not vid or not legacy: continue
            matches=[x for x in pprices if subtype_matches(x.get("subTypeName"),legacy,v)]
            if len(matches)!=1:
                # Some TCGdex historical rows label a single physical printing
                # as NORMAL even though TCGplayer calls that sole printing
                # Holofoil. If the edition filter leaves exactly one market
                # subtype, it is unambiguous and safe to use.
                edition_rows=[]
                for x in pprices:
                    subtype=str(x.get("subTypeName") or "").lower()
                    if first_edition(v):
                        if "1st edition" in subtype:
                            edition_rows.append(x)
                    elif "1st edition" not in subtype:
                        edition_rows.append(x)
                if len(edition_rows)==1:
                    matches=edition_rows
                elif legacy=="NORMAL":
                    non_reverse=[
                        x for x in edition_rows
                        if "reverse" not in str(x.get("subTypeName") or "").lower()
                    ]
                    # Some historical TCGplayer products call the ordinary
                    # non-reverse bucket "Holofoil" even when TCGdex labels the
                    # catalog variant NORMAL. If it is the sole non-reverse
                    # market bucket, identity remains unambiguous.
                    if len(non_reverse)==1:
                        matches=non_reverse
            if len(matches)!=1:
                continue
            px=matches[0]
            usd=px.get("marketPrice")
            if not isinstance(usd,(int,float)) or not math.isfinite(usd) or usd<=0:
                usd=px.get("midPrice")
            if not isinstance(usd,(int,float)) or not math.isfinite(usd) or usd<=0:
                continue
            # TCGplayer market values are closest to an NM market baseline.
            base_eur=(float(usd)*USD_TO_EUR)/0.90
            if math.isfinite(base_eur) and base_eur>0:
                resolved.append((cid,vid,legacy,round(base_eur,4),int(product["productId"]),str(px.get("subTypeName") or "")))

    print(f"group={idx}/{len(by_group)} gid={gid} cards={len(cards)} resolved={len(resolved)}",flush=True)
    time.sleep(0.15)

# Deduplicate exact cache keys before SQL.
unique={}
for row in resolved:
    unique[(row[0],row[1])]=row
resolved=list(unique.values())

sql=["BEGIN;"]
for cid,vid,legacy,eur,product_id,subtype in resolved:
    detail=q(f"TCGplayer product {product_id}; {subtype}")
    sql.append(f"""INSERT INTO tcg_price_cache
(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
VALUES ('{q(cid)}','de','{q(vid)}','{q(legacy)}','TCGCSV_TCGPLAYER',{eur},NOW(),'PRICE_FOUND','{detail}',NOW()+INTERVAL '7 days')
ON CONFLICT (card_id,language_code,variant_id) DO UPDATE SET
legacy_variant=EXCLUDED.legacy_variant,source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail=EXCLUDED.failure_detail,
next_attempt_at=EXCLUDED.next_attempt_at;""")
    sql.append(f"""INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES ('{q(cid)}','de','{q(vid)}','TCGCSV_TCGPLAYER',{eur},NOW());""")
sql.append("COMMIT;")
if resolved:
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
        input="\n".join(sql),text=True,check=True,stdout=subprocess.DEVNULL
    )

print("applied_variants",len(resolved),flush=True)
print("unmatched_cards",len(unmatched),flush=True)
for x in unmatched[:50]:
    print("unmatched",x[0],x[1],flush=True)
