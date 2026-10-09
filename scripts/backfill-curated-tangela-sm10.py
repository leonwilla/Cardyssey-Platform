#!/usr/bin/env python3
import json, subprocess

CARDMARKET_ID = 372309
BLUEPRINT_ID = 130442
EXPANSION_ID = 1613
OLD_VARIANT_ID = "curated:sm10:16:reverse"

def variant_id(lang):
    return f"curated:{lang}:sm10:16:reverse"

def db_exec(sql):
    subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
         "-v","ON_ERROR_STOP=1","-q"],
        input=sql,text=True,check=True,
    )

parts=["BEGIN;"]
for lang in ("de","en"):
    vid=variant_id(lang)
    variant=json.dumps({
        "id":vid,
        "foil":None,
        "size":"standard",
        "type":"Reverse",
        "stamps":[],
        "subtype":None,
        "tcgDexEur":None,
        "legacyVariant":"REVERSE",
    },separators=(",",":")).replace("'","''")
    parts.append(f"""
UPDATE catalog_cards_mirror
SET variants = (
    SELECT COALESCE(jsonb_agg(item), '[]'::jsonb)
    FROM (
        SELECT value AS item
        FROM jsonb_array_elements(variants)
        WHERE value->>'id' <> '{OLD_VARIANT_ID}'
        UNION ALL
        SELECT '{variant}'::jsonb
        WHERE NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements(variants)
            WHERE value->>'id' = '{vid}'
        )
    ) x
)
WHERE language_code='{lang}' AND card_id='sm10-16';

DELETE FROM tcg_price_history
WHERE card_id='sm10-16' AND language_code='{lang}'
  AND variant_id='{OLD_VARIANT_ID}';

DELETE FROM tcg_price_cache
WHERE card_id='sm10-16' AND language_code='{lang}'
  AND variant_id='{OLD_VARIANT_ID}';

DELETE FROM cardtrader_variant_identity_cache
WHERE card_id='sm10-16' AND language_code='{lang}'
  AND variant_id='{OLD_VARIANT_ID}';

INSERT INTO tcg_price_cache(
    card_id,language_code,variant_id,legacy_variant,source,base_eur,
    updated_at,resolution_status,failure_detail,next_attempt_at
)
VALUES(
    'sm10-16','{lang}','{vid}','REVERSE',NULL,NULL,NOW(),'NO_PRICE',
    'Curated Unbroken Bonds Reverse Holo variant awaiting exact provider price',NOW()
)
ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET
    legacy_variant=EXCLUDED.legacy_variant,
    resolution_status=CASE
        WHEN tcg_price_cache.resolution_status='PRICE_FOUND' THEN tcg_price_cache.resolution_status
        ELSE 'NO_PRICE'
    END,
    failure_detail=CASE
        WHEN tcg_price_cache.resolution_status='PRICE_FOUND' THEN tcg_price_cache.failure_detail
        ELSE EXCLUDED.failure_detail
    END,
    next_attempt_at=CASE
        WHEN tcg_price_cache.resolution_status='PRICE_FOUND' THEN tcg_price_cache.next_attempt_at
        ELSE NOW()
    END;

INSERT INTO cardtrader_variant_identity_cache(
    card_id,language_code,variant_id,cardmarket_product_id,blueprint_id,expansion_id,method
)
VALUES(
    'sm10-16','{lang}','{vid}',{CARDMARKET_ID},{BLUEPRINT_ID},{EXPANSION_ID},
    'curated-unb-reverse'
)
ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET
    cardmarket_product_id=EXCLUDED.cardmarket_product_id,
    blueprint_id=EXCLUDED.blueprint_id,
    expansion_id=EXCLUDED.expansion_id,
    method=EXCLUDED.method,
    updated_at=NOW();
""")
parts.append("COMMIT;")
db_exec("\n".join(parts))
print("curated_tangela_sm10_backfill=ok")
