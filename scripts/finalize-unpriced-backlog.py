#!/usr/bin/env python3
"""Defer unresolved price rows after the complete free-provider/public-web pass.

The weekly job reactivates these after 90 days so newly listed cards are retried.
Existing NO_PUBLIC_PRICE rows (for example unreleased promos with a specific
release-date retry) are intentionally left untouched.
"""
import subprocess

sql=r"""
WITH classified AS (
  SELECT p.card_id,p.language_code,p.variant_id,
         vi.blueprint_id AS variant_blueprint,
         vi.method AS variant_method,
         ci.blueprint_id AS card_blueprint
  FROM tcg_price_cache p
  LEFT JOIN cardtrader_variant_identity_cache vi
    ON vi.card_id=p.card_id
   AND vi.language_code=p.language_code
   AND vi.variant_id=p.variant_id
  LEFT JOIN cardtrader_identity_cache ci
    ON ci.card_id=p.card_id
   AND ci.language_code=p.language_code
  WHERE p.resolution_status='NO_PRICE'
    AND p.language_code IN ('de','en','ja','zh-cn','zh-tw')
)
UPDATE tcg_price_cache p
SET resolution_status='NO_PUBLIC_PRICE',
    failure_detail=CASE
      WHEN x.variant_blueprint IS NOT NULL THEN
        'NO_PUBLIC_PRICE: exact variant identity verified; full Cardmarket/CardTrader/TCGCSV/public-retailer pass found no usable exact market price'
      WHEN x.card_blueprint IS NOT NULL THEN
        'NO_PUBLIC_PRICE: card identity verified but no exact variant-specific public market price after full provider/web pass'
      ELSE
        'NO_PUBLIC_PRICE: no exact provider identity or supported public-retailer match after full provider/web pass'
    END,
    next_attempt_at=NOW()+INTERVAL '90 days',
    updated_at=NOW()
FROM classified x
WHERE p.card_id=x.card_id
  AND p.language_code=x.language_code
  AND p.variant_id=x.variant_id
  AND p.resolution_status='NO_PRICE';
"""
subprocess.run(
    ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
     "-v","ON_ERROR_STOP=1","-q"],
    input=sql,text=True,check=True,
)

summary=subprocess.run(
    ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
     "-At","-F","\t","-c",
     """SELECT language_code,resolution_status,COUNT(*)
        FROM tcg_price_cache
        WHERE language_code IN ('de','en','ja','ko','zh-cn','zh-tw')
        GROUP BY language_code,resolution_status
        ORDER BY language_code,resolution_status"""],
    capture_output=True,text=True,check=True,
).stdout.strip()
print(summary,flush=True)
