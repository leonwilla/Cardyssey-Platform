#!/usr/bin/env python3
"""Recover duplicate catalogue entries only from one exact, same-language image identity.

No rows/collection references are merged or deleted. Copied prices retain the
original timestamps and are not counted as independently discovered market prices.
"""
import argparse
import json
import subprocess

PAIRS_SQL = r"""
WITH candidates AS (
 SELECT c.card_id,c.language_code,k.card_id source_id,k.variants,
 COUNT(*) OVER(PARTITION BY c.card_id,c.language_code) AS matches,
 COALESCE(jsonb_array_length(c.variants),0)=0 AS missing
 FROM catalog_cards_mirror c JOIN catalog_cards_mirror k
 ON k.language_code=c.language_code AND k.set_id=c.set_id
 AND LTRIM(k.local_id,'0')=LTRIM(c.local_id,'0')
 AND k.image_source_url=c.image_source_url
 AND regexp_replace(c.raw_payload->>'name','\s','','g')=regexp_replace(k.raw_payload->>'name','\s','','g')
 WHERE c.language_code IN ('de','en','ja','ko','zh-cn','zh-tw')
 AND c.card_id<>k.card_id AND c.details_complete AND k.details_complete
 AND c.image_source_url IS NOT NULL AND c.image_source_url<>''
 AND c.set_id !~ '^(A[0-9]|B[0-9]|P-A)'
 AND jsonb_array_length(k.variants)>0
 AND k.raw_payload->>'_cardyssey_verified_variant_source' IS NULL
 AND NOT EXISTS(SELECT 1 FROM tcg_price_cache kp WHERE kp.card_id=k.card_id
   AND kp.language_code=k.language_code AND kp.failure_detail LIKE '%Exact catalogue duplicate of %')
 AND (COALESCE(jsonb_array_length(c.variants),0)=0
      OR (c.raw_payload->>'_cardyssey_verified_variant_source'=k.card_id AND c.variants=k.variants)
      OR (c.raw_payload->>'_cardyssey_verified_variant_source' IS NULL AND c.variants=k.variants
          AND EXISTS(SELECT 1 FROM tcg_price_cache cp WHERE cp.card_id=c.card_id
            AND cp.language_code=c.language_code AND cp.failure_detail LIKE
              '%Exact catalogue duplicate of ' || k.card_id || ';%')))
), verified AS (
 SELECT * FROM candidates WHERE matches=1
 AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(variants) v(value)
   WHERE COALESCE(v.value->>'id','')='' OR COALESCE(v.value->>'legacyVariant','')='')
)
"""
PREVIEW_SQL = PAIRS_SQL + """
SELECT jsonb_build_object('verified_entries',COUNT(*),'missing_entries',COUNT(*) FILTER(WHERE missing),
 'variants',COALESCE(SUM(jsonb_array_length(variants)),0),
 'pairs',COALESCE(jsonb_agg(jsonb_build_object('card_id',card_id,'language_code',language_code,'source_id',source_id)),'[]'))
FROM verified;
"""
APPLY_SQL = PAIRS_SQL + """
, changed_catalog AS (
 UPDATE catalog_cards_mirror c SET variants=q.variants,
 raw_payload=jsonb_set(c.raw_payload,'{_cardyssey_verified_variant_source}',to_jsonb(q.source_id),true)
 FROM verified q WHERE c.card_id=q.card_id AND c.language_code=q.language_code
 AND (COALESCE(jsonb_array_length(c.variants),0)=0 OR
      (c.variants=q.variants AND c.raw_payload->>'_cardyssey_verified_variant_source' IS NULL))
 RETURNING c.card_id,c.language_code
), copied_prices AS (
 INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,source,base_eur,
                            updated_at,resolution_status,failure_detail,next_attempt_at)
 SELECT q.card_id,q.language_code,p.variant_id,p.legacy_variant,p.source,p.base_eur,
        p.updated_at,p.resolution_status,
        COALESCE(p.failure_detail,'') || ' | Exact catalogue duplicate of ' || q.source_id
        || '; same language/set/number/native-name/image URL; original price timestamp retained',
        p.next_attempt_at
 FROM verified q JOIN tcg_price_cache p ON p.card_id=q.source_id AND p.language_code=q.language_code
 JOIN LATERAL jsonb_array_elements(q.variants) v(value) ON v.value->>'id'=p.variant_id
 WHERE p.resolution_status='PRICE_FOUND' AND p.base_eur>0
 AND p.base_eur::text NOT IN ('NaN','Infinity','-Infinity')
 AND p.updated_at>=NOW()-INTERVAL '8 days'
 ON CONFLICT(card_id,language_code,variant_id) DO UPDATE
 SET source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,updated_at=EXCLUDED.updated_at,
     resolution_status=EXCLUDED.resolution_status,failure_detail=EXCLUDED.failure_detail,
     next_attempt_at=EXCLUDED.next_attempt_at
 WHERE tcg_price_cache.updated_at<EXCLUDED.updated_at
 RETURNING card_id,language_code,variant_id,source,base_eur
), history AS (
 INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
 SELECT p.card_id,p.language_code,p.variant_id,p.source,p.base_eur,h.captured_at
 FROM copied_prices p JOIN verified q ON q.card_id=p.card_id AND q.language_code=p.language_code
 JOIN LATERAL (
  SELECT h.captured_at FROM tcg_price_history h WHERE h.card_id=q.source_id
  AND h.language_code=p.language_code AND h.variant_id=p.variant_id
  AND h.source=p.source AND h.base_eur=p.base_eur
  ORDER BY h.captured_at DESC LIMIT 1
 ) h ON TRUE
 WHERE NOT EXISTS(SELECT 1 FROM tcg_price_history old
  WHERE old.card_id=p.card_id AND old.language_code=p.language_code AND old.variant_id=p.variant_id
  AND old.source=p.source AND old.base_eur=p.base_eur AND old.captured_at=h.captured_at)
 RETURNING 1
)
SELECT jsonb_build_object('catalog_entries_repaired',(SELECT COUNT(*) FROM changed_catalog),
 'price_rows_copied',(SELECT COUNT(*) FROM copied_prices),
 'original_history_points_copied',(SELECT COUNT(*) FROM history));
"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    sql=APPLY_SQL if args.apply else PREVIEW_SQL
    result=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-U','cardyssey','-d','cardyssey',
                           '-X','-qAt','-v','ON_ERROR_STOP=1'],
                          input="BEGIN; SET LOCAL statement_timeout='20s';\n"+sql+'\nCOMMIT;',
                          text=True,capture_output=True,check=True,timeout=30)
    print(json.dumps(json.loads(result.stdout.strip()),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
