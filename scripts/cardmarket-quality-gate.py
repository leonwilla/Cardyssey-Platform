#!/usr/bin/env python3
"""Read-only DE/EN Cardmarket quality gate. No inferred products or prices."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SQL = """
WITH catalog AS (
  SELECT language_code, count(*) AS cards
  FROM catalog_cards_mirror WHERE language_code IN ('de','en')
  GROUP BY language_code
), links AS (
  SELECT language_code, count(*) FILTER (WHERE jsonb_array_length(provider_product_ids)>0) AS id_candidates,
    count(*) FILTER (WHERE candidate_status='SINGLE_SET_PRODUCT') AS unique_candidates
  FROM cardmarket_catalog_link_candidates GROUP BY language_code
), routing AS (
  SELECT language_code,
    count(*) FILTER (WHERE primary_provider='CARDMARKET' AND nullif(provider_product_id,'') IS NOT NULL) AS ids,
    count(*) FILTER (WHERE primary_provider='CARDMARKET' AND nullif(provider_product_url,'') IS NOT NULL) AS urls,
    count(*) FILTER (WHERE primary_provider='CARDMARKET' AND verification_state NOT IN ('SOURCE_ONLY')) AS verified
  FROM price_source_routing GROUP BY language_code
), price AS (
  SELECT language_code, count(*) FILTER (WHERE source ILIKE '%CARDMARKET%' AND resolution_status='PRICE_FOUND') AS cm_prices,
    count(*) FILTER (WHERE resolution_status='PRICE_FOUND') AS any_price,
    count(*) AS total_variants
  FROM tcg_price_cache GROUP BY language_code
)
SELECT coalesce(jsonb_agg(jsonb_build_object(
  'language',c.language_code,'cards',c.cards,
  'id_candidates',coalesce(l.id_candidates,0),
  'unique_candidates',coalesce(l.unique_candidates,0),
  'routed_ids',coalesce(r.ids,0),
  'routed_urls',coalesce(r.urls,0),
  'verified_routes',coalesce(r.verified,0),
  'cardmarket_prices',coalesce(p.cm_prices,0),
  'prices_all_sources',coalesce(p.any_price,0),
  'price_variants',coalesce(p.total_variants,0)
) ORDER BY c.language_code),'[]'::jsonb)
FROM catalog c LEFT JOIN links l USING(language_code)
LEFT JOIN routing r USING(language_code)
LEFT JOIN price p USING(language_code);
"""

def main():
    result = subprocess.run(
        ["docker","exec","-i","cardyssey-db","psql","-X","-qAt",
         "-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],
        input="BEGIN READ ONLY; SET LOCAL statement_timeout='25s';\n" + SQL + "\nCOMMIT;\n",
        text=True,capture_output=True,timeout=40,check=True)
    rows=json.loads(result.stdout.strip())
    issues=[]
    for row in rows:
        language=row["language"]
        if row["routed_urls"] < row["cards"]:
            issues.append(f"{language}: Cardmarket URLs {row['routed_urls']}/{row['cards']}")
        if row["routed_ids"] < row["cards"]:
            issues.append(f"{language}: Cardmarket IDs {row['routed_ids']}/{row['cards']}")
        if row["cardmarket_prices"] < row["price_variants"]:
            issues.append(f"{language}: Cardmarket prices {row['cardmarket_prices']}/{row['price_variants']} variants")
        if row["id_candidates"] < row["cards"]:
            issues.append(f"{language}: unresolved catalog links {row['cards']-row['id_candidates']}")
    status="QUALITY_GAP" if issues else "QUALITY_OK"
    report={"checked_at":datetime.now(timezone.utc).isoformat(),"status":status,
            "languages":rows,"issues":issues,
            "caution":"Catalog candidates are not verified language/condition/print identities."}
    state=Path.home()/".local/state/cardyssey-codex"
    state.mkdir(parents=True,exist_ok=True)
    output=state/"latest-quality.json"
    tmp=output.with_suffix(".tmp")
    tmp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    tmp.replace(output)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
