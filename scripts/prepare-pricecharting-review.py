#!/usr/bin/env python3
"""Prepare PriceCharting research evidence for unresolved physical variants.

No bulk scraping and NO auto-pricing from name-only search results.
The free public product pages are a human-review source; a PriceCharting
product needs separately verified printing and language before publishing.
"""
import argparse,json,subprocess,urllib.parse
from pathlib import Path

DB=["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t"]
def sql(text):
 return subprocess.run(DB+["-c",text],check=True,text=True,capture_output=True).stdout
def quote(value):return "'"+str(value).replace("'","''")+"'"
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--apply",action="store_true")
 p.add_argument("--report",type=Path,default=Path("/tmp/cardyssey-pricecharting-research.json"))
 a=p.parse_args()
 query="""SELECT r.language_code,r.card_id,r.variant_id,c.name,c.local_id,
  c.set_id,v.value::text
 FROM price_review_cases r
 JOIN catalog_cards_mirror c ON c.card_id=r.card_id AND c.language_code=r.language_code
 LEFT JOIN LATERAL (SELECT x.value FROM jsonb_array_elements(c.variants) x(value)
   WHERE x.value->>'id'=r.variant_id LIMIT 1) v ON TRUE
 LEFT JOIN tcg_price_cache p ON p.card_id=r.card_id AND p.language_code=r.language_code AND p.variant_id=r.variant_id
 WHERE COALESCE(p.resolution_status,'NO_PRICE')<>'PRICE_FOUND'
 ORDER BY r.language_code,r.card_id,r.variant_id"""
 rows=[]
 for line in sql(query).splitlines():
  parts=line.split("\t",6)
  if len(parts)!=7:continue
  lng,card,variant,name,number,setid,raw=parts
  try:details=json.loads(raw) if raw not in ("","") else {}
  except ValueError:details={}
  if not isinstance(details,dict):details={}
  num=(str(number or "").strip())
  # Only base1 has an independently confirmed 102-card collector denominator.
  collector=num+"/102" if setid=="base1" and num.isdigit() else num
  terms=[name,collector]
  for key in ("subtype","foil","size"):
   value=str(details.get(key) or "").strip()
   if value and value.lower() not in ("standard","normal","none","unlimited","unbegrenzt"):terms.append(value)
  for value in details.get("stamps") or []:
   if value:terms.append(str(value))
  search=" ".join(x for x in terms if x)
  url="https://www.pricecharting.com/search-products?type=prices&q="+urllib.parse.quote(search)
  rows.append(dict(language=lng,card_id=card,variant_id=variant,search_terms=search,
                   source_url=url,match_status="RESEARCH_REQUIRED",
                   reason="Product name/number is only a search hint; edition, language, condition, print and unique product ID need verification."))
 if a.apply and rows:
  payload=quote(json.dumps(rows,ensure_ascii=False))
  statement="""WITH scans AS (SELECT jsonb_array_elements("""+payload+"""::jsonb) AS x),
 refined AS (SELECT r.language_code,r.card_id,r.variant_id,
 COALESCE((SELECT jsonb_agg(e) FROM jsonb_array_elements(r.candidates) e
 WHERE e->>'match_type'<>'PRICECHARTING_SEARCH_HINT'),'[]'::jsonb)||
 jsonb_build_array(jsonb_build_object('match_type','PRICECHARTING_SEARCH_HINT',
 'url',scans.x->>'source_url','query',scans.x->>'search_terms',
 'match_status','RESEARCH_REQUIRED','reason',scans.x->>'reason')) candidates
 FROM price_review_cases r JOIN scans ON r.language_code=scans.x->>'language'
  AND r.card_id=scans.x->>'card_id' AND r.variant_id=scans.x->>'variant_id')
 UPDATE price_review_cases r SET candidates=refined.candidates FROM refined
 WHERE r.language_code=refined.language_code AND r.card_id=refined.card_id
 AND r.variant_id=refined.variant_id"""
  sql(statement)
 report={"total_review_cases":len(rows),"staged_for_review":len(rows) if a.apply else 0,
  "published_prices":0,"reason":"Public search results cannot prove exact-print price"}
 a.report.write_text(json.dumps({"summary":report,"research":rows},indent=2,ensure_ascii=False)+"\n")
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
