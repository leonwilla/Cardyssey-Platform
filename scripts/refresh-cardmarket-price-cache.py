#!/usr/bin/env python3
"""Backfill and refresh verified Cardmarket prices from Cardmarket's public Pokémon JSON files.

Identity resolution is fail-closed:
1) prefer a Cardmarket product id exposed by TCGdex for the exact card;
2) otherwise use a high-confidence Cardmarket expansion mapping plus exact English card name.

Special physical variants are only resolved when the Cardmarket identity cannot
collapse multiple distinct holo-like variants into one bucket.
"""
import argparse
import collections
import concurrent.futures
import json
from pathlib import Path
import math
import re
import subprocess
import requests
from price_identity_validation import print_reasons,candidate_status

UA = {"User-Agent": "Cardyssey/0.4 cardmarket-price-refresh"}
PRICE_URL = "https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"
PRODUCT_URL = "https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json"

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def q(value):
    return str(value).replace("'","''")

def positive(value):
    return isinstance(value,(int,float)) and math.isfinite(value) and value > 0

def norm(value):
    s=str(value or "").lower().replace("’","'")
    for a,b in (("é","e"),("è","e"),("á","a"),("ö","o"),("ü","u"),("ä","a")):
        s=s.replace(a,b)
    s=re.sub(r"\[[^\]]*\]","",s)
    s=re.sub(r"\s*\([^)]*\)\s*$","",s)
    return re.sub(r"[^a-z0-9]+","",s)

def semantic_name(value):
    s=str(value or "").lower().replace("’","'")
    # Cardmarket spells legacy rarity/Delta markers out while TCGdex often
    # uses the printed symbols. Normalize both representations.
    s=s.replace("☆"," gold star ").replace("★"," gold star ")
    s=re.sub(r"δ\s*delta\s*species", " delta species ", s)
    s=s.replace("δ"," delta species ")
    s=re.sub(r"gold\s+star", "goldstar", s)
    s=re.sub(r"delta\s+species", "deltaspecies", s)
    s=re.sub(r"\[[^\]]*\]","",s)
    s=re.sub(r"\s*\([^)]*\)\s*$","",s)
    return re.sub(r"[^a-z0-9]+","",s)

def norm_full(value):
    s=str(value or "").lower().replace("’","'")
    for a,b in (("é","e"),("è","e"),("á","a"),("ö","o"),("ü","u"),("ä","a")):
        s=s.replace(a,b)
    return re.sub(r"[^a-z0-9]+","",s)

def variant_is_holo(legacy, variant):
    typ=str(variant.get("type") or "").lower()
    return (
        str(legacy).upper() in ("HOLO","REVERSE")
        or typ in ("holo","reverse")
        or bool(variant.get("foil"))
    )

def variant_is_special(variant):
    return bool(variant.get("foil") or variant.get("stamps") or variant.get("subtype"))

def holo_variant_count(variants):
    count=0
    for v in variants:
        if variant_is_holo(v.get("legacyVariant"),v):
            count+=1
    return count

def price_from_guide(guide, legacy, variant):
    if variant_is_holo(legacy,variant):
        keys=("trend-holo","avg7-holo","avg30-holo","avg-holo","low-holo")
    else:
        keys=("trend","avg7","avg30","avg","low")
    for key in keys:
        value=guide.get(key)
        if positive(value):
            return float(value),key
    return None,None

def explicit_special_product(name, variant):
    text=str(name or "").lower()
    foil=str(variant.get("foil") or "").lower().replace("_","-")
    stamps=" ".join(str(x).lower() for x in (variant.get("stamps") or []))
    subtype=str(variant.get("subtype") or "").lower()
    if foil in ("cosmos","kosmos"):
        return "cosmos" in text or "cosmo holo" in text
    if foil in ("cracked-ice","cracked ice"):
        return "cracked ice" in text
    if foil=="league":
        return "league" in text
    if "staff" in stamps:
        return "staff" in text
    if subtype and subtype in text:
        return True
    return not variant_is_special(variant)

