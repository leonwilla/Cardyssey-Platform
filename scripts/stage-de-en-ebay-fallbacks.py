#!/usr/bin/env python3
"""Stage unresolved DE/EN special prints for exact eBay sold-comps review.

Preview by default. This never invents a price and never writes tcg_price_cache.
Only unresolved variants with explicit special-print identity (stamp, subtype or
foil marker) and an ambiguous/review provider mapping are eligible.
"""
import argparse
import json
import subprocess
from pathlib import Path

SELECT_SQL = r"""
SELECT jsonb_build_object(
 'language',r.language_code,'card_id',r.card_id,'variant_id',r.variant_id,
 'name',c.name,'number',c.local_id,'set_id',c.set_id,'variant',v.value,
 'old_status',r.search_status
)::text
FROM price_review_cases r
JOIN tcg_price_cache p USING(language_code,card_id,variant_id)
JOIN catalog_cards_mirror c
  ON c.language_code=r.language_code AND c.card_id=r.card_id
JOIN LATERAL (
 SELECT value FROM jsonb_array_elements(c.variants)
 WHERE value->>'id'=r.variant_id LIMIT 1
) v ON TRUE
WHERE r.language_code IN ('de','en')
  AND p.resolution_status='NO_PRICE'
  AND r.search_status IN ('READY_FOR_REVIEW','AMBIGUOUS_PRODUCT_IDENTITY','EBAY_FALLBACK')
  AND (
    COALESCE(v.value->>'subtype','') <> ''
    OR COALESCE(v.value->>'foil','') <> ''
    OR jsonb_array_length(COALESCE(v.value->'stamps','[]'::jsonb)) > 0
  )
ORDER BY r.language_code,r.card_id,r.variant_id
"""

def psql(sql: str) -> str:
    cmd=["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1",
         "-U","cardyssey","-d","cardyssey","-At","-c",sql]
    return subprocess.run(cmd,check=True,text=True,capture_output=True).stdout

def q(value: str) -> str:
    return "'" + value.replace("'","''") + "'"

def parts(value):
    if value is None:
        return []
    if isinstance(value,list):
        return [str(x).strip() for x in value if str(x).strip()]
    text=str(value).strip()
    return [text] if text else []

def build_query(row):
    variant=row.get("variant") or {}
    tokens=[row["name"],row["number"],row["set_id"]]
    tokens += ["German" if row["language"]=="de" else "English"]
    tokens += parts(variant.get("type"))
    tokens += parts(variant.get("subtype"))
    tokens += parts(variant.get("foil"))
    tokens += parts(variant.get("stamps"))
    seen=[]
    for token in tokens:
        token=" ".join(str(token).replace("_","-").split())
        if token and token.lower() not in {x.lower() for x in seen}:
            seen.append(token)
    return "Pokemon " + " ".join(seen) + " ungraded sold"

def candidate(row, query):
    variant=row.get("variant") or {}
    return {
        "match_type":"EBAY_FALLBACK",
        "status":"NEEDS_EXACT_SOLD_COMPS",
        "query":query,
        "required_identity":{
            "language":row["language"],
            "card_number":row["number"],
            "set_id":row["set_id"],
            "type":variant.get("type"),
            "subtype":variant.get("subtype"),
            "foil":variant.get("foil"),
            "stamps":variant.get("stamps") or [],
            "condition":"ungraded"
        },
        "verified":False,
        "reason":"Use only explicit sold listings matching this physical print; asking/active listings are not price evidence."
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()

    rows=[json.loads(line) for line in psql(SELECT_SQL).splitlines() if line.strip()]
    staged=[]
    updates=[]
    reason=("Special print identity is not uniquely mapped by Cardmarket/TCGplayer; "
            "exact eBay sold-comps must match language, number, stamps/subtype/foil and condition.")
    for row in rows:
        query=build_query(row)
        item=candidate(row,query)
        staged.append({**row,"query":query,"fallback":item})
        payload=json.dumps(item,ensure_ascii=False,separators=(",",":"))
        updates.append(f"""
UPDATE price_review_cases
SET search_status='EBAY_FALLBACK',
    search_query={q(query)},
    candidates=COALESCE((
      SELECT jsonb_agg(x)
      FROM jsonb_array_elements(candidates) x
      WHERE x->>'match_type'<>'EBAY_FALLBACK'
    ),'[]'::jsonb) || jsonb_build_array({q(payload)}::jsonb),
    failure_reason={q(reason)},
    checked_at=NOW()
WHERE language_code={q(row['language'])}
  AND card_id={q(row['card_id'])}
  AND variant_id={q(row['variant_id'])};
""")
    if args.apply and updates:
        psql("BEGIN;\n"+"\n".join(updates)+"\nCOMMIT;")
    report={
        "eligible":len(staged),
        "applied":len(staged) if args.apply else 0,
        "languages":{lang:sum(x["language"]==lang for x in staged) for lang in ("de","en")},
        "cases":staged
    }
    if args.report:
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},ensure_ascii=False))
    for row in staged:
        print(row["language"],row["card_id"],row["variant_id"],row["query"])

if __name__=="__main__":
    main()
