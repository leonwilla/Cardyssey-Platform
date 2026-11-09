#!/usr/bin/env python3
"""Export complete Cardmarket DE/EN variant queues from Cardyssey PostgreSQL.

Read only. Product IDs from catalog candidates or TCGdex are *unverified* hints.
"""
import argparse
import csv
import json
import os
import subprocess
from pathlib import Path

SQL = r"""
COPY (
WITH source AS (
 SELECT c.language_code,c.card_id,c.set_id,c.local_id,c.name,c.variants,
        k.provider_product_ids,k.candidate_status
 FROM catalog_cards_mirror c
 LEFT JOIN cardmarket_catalog_link_candidates k
   ON k.language_code=c.language_code AND k.card_id=c.card_id
 WHERE c.language_code='{language}'
)
SELECT
 c.card_id AS cardyssey_karte,
 v.value->>'id' AS variante_id,
 c.set_id,
 c.local_id AS kartennummer,
 c.name AS kartenname_suche,
 COALESCE(v.value->>'type','') AS drucktyp,
 COALESCE(v.value->>'subtype','') AS sonderdruck,
 COALESCE(v.value->>'foil','') AS foil,
 COALESCE(v.value->>'stamps','[]') AS stempel,
 CASE WHEN r.primary_provider='CARDMARKET'
      AND r.verification_state='VERIFIED_PRODUCT_ID'
      AND COALESCE(r.provider_product_id,'') ~ '^[0-9]+$'
   THEN r.provider_product_id
 ELSE COALESCE(
   (SELECT string_agg(DISTINCT pid,',' ORDER BY pid) FROM (
      SELECT jsonb_array_elements_text(
         CASE WHEN jsonb_typeof(c.provider_product_ids)='array'
              THEN c.provider_product_ids ELSE '[]'::jsonb END
      ) pid
      UNION
      SELECT v.value->>'cardmarketProductId' pid
      UNION
      SELECT CASE WHEN r.primary_provider='CARDMARKET' THEN r.provider_product_id END pid
   ) candidates WHERE pid ~ '^[0-9]+$'), ''
 ) END AS cardmarket_ids,
 COALESCE(r.provider_product_url,'') AS known_url,
 CASE WHEN r.primary_provider='CARDMARKET' AND r.verification_state='VERIFIED_PRODUCT_ID'
  AND r.source_evidence LIKE 'Human confirmed exact%'
  THEN COALESCE(to_char(r.updated_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),'')
  ELSE '' END AS manual_scan_requested_at,
 COALESCE(r.verification_state,'UNVERIFIED') AS routing_state,
 COALESCE(c.candidate_status,'NO_CATALOG_CANDIDATE') AS candidate_status,
 CASE WHEN lower(coalesce(v.value->>'type','')) IN ('normal','nonholo','common') THEN '4' ELSE '2' END AS scan_tier,
 'YES' AS needs_price
FROM source c
CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c.variants,'[]'::jsonb)) AS v(value)
LEFT JOIN price_source_routing r
 ON r.language_code=c.language_code AND r.card_id=c.card_id
 AND r.variant_id=v.value->>'id'
ORDER BY c.set_id,c.local_id,c.card_id,v.value->>'id'
) TO STDOUT WITH (FORMAT csv, HEADER, ENCODING 'UTF8');
"""

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--language",choices=("de","en"),required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    sql=SQL.format(language=args.language)
    process=subprocess.run(["docker","exec","cardyssey-db","psql","-X","-qAt",
                            "-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey","-c",sql],
                           capture_output=True,check=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.output.with_suffix(args.output.suffix+".tmp")
    tmp.write_bytes(process.stdout)
    with tmp.open(encoding="utf-8",newline="") as f:
        data=list(csv.DictReader(f))
    if not data or any(not r["variante_id"] or not r["kartennummer"] for r in data):
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Invalid queue: empty or missing variant ID/card number")
    keys={(r["cardyssey_karte"],r["variante_id"]) for r in data}
    if len(keys)!=len(data):
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Duplicate variant identities in queue")
    os.replace(tmp,args.output)
    result={"language":args.language,"variants":len(data),
            "candidate_rows":sum(bool(r["cardmarket_ids"]) for r in data),
            "with_existing_url":sum(bool(r["known_url"]) for r in data),
            "output":str(args.output)}
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