parser=argparse.ArgumentParser()
parser.add_argument("--dry-run",action="store_true")
parser.add_argument("--fallback-report",type=Path,help="JSON audit of unresolved identity candidates, no guessed prices")
args=parser.parse_args()

print("cardmarket_download=products_start",flush=True)
products_payload=requests.get(PRODUCT_URL,headers=UA,timeout=45)
products_payload.raise_for_status()
print(f"cardmarket_download=products_done bytes={len(products_payload.content)}",flush=True)
print("cardmarket_download=prices_start",flush=True)
price_payload=requests.get(PRICE_URL,headers=UA,timeout=45)
price_payload.raise_for_status()
print(f"cardmarket_download=prices_done bytes={len(price_payload.content)}",flush=True)
products=products_payload.json().get("products") or []
price_rows=price_payload.json().get("priceGuides") or []
prices={str(x.get("idProduct")):x for x in price_rows}

by_exp=collections.defaultdict(list)
by_name=collections.defaultdict(list)
by_semantic_name=collections.defaultdict(list)
for product in products:
    by_exp[product.get("idExpansion")].append(product)
    key=norm(product.get("name"))
    if key:
        by_name[key].append(product)
    semantic_key=semantic_name(product.get("name"))
    if semantic_key:
        by_semantic_name[semantic_key].append(product)

# Build a high-confidence Cardyssey set -> Cardmarket idExpansion map from full EN set-name overlap.
set_cards=collections.defaultdict(list)
for line in db("SELECT set_id,name FROM catalog_cards_mirror WHERE language_code='en';").splitlines():
    if "\t" not in line:
        continue
    sid,name=line.split("\t",1)
    key=semantic_name(name)
    if key:
        set_cards[sid].append(key)

exp_names={
    eid:collections.Counter(
        semantic_name(p.get("name"))
        for p in plist
        if semantic_name(p.get("name"))
    )
    for eid,plist in by_exp.items()
}
set_map={}
for sid,names in set_cards.items():
    wanted=collections.Counter(names)
    scores=[]
    for eid,available in exp_names.items():
        overlap=sum(min(count,available.get(name,0)) for name,count in wanted.items())
        if overlap:
            scores.append((overlap,overlap/max(1,len(names)),eid))
    scores.sort(reverse=True)
    if not scores:
        continue
    top=scores[0]
    second=scores[1] if len(scores)>1 else (0,0,None)
    if top[1] >= 0.90 and (top[0]-second[0] >= 3 or top[1] >= 0.98):
        set_map[sid]=top[2]

rows=[]
query="""
SELECT p.card_id,p.language_code,c.set_id,c.local_id,
       COALESCE(e.name,c.name) AS en_name,
       p.variant_id,p.legacy_variant,c.variants::text,
       p.source,p.failure_detail
FROM tcg_price_cache p
JOIN catalog_cards_mirror c
  ON c.card_id=p.card_id AND c.language_code=p.language_code
LEFT JOIN catalog_cards_mirror e
  ON e.language_code='en' AND e.set_id=c.set_id AND e.local_id=c.local_id
WHERE p.language_code IN ('de','en')
  AND (p.resolution_status='NO_PRICE' OR p.source='CARDMARKET_OFFICIAL')
ORDER BY p.language_code,p.card_id,p.variant_id
"""
for line in db(query).splitlines():
    parts=line.split("\t",9)
    if len(parts)!=10:
        continue
    cid,lang,sid,local_id,en_name,vid,legacy,variants_json,source,failure=parts
    variants=json.loads(variants_json or "[]")
    selected=next((v for v in variants if str(v.get("id") or "")==vid),None)
    if selected is None:
        continue
    rows.append({
        "card_id":cid,"language":lang,"set_id":sid,"local_id":local_id,
        "en_name":en_name,"variant_id":vid,"legacy":legacy,"variant":selected,
        "variants":variants,"source":source,"failure":failure,
    })

