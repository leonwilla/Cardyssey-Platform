#!/usr/bin/env python3
"""Finish German physical cards that lack any market value.

Values are tied to exact marketplace identities:
- Cardmarket trend for DP promo base printings.
- German Cardmarket Near-Mint floor for the three Gold Star cards.
Special Worlds/staff/deck reprints are deliberately not assigned the base value.
"""
import json, subprocess

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def q(s): return str(s).replace("'","''")

def put(cid,vid,legacy,source,eur,detail):
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

# Cardmarket current trend on exact DP Black Star Promo products.
promo_trend={
    "dpp-DP05":("worlds-2007",402.89),
    "dpp-DP25":("worlds-2008",187.15),
    "dpp-DP48":("worlds-2009",251.75),
}
for cid,(base_stamp,eur) in promo_trend.items():
    rows=db(f"""SELECT v.value->>'id',COALESCE(v.value->>'legacyVariant','NORMAL'),
                       COALESCE(v.value->'stamps','[]'::jsonb)::text
                FROM catalog_cards_mirror c
                CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
                WHERE c.language_code='de' AND c.card_id='{q(cid)}';""").splitlines()
    for row in rows:
        vid,legacy,stamps_json=row.split("\t",2)
        stamps=[str(x).lower() for x in json.loads(stamps_json)]
        if stamps==[base_stamp]:
            put(cid,vid,legacy,"CARDMARKET_WEB",eur,f"Cardmarket exact product trend; {cid}")

# Exact Cardmarket product trends for the standard DP54/DP55 printings.
for cid,eur in {"dpp-DP54":18.85,"dpp-DP55":25.67}.items():
    row=db(f"""SELECT v.value->>'id',COALESCE(v.value->>'legacyVariant','HOLO')
               FROM catalog_cards_mirror c
               CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
               WHERE c.language_code='de' AND c.card_id='{cid}'
               LIMIT 1;""")
    vid,legacy=row.split("\t",1)
    put(cid,vid,legacy,"CARDMARKET_WEB",eur,f"Cardmarket exact product trend; {cid}")

# German Cardmarket NM floors, published 2026-10-03 for Gold Stars.
# Cardyssey stores the MINT base; NM display uses factor 0.90.
gold_nm={
    "ex12-92":1550.00,
    "ex15-101":2800.00,
    "ex8-105":4600.00,
}
for cid,nm_eur in gold_nm.items():
    rows=db(f"""SELECT v.value->>'id',COALESCE(v.value->>'legacyVariant','HOLO'),
                       COALESCE(v.value->'stamps','[]'::jsonb)::text
                FROM catalog_cards_mirror c
                CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
                WHERE c.language_code='de' AND c.card_id='{cid}';""").splitlines()
    for row in rows:
        vid,legacy,stamps_json=row.split("\t",2)
        stamps=json.loads(stamps_json)
        if stamps:
            continue
        base=round(nm_eur/0.90,4)
        put(cid,vid,legacy,"CARDMARKET_DE_NM_WEB",base,f"German Cardmarket NM floor; {cid}")

print("finished German cards without any price")
