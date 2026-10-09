#!/usr/bin/env python3
"""Read-only coverage report: catalogue entries are not the same as priced variants."""
import json
import subprocess

LANGUAGES = ('de', 'en', 'ja', 'ko', 'zh-cn', 'zh-tw')
SUMMARY_SQL = """
WITH languages(language_code) AS (VALUES ('de'),('en'),('ja'),('ko'),('zh-cn'),('zh-tw')),
physical AS (
 SELECT c.* FROM catalog_cards_mirror c JOIN languages USING(language_code)
 WHERE c.set_id !~ '^(A[0-9]|B[0-9]|P-A)'
), known AS (
 SELECT DISTINCT language_code,set_id,LTRIM(local_id,'0') num FROM physical
 WHERE jsonb_array_length(variants)>0
), cards AS (
 SELECT c.language_code,COUNT(*) catalog_entries,
 COUNT(*) FILTER(WHERE NOT c.details_complete) incomplete_details,
 COUNT(*) FILTER(WHERE COALESCE(jsonb_array_length(c.variants),0)=0) missing_variants,
 COUNT(*) FILTER(WHERE COALESCE(jsonb_array_length(c.variants),0)=0 AND k.language_code IS NOT NULL) missing_with_number_twin,
 COUNT(*) FILTER(WHERE COALESCE(jsonb_array_length(c.variants),0)=0 AND k.language_code IS NULL) missing_without_number_twin
 FROM physical c LEFT JOIN known k ON k.language_code=c.language_code AND k.set_id=c.set_id AND k.num=LTRIM(c.local_id,'0')
 GROUP BY c.language_code
), variants AS (
 SELECT c.language_code,c.card_id,v.value->>'id' variant_id
 FROM physical c CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
 WHERE COALESCE(v.value->>'id','')<>''
), coverage AS (
 SELECT v.language_code,COUNT(*) catalog_variants,
 COUNT(*) FILTER(WHERE p.card_id IS NULL) missing_cache,
 COUNT(*) FILTER(WHERE p.resolution_status='PRICE_FOUND') price_found,
 COUNT(*) FILTER(WHERE p.resolution_status='NO_PUBLIC_PRICE') deferred,
 COUNT(*) FILTER(WHERE p.resolution_status='NO_PRICE') no_price,
 COUNT(*) FILTER(WHERE p.resolution_status='PROVIDER_ERROR') provider_error,
 COUNT(*) FILTER(WHERE p.resolution_status NOT IN ('PRICE_FOUND','NO_PUBLIC_PRICE','NO_PRICE','PROVIDER_ERROR')) other_status
 FROM variants v LEFT JOIN tcg_price_cache p USING(language_code,card_id,variant_id)
 GROUP BY v.language_code
)
SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY language_code),'[]'::jsonb) FROM (
 SELECT l.language_code,COALESCE(c.catalog_entries,0) catalog_entries,
 COALESCE(c.incomplete_details,0) incomplete_details,
 COALESCE(c.missing_variants,0) missing_variants,
 COALESCE(c.missing_with_number_twin,0) missing_with_number_twin,
 COALESCE(c.missing_without_number_twin,0) missing_without_number_twin,
 COALESCE(v.catalog_variants,0) catalog_variants,COALESCE(v.missing_cache,0) missing_cache,
 COALESCE(v.price_found,0) price_found,COALESCE(v.deferred,0) deferred,
 COALESCE(v.no_price,0) no_price,COALESCE(v.provider_error,0) provider_error,
 COALESCE(v.other_status,0) other_status
 FROM languages l LEFT JOIN cards c USING(language_code) LEFT JOIN coverage v USING(language_code)
) t;
"""


def main():
    result = subprocess.run(
        ['docker','exec','-i','cardyssey-db','psql','-U','cardyssey','-d','cardyssey',
         '-X','-qAt','-v','ON_ERROR_STOP=1'],
        input="BEGIN READ ONLY; SET LOCAL statement_timeout='20s';\n" + SUMMARY_SQL + "\nCOMMIT;",
        text=True,capture_output=True,check=True,timeout=30,
    )
    rows = json.loads(result.stdout.strip())
    print(json.dumps({'scope':'physical_catalog_entries_and_variants', 'languages':rows}, ensure_ascii=False,indent=2))
    print('Missing variants may include duplicate catalogue entries. A set/number twin is a review hint, not a verified identity.')
    print('PRICE_FOUND counts include provider guides, estimates and retailer references; they are not a count of verified sales.')


if __name__ == '__main__':
    main()