# Refresh already verified Cardmarket rows from stored product id without re-resolving identity.
updates=[]
pending=[]
pattern=re.compile(r"Cardmarket product (\d+); key ([A-Za-z0-9_-]+)")
for row in rows:
    if row["source"]=="CARDMARKET_OFFICIAL":
        match=pattern.search(row["failure"] or "")
        if match:
            product_id=match.group(1)
            guide=prices.get(product_id)
            if guide:
                value,key=price_from_guide(guide,row["legacy"],row["variant"])
                if value is not None:
                    updates.append((row,product_id,value,key,"refresh"))
                    continue
    pending.append(row)

# Fetch TCGdex details only for unresolved rows; this is identity metadata, not the price source.
card_keys=sorted({(r["card_id"],r["language"]) for r in pending})
def fetch_card(key):
    cid,lang=key
    try:
        response=requests.get(
            f"https://api.tcgdex.net/v2/{lang}/cards/{cid}",
            headers=UA,timeout=20
        )
        return key,(response.json() if response.status_code==200 else None)
    except requests.RequestException:
        return key,None

cards={}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    for index,(key,payload) in enumerate(pool.map(fetch_card,card_keys),1):
        cards[key]=payload
        if index%250==0 or index==len(card_keys):
            print(f"cardmarket_identity={index}/{len(card_keys)}",flush=True)

resolved_keys={(u[0]["card_id"],u[0]["language"],u[0]["variant_id"]) for u in updates}
for row in pending:
    identity=(row["card_id"],row["language"],row["variant_id"])
    if identity in resolved_keys:
        continue

    guide=None
    product_id=None
    product_name=None
    method=None
    card=cards.get((row["card_id"],row["language"]))

    # Preferred: exact Cardmarket product bucket supplied by TCGdex card details.
    if card:
        top_cm=((card.get("pricing") or {}).get("cardmarket") or {})
        top_id=top_cm.get("idProduct")
        if top_id is not None and str(top_id) in prices:
            # Special variants can use a shared Cardmarket foil bucket only if there is
            # exactly one holo-like physical variant on this card.
            if not variant_is_special(row["variant"]) or holo_variant_count(row["variants"])==1:
                product_id=str(top_id)
                guide=prices[product_id]
                method="tcgdex-cardmarket-id"

    # Fallback: high-confidence set mapping + exact EN card name.
    # This name-based path is intentionally limited to Western languages.
    # Asian cards use only TCGdex's exact Cardmarket product identity.
    if guide is None and row["language"] in ("de","en") and row["set_id"] in set_map:
        eid=set_map[row["set_id"]]
        candidates=[
            p for p in by_exp[eid]
            if (
                norm(p.get("name"))==norm(row["en_name"])
                or semantic_name(p.get("name"))==semantic_name(row["en_name"])
            )
        ]
        if len(candidates)>1 and card:
            attacks=[
                str(a.get("name") or "")
                for a in (card.get("attacks") or [])
                if str(a.get("name") or "").strip()
            ]
            if attacks:
                attack_matches=[
                    p for p in candidates
                    if all(norm_full(attack) in norm_full(p.get("name")) for attack in attacks)
                ]
                if len(attack_matches)==1:
                    candidates=attack_matches
        if len(candidates)==1:
            candidate=candidates[0]
            if (
                not variant_is_special(row["variant"])
                or explicit_special_product(candidate.get("name"),row["variant"])
            ):
                candidate_id=str(candidate.get("idProduct"))
                if candidate_id in prices:
                    product_id=candidate_id
                    product_name=candidate.get("name")
                    guide=prices[candidate_id]
                    method="set-name"

    if guide is None:
        continue
    value,key=price_from_guide(guide,row["legacy"],row["variant"])
    if value is None:
        continue
    updates.append((row,product_id,value,key,method))

