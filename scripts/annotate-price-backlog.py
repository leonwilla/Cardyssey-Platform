#!/usr/bin/env python3
"""Add actionable reasons to unresolved price-cache rows.

Only blank/generic NO_PRICE diagnostics are replaced. Specific provider errors,
manual rollback notes, and successful prices are never touched.
"""
import subprocess

sql=r"""
WITH classified AS (
  SELECT p.card_id,p.language_code,p.variant_id,
         vi.blueprint_id AS variant_blueprint,
         ci.blueprint_id AS card_blueprint,
         vi.method AS variant_method
  FROM tcg_price_cache p
  LEFT JOIN cardtrader_variant_identity_cache vi
    ON vi.card_id=p.card_id
   AND vi.language_code=p.language_code
   AND vi.variant_id=p.variant_id
  LEFT JOIN cardtrader_identity_cache ci
    ON ci.card_id=p.card_id
   AND ci.language_code=p.language_code
  WHERE p.resolution_status='NO_PRICE'
)
UPDATE tcg_price_cache p
SET failure_detail=CASE
      WHEN x.variant_blueprint IS NOT NULL THEN
        CASE p.language_code
          WHEN 'zh-tw' THEN 'Exact variant identity; no acceptable zh-TW listing/price currently'
          WHEN 'zh-cn' THEN 'Exact variant identity; no acceptable zh-CN listing/price currently'
          WHEN 'ja' THEN 'Exact variant identity; no acceptable Japanese listing/price currently'
          WHEN 'de' THEN 'Exact variant identity; no acceptable German listing/price currently'
          WHEN 'en' THEN 'Exact variant identity; no acceptable English listing/price currently'
          ELSE 'Exact variant identity; no acceptable current listing/price'
        END
      WHEN x.card_blueprint IS NOT NULL THEN
        'Card-level provider identity exists; exact variant price unavailable'
      ELSE
        'No exact provider identity for this variant yet'
    END
FROM classified x
WHERE p.card_id=x.card_id
  AND p.language_code=x.language_code
  AND p.variant_id=x.variant_id
  AND p.resolution_status='NO_PRICE'
  AND (
    p.failure_detail IS NULL
    OR BTRIM(p.failure_detail)=''
    OR p.failure_detail='No current provider price during refresh'
    OR p.failure_detail='No exact provider identity for this variant yet'
    OR p.failure_detail='Card-level provider identity exists; exact variant price unavailable'
    OR p.failure_detail LIKE 'Exact variant identity; no acceptable % listing/price currently'
  );
"""
subprocess.run(
    ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
     "-v","ON_ERROR_STOP=1","-q"],
    input=sql,text=True,check=True,
)

summary=subprocess.run(
    ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
     "-At","-F","\t","-c",
     """SELECT language_code,failure_detail,COUNT(*)
        FROM tcg_price_cache
        WHERE resolution_status='NO_PRICE'
        GROUP BY language_code,failure_detail
        ORDER BY language_code,COUNT(*) DESC"""],
    capture_output=True,text=True,check=True,
).stdout.strip()
print(summary)
