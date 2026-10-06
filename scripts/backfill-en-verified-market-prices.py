#!/usr/bin/env python3
"""Seed exact English market identities not represented cleanly in TCGdex."""
import json, subprocess
USD_TO_EUR=0.88739

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()
def q(s): return str(s).replace("'","''")
def put(cid,vid,legacy,usd,pid,subtype):
    eur=round((usd*USD_TO_EUR)/0.90,4)
    detail=q(f"TCGplayer product {pid}; {subtype}")
    db(f"""INSERT INTO tcg_price_cache
(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
VALUES ('{q(cid)}','en','{q(vid)}','{q(legacy)}','TCGCSV_TCGPLAYER',{eur},NOW(),'PRICE_FOUND','{detail}',NOW()+INTERVAL '7 days')
ON CONFLICT (card_id,language_code,variant_id) DO UPDATE SET
legacy_variant=EXCLUDED.legacy_variant,source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail=EXCLUDED.failure_detail,
next_attempt_at=EXCLUDED.next_attempt_at;""")
    db(f"""INSERT INTO tcg_price_history
(card_id,language_code,variant_id,source,base_eur,captured_at)
VALUES ('{q(cid)}','en','{q(vid)}','TCGCSV_TCGPLAYER',{eur},NOW());""")

# Exact TCGplayer products and current market USD.
exact={
 "basep-2": (12.39,85107,"Normal"),
 "basep-3": (39.49,87414,"Normal"),
 "basep-5": (59.76,84909,"Normal"),
 "basep-8": (37.25,607818,"Normal"),
 "basep-11":(52.58,85074,"Holofoil"),
 "g1-RC31":(107.33,113773,"Holofoil"),
}
for cid,(usd,pid,subtype) in exact.items():
    rows=db(f"""SELECT v.value->>'id',COALESCE(v.value->>'legacyVariant','NORMAL')
                FROM catalog_cards_mirror c
                CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
                WHERE c.language_code='en' AND c.card_id='{q(cid)}';""").splitlines()
    for row in rows:
        vid,legacy=row.split("\t",1)
        put(cid,vid,legacy,usd,pid,subtype)

# Historical Unown (?) row has no variant metadata in the catalog.
cid="exu-%3F"
variants=[{
    "id":"legacy:holo","type":"Holo","subtype":None,"foil":None,
    "size":"Standard","stamps":[],"legacyVariant":"HOLO","tcgDexEur":None
}]
db(f"""UPDATE catalog_cards_mirror
SET variants='{q(json.dumps(variants,separators=(",",":")))}'::jsonb,
    details_complete=TRUE,source_updated_at=NOW()
WHERE language_code='en' AND card_id='{cid}';""")
put(cid,"legacy:holo","HOLO",139.99,90167,"Holofoil")
print("seeded exact English market identities")
