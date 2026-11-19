#!/usr/bin/env python3
"""Export complete Cardmarket DE/EN variant queues from Cardyssey PostgreSQL.

Read only. Export current price eligibility inputs along with all catalog
variants. Product IDs from catalog candidates or TCGdex are unverified hints.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
from cardmarket_browser_queue import browser_scan_tier

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
   ON k.language_code='de' AND k.card_id=c.card_id
   -- The Cardmarket expansion/product is defined by the set and collector
   -- card identity, not the requested offering language. DE is the verified
   -- set-candidate source for both DE/EN queues. A physical print is still
   -- unverified when only the card-level ID is available.
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
 -- Cardyssey stores the exact Cardmarket ID on EACH physical variant.
 -- Never merge all products with the same card name: Undaunted Houndoom
 -- UD5 and UD82 are different cards even though both are called Houndoom.
 ELSE COALESCE(
   CASE WHEN v.value->>'cardmarketProductId' ~ '^[0-9]{{3,12}}$'
        THEN v.value->>'cardmarketProductId' END,
   CASE WHEN r.primary_provider='CARDMARKET'
             AND r.provider_product_id ~ '^[0-9]{{3,12}}$'
        THEN r.provider_product_id END,
   CASE WHEN jsonb_typeof(c.provider_product_ids)='array'
             AND jsonb_array_length(c.provider_product_ids)=1
        THEN c.provider_product_ids->>0 END,
   ''
 ) END AS cardmarket_ids,
 -- A previously observed URL belongs to one product ID; never pair it with
 -- a different per-variant ID without a new visit to the product page.
 CASE WHEN r.verification_state='VERIFIED_PRODUCT_ID'
           OR NULLIF(v.value->>'cardmarketProductId','') IS NULL
           OR r.provider_product_id=v.value->>'cardmarketProductId'
      THEN COALESCE(r.provider_product_url,'') ELSE '' END AS known_url,
 CASE WHEN r.primary_provider='CARDMARKET' AND r.verification_state='VERIFIED_PRODUCT_ID'
  AND r.source_evidence LIKE 'Human confirmed exact%'
  THEN COALESCE(to_char(r.updated_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),'')
  ELSE '' END AS manual_scan_requested_at,
 COALESCE(r.verification_state,'UNVERIFIED') AS routing_state,
 COALESCE(c.candidate_status,'NO_CATALOG_CANDIDATE') AS candidate_status,
 -- Cardmarket candidates for the CARD, used only for print-uncertain hints.
 -- Never promote these into a variant-level verified route.
 COALESCE((SELECT string_agg(x.id,',' ORDER BY x.id) FROM (
     SELECT DISTINCT jsonb_array_elements_text(
       CASE WHEN jsonb_typeof(c.provider_product_ids)='array'
         THEN c.provider_product_ids ELSE '[]'::jsonb END) AS id
   ) x), '') AS set_card_candidate_ids,
 CASE WHEN lower(coalesce(v.value->>'type','')) IN ('normal','nonholo','common') THEN '4' ELSE '2' END AS scan_tier,
 CASE WHEN p.resolution_status='PRICE_FOUND' AND p.base_eur>0 THEN 'NO' ELSE 'YES' END AS needs_price,
 CASE WHEN p.resolution_status='PRICE_FOUND' AND p.base_eur>0 THEN p.base_eur::text ELSE '' END AS existing_price_eur,
 COALESCE(p.source,'') AS existing_source
FROM source c
CROSS JOIN LATERAL jsonb_array_elements(COALESCE(c.variants,'[]'::jsonb)) AS v(value)
LEFT JOIN price_source_routing r
 ON r.language_code=c.language_code AND r.card_id=c.card_id
 AND r.variant_id=v.value->>'id'
LEFT JOIN tcg_price_cache p
 ON p.language_code=c.language_code AND p.card_id=c.card_id
 AND p.variant_id=v.value->>'id'
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
    # Export the same live browser tiers used by prioritization and monitoring.
    for row in data:
        row["scan_tier"] = browser_scan_tier(row)
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    os.replace(tmp,args.output)
    result={"language":args.language,"variants":len(data),
            "candidate_rows":sum(bool(r["cardmarket_ids"]) for r in data),
            "with_existing_url":sum(bool(r["known_url"]) for r in data),
            "output":str(args.output)}
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