# Second-stage fallback: use the real card name and set context to expose
# otherwise overlooked provider candidates. This is a diagnostic route, not
# automatic authority to assign a price across languages or printings.
found_keys={(u[0]["card_id"],u[0]["language"],u[0]["variant_id"]) for u in updates}
fallback=[]
for row in rows:
    identity=(row["card_id"],row["language"],row["variant_id"])
    if identity in found_keys:
        continue
    label=row["en_name"]
    matching=[p for p in by_name.get(norm(label),[]) if str(p.get("idProduct")) in prices]
    # Also support semantic star/delta naming, only if the normalized name
    # yields no matches. Avoid a full catalogue scan on every card.
    if not matching:
        matching=[p for p in by_semantic_name.get(semantic_name(label),[])
                  if str(p.get("idProduct")) in prices]
    matched_set=set_map.get(row["set_id"])
    same_set=[p for p in matching if p.get("idExpansion")==matched_set] if matched_set is not None else []
    candidates=same_set if same_set else matching
    # The public product list does not establish a language-filtered or
    # first-edition-filtered price. Never mark a candidate as import-ready.
    reasons=print_reasons(row["variant"],candidates[0].get("name") if len(candidates)==1 else "",
                          set_verified=bool(same_set),number_verified=False,
                          language_verified=False,edition_verified=False)
    fallback.append(dict(language=row["language"],card_id=row["card_id"],
                         set_code=row["set_id"],number=row["local_id"],
                         english_name=label,variant_id=row["variant_id"],
                         variant=row["variant"],total_candidates=len(candidates),
                         set_verified=bool(same_set),
                         status=candidate_status(len(candidates),reasons),
                         unverified_identity_fields=reasons,
                         products=[dict(id=x.get("idProduct"),name=x.get("name"),
                                        expansion=x.get("idExpansion")) for x in candidates[:8]]))
if args.fallback_report:
    args.fallback_report.parent.mkdir(parents=True,exist_ok=True)
    args.fallback_report.write_text(json.dumps({
        "source":"Cardmarket public product catalogue",
        "scope":"Unresolved after quick product-ID and safe set/name lookups",
        "warning":"Candidates are NOT verified language/edition/size/stamp prices",
        "unresolved":fallback},ensure_ascii=False,indent=2)+"\n")
print(f"cardmarket_fallback_unresolved={len(fallback)} review_candidates={sum(bool(x['products']) for x in fallback)}",flush=True)

# Deduplicate by cache primary key, preferring exact Cardmarket-id resolution.
best={}
rank={"refresh":3,"tcgdex-cardmarket-id":2,"set-name":1}
for update in updates:
    row=update[0]
    key=(row["card_id"],row["language"],row["variant_id"])
    if key not in best or rank.get(update[4],0)>rank.get(best[key][4],0):
        best[key]=update
updates=list(best.values())

print(
    f"cardmarket_created_at={price_payload.json().get('createdAt')} "
    f"catalog_products={len(products)} set_map={len(set_map)} "
    f"eligible_rows={len(rows)} updates={len(updates)} dry_run={args.dry_run}",
    flush=True
)

for row,product_id,value,price_key,method in updates:
    print(
        f"{row['language']} {row['card_id']} {row['variant_id']} "
        f"{value:.4f} EUR product={product_id} key={price_key} via={method}",
        flush=True
    )

if not args.dry_run and updates:
    sql=["BEGIN;"]
    for row,product_id,value,price_key,method in updates:
        detail=f"Cardmarket product {product_id}; key {price_key}; via {method}"
        sql.append(f"""
UPDATE tcg_price_cache
SET source='CARDMARKET_OFFICIAL',
    base_eur={value:.4f},
    updated_at=NOW(),
    resolution_status='PRICE_FOUND',
    failure_detail='{q(detail)}',
    next_attempt_at=NOW()+INTERVAL '7 days'
WHERE card_id='{q(row["card_id"])}'
  AND language_code='{q(row["language"])}'
  AND variant_id='{q(row["variant_id"])}';
""")
        sql.append(f"""
INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES (
  '{q(row["card_id"])}','{q(row["language"])}','{q(row["variant_id"])}',
  'CARDMARKET_OFFICIAL',{value:.4f},NOW()
);
""")
    sql.append("COMMIT;")
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
        input="\n".join(sql),text=True,check=True,stdout=subprocess.DEVNULL
    )
    print(f"applied={len(updates)}",flush=True)
