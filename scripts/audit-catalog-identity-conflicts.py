#!/usr/bin/env python3
"""Read-only review of official/provider identity conflicts in unpriced catalogue gaps.

A shared set/number is a review hint, never permission to copy variants or prices.
Different image URLs may represent separate printings or different image hosts.
"""
import argparse
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("conflict_retail", Path(__file__).with_name("resolve-zhtw-retailer-prices.py"))
retail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retail)

CANDIDATES_SQL = r"""
WITH candidates AS (
 SELECT c.language_code,c.card_id target_id,k.card_id provider_id,c.set_id,c.local_id,
        c.raw_payload->>'name' official_name,k.raw_payload->>'name' provider_name,
        c.image_source_url official_image,k.image_source_url provider_image,
        regexp_replace(c.raw_payload->>'name','\s','','g')
          IS DISTINCT FROM regexp_replace(k.raw_payload->>'name','\s','','g') AS name_differs,
        c.image_source_url IS DISTINCT FROM k.image_source_url AS image_differs
 FROM catalog_cards_mirror c JOIN catalog_cards_mirror k
 ON c.language_code=k.language_code AND c.set_id=k.set_id
 AND LTRIM(c.local_id,'0')=LTRIM(k.local_id,'0')
 WHERE c.language_code IN ('de','en','ja','ko','zh-cn','zh-tw')
 AND c.card_id LIKE 'official\_%' ESCAPE '\'
 AND k.card_id NOT LIKE 'official\_%' ESCAPE '\'
 AND c.set_id !~ '^(A[0-9]|B[0-9]|P-A)'
 AND COALESCE(jsonb_array_length(c.variants),0)=0 AND jsonb_array_length(k.variants)>0
 AND c.details_complete AND k.details_complete
), conflicts AS (
 SELECT *, CASE WHEN name_differs AND image_differs THEN 'name_and_image_differ'
                WHEN name_differs THEN 'name_differs_same_image'
                ELSE 'image_differs_same_name' END AS review_reason
 FROM candidates WHERE name_differs OR image_differs
)
"""
REPORT_SQL = CANDIDATES_SQL + """
SELECT jsonb_build_object(
 'scope','official_entries_missing_variants_with_provider_number_twins',
 'summary',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY language_code,review_reason)
   FROM (SELECT language_code,review_reason,COUNT(*) candidate_pairs,
          COUNT(DISTINCT target_id) official_entries
         FROM conflicts GROUP BY language_code,review_reason) s),'[]'::jsonb),
 'samples',COALESCE((SELECT jsonb_agg(to_jsonb(s))
   FROM (SELECT * FROM conflicts
         ORDER BY name_differs DESC,image_differs DESC,language_code,set_id,local_id,target_id,provider_id
         LIMIT 100) s),'[]'::jsonb),
 'sample_limit',100,'automatic_repairs',0);
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = json.loads(retail.db("BEGIN READ ONLY;\n" + REPORT_SQL + "\nCOMMIT;"))
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
