#!/usr/bin/env python3
"""Seed remaining exact DE price cases from verified market identities.

Sources:
- TCGCSV/TCGplayer exact product/subtype ids for legacy/special products.
- Cardmarket trend for SVP 105-113 where the exact official promo number is
  verified but TCGCSV currently lacks those product rows.
"""
import json, math, subprocess

USD_TO_EUR=0.88739

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def q(s): return str(s).replace("'","''")

def put_price(cid, vid, legacy, source, eur, detail):
    db(f"""INSERT INTO tcg_price_cache
(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
VALUES ('{q(cid)}','de','{q(vid)}','{q(legacy)}','{q(source)}',{eur},NOW(),'PRICE_FOUND','{q(detail)}',NOW()+INTERVAL '7 days')
ON CONFLICT (card_id,language_code,variant_id) DO UPDATE SET
legacy_variant=EXCLUDED.legacy_variant,source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail=EXCLUDED.failure_detail,
next_attempt_at=EXCLUDED.next_attempt_at;""")
    db(f"""INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES ('{q(cid)}','de','{q(vid)}','{q(source)}',{eur},NOW());""")

# Exact TCGplayer market product identities. USD market is treated as an NM
# baseline, consistent with the existing Cardyssey TCGplayer fallback.
tcgplayer = {
    "basep-2":  (12.39, 85107, "Normal"),
    "basep-3":  (39.49, 87414, "Normal"),
    "basep-5":  (59.76, 84909, "Normal"),
    "g1-RC31":  (107.33, 113773, "Holofoil"),
    "mep-101":  (2.13, 713260, "Holofoil"),
}

for cid,(usd,pid,subtype) in tcgplayer.items():
    rows=db(f"""SELECT COALESCE(v.value->>'id',''),COALESCE(v.value->>'legacyVariant','NORMAL')
                FROM catalog_cards_mirror c
                CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
                WHERE c.language_code='de' AND c.card_id='{q(cid)}'
                ORDER BY v.value->>'id';""").splitlines()
    for row in rows:
        vid,legacy=row.split("\t",1)
        eur=round((usd*USD_TO_EUR)/0.90,4)
        put_price(cid,vid,legacy,"TCGCSV_TCGPLAYER",eur,f"TCGplayer product {pid}; {subtype}")

# Unown (?) has no catalog variant metadata in the imported historical row.
# TCGplayer identifies the physical printing uniquely as Holofoil.
cid="exu-%3F"
variant_id="legacy:holo"
variants=[{
    "id":variant_id,
    "type":"Holo",
    "subtype":None,
    "foil":None,
    "size":"Standard",
    "stamps":[],
    "legacyVariant":"HOLO",
    "tcgDexEur":None,
}]
db(f"""UPDATE catalog_cards_mirror
SET variants='{q(json.dumps(variants,separators=(",",":")))}'::jsonb,
    details_complete=TRUE,
    source_updated_at=NOW()
WHERE language_code='de' AND card_id='{cid}';""")
eur=round((139.99*USD_TO_EUR)/0.90,4)
put_price(cid,variant_id,"HOLO","TCGCSV_TCGPLAYER",eur,"TCGplayer product 90167; Holofoil")

# Paradise Resort SVP224: TCGplayer exposes exact Worlds 2025 and Staff products.
rows=db("""SELECT v.value->>'id',
                 COALESCE(v.value->>'legacyVariant','NORMAL'),
                 COALESCE(v.value->'stamps','[]'::jsonb)::text
          FROM catalog_cards_mirror c
          CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
          WHERE c.language_code='de' AND c.card_id='svp-224';""").splitlines()
for row in rows:
    vid,legacy,stamps_json=row.split("\t",2)
    stamps=[str(x).lower() for x in json.loads(stamps_json)]
    if "mitarbeiter" in stamps:
        usd,pid=369.52,649234
    elif stamps==["worlds-2025"]:
        usd,pid=295.61,649232
    else:
        continue
    eur=round((usd*USD_TO_EUR)/0.90,4)
    put_price("svp-224",vid,legacy,"TCGCSV_TCGPLAYER",eur,f"TCGplayer product {pid}; Normal")

# Exact Cardmarket promo pages, current trend values in EUR.
svp_trend={
    "svp-105":5.28,
    "svp-106":9.94,
    "svp-107":0.70,
    "svp-108":0.99,
    "svp-109":2.51,
    "svp-110":8.97,
    "svp-111":0.40,
    "svp-112":0.77,
    "svp-113":1.71,
}
for cid,eur in svp_trend.items():
    rows=db(f"""SELECT v.value->>'id',COALESCE(v.value->>'legacyVariant','NORMAL')
                FROM catalog_cards_mirror c
                CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
                WHERE c.language_code='de' AND c.card_id='{cid}';""").splitlines()
    for row in rows:
        vid,legacy=row.split("\t",1)
        put_price(cid,vid,legacy,"CARDMARKET_WEB",eur,f"Cardmarket exact SVP promo trend; {cid.upper()}")

print("seeded exact remaining market cases")
