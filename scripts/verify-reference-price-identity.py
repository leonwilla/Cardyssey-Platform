#!/usr/bin/env python3
"""Classify staged reference prices against physical card identity. Fail closed."""
import argparse,collections,json,subprocess
from datetime import date
from pathlib import Path

def classify(variant, evidence, language):
 origin=evidence.get("origin_language")
 if origin and origin != language:
  return "CROSS_LANGUAGE_REFERENCE", ["ENGLISH_REFERENCE_NOT_GERMAN_PRICE","PRINT_AND_CONDITION_UNVERIFIED"]
 quotes=evidence.get("quotes") or []
 index=evidence.get("index") or {}
 locale_quotes=[q for q in quotes if q.get("locale")==language and isinstance(q.get("amount"),(int,float))]
 reasons=[]
 if not locale_quotes: reasons.append("NO_LANGUAGE_QUOTE")
 if not any(q.get("printing") for q in locale_quotes):reasons.append("PRINTING_NOT_IDENTIFIED")
 size=str(variant.get("size") or "standard").lower()
 if size not in ("standard",""):
  if not any(size in str(q.get("printing") or "").lower() for q in locale_quotes):reasons.append("SIZE_NOT_VERIFIED")
 stamps=variant.get("stamps") or []
 if stamps:reasons.append("STAMP_NOT_VERIFIED")
 subtype=variant.get("subtype")
 if subtype:reasons.append("SUBTYPE_NOT_VERIFIED")
 foil=variant.get("foil")
 if foil:reasons.append("FOIL_NOT_VERIFIED")
 if any(q.get("condition") is None for q in locale_quotes):reasons.append("CONDITION_MIXED_OR_UNKNOWN")
 if any(q.get("basis")=="ASKING" for q in locale_quotes):reasons.append("ASKING_NOT_SOLD")
 if not any(q.get("basis") in ("SOLD","TRANSACTION") for q in locale_quotes):reasons.append("NO_VERIFIED_SOLD_COMPS")
 if any(q.get("currency")!="EUR" for q in locale_quotes):reasons.append("MIXED_CURRENCY_QUOTES")
 index_date=str(index.get("as_of") or "")
 if index_date:
  try:
   if (date.today()-date.fromisoformat(index_date)).days>8:reasons.append("STALE_REFERENCE")
  except ValueError:reasons.append("INVALID_REFERENCE_DATE")
 status="READY_FOR_EXACT_PRICE_REVIEW" if not reasons else "REQUIRES_IDENTITY_REVIEW"
 return status,sorted(set(reasons))

def run():
 p=argparse.ArgumentParser()
 p.add_argument("--apply",action="store_true")
 a=p.parse_args()
 query="""SELECT r.language_code,r.card_id,r.variant_id,r.evidence::text,
      COALESCE(v.value::text,'{}')
 FROM price_reference_candidates r
 LEFT JOIN catalog_cards_mirror c ON c.language_code=r.language_code AND c.card_id=r.card_id
 LEFT JOIN LATERAL jsonb_array_elements(c.variants) v(value) ON v.value->>'id'=r.variant_id
 ORDER BY r.language_code,r.card_id,r.variant_id"""
 command=["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",query]
 result=subprocess.run(command,capture_output=True,text=True,check=True)
 rows=[]
 for line in result.stdout.splitlines():
  fields=line.split("\t",4)
  if len(fields)!=5:continue
  lang,cid,vid,evidence_str,variant_str=fields
  evidence=json.loads(evidence_str); variant=json.loads(variant_str)
  status,reasons=classify(variant,evidence,lang)
  rows.append(dict(language_code=lang,card_id=cid,variant_id=vid,
                   status=status,reasons=reasons))
 counts=collections.Counter(r["status"] for r in rows)
 print("variants",len(rows),"status",dict(counts))
 print("blockers",dict(collections.Counter(reason for r in rows for reason in r["reasons"])))
 if not a.apply:return
 payload=json.dumps(rows,ensure_ascii=False).replace("'","''")
 sql=f"""WITH incoming AS (SELECT jsonb_array_elements('{payload}'::jsonb) AS x)
 UPDATE price_reference_candidates p
 SET verification_status=incoming.x->>'status',
     evidence=jsonb_set(p.evidence,'{{verification}}',
       jsonb_build_object('reasons',incoming.x->'reasons','evaluated_at',now()),true)
 FROM incoming
 WHERE p.language_code=incoming.x->>'language_code' AND p.card_id=incoming.x->>'card_id'
   AND p.variant_id=incoming.x->>'variant_id'"""
 subprocess.run(["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],input=sql,text=True,check=True,stdout=subprocess.DEVNULL)
 print("saved",len(rows))
if __name__=="__main__":run()
