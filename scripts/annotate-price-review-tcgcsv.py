#!/usr/bin/env python3
"""Annotate the admin review queue with independently audited exact product feed results."""
import argparse,json,subprocess
from pathlib import Path

def sqlquote(v): return "'"+v.replace("'","''")+"'"
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--report",type=Path,required=True)
 p.add_argument("--apply",action="store_true")
 args=p.parse_args()
 rows=json.loads(args.report.read_text()).get("results",[])
 evidence=[]
 for x in rows:
  if x.get("status") not in ("EXACT_PRODUCT_HAS_NO_PUBLIC_MARKET_PRICE","PRODUCT_NOT_IN_GROUP","EXACT_PRODUCT_MARKET_PRICE_AVAILABLE"):continue
  evidence.append(dict(language=x["language"],card_id=x["card_id"],variant_id=x["variant_id"],product_id=x.get("product_id"),status=x["status"]))
 print("diagnostics",len(evidence),"apply",args.apply)
 if not args.apply:return
 js=sqlquote(json.dumps(evidence))
 sql=f"""WITH audits AS (SELECT jsonb_array_elements({js}::jsonb) a),
 refined AS (SELECT p.language_code,p.card_id,p.variant_id,
 COALESCE((SELECT jsonb_agg(v) FROM jsonb_array_elements(p.candidates) v
     WHERE v->>'match_type'<>'EXACT_TCGCSV_AUDIT'),'[]'::jsonb)
 || jsonb_build_array(jsonb_build_object('match_type','EXACT_TCGCSV_AUDIT',
      'provider','TCGCSV','provider_id',audits.a->'product_id',
      'status',audits.a->>'status')) AS new_candidates
 FROM price_review_cases p JOIN audits ON
 p.language_code=audits.a->>'language' AND p.card_id=audits.a->>'card_id'
 AND p.variant_id=audits.a->>'variant_id')
 UPDATE price_review_cases p SET candidates=refined.new_candidates
 FROM refined WHERE p.language_code=refined.language_code
 AND p.card_id=refined.card_id AND p.variant_id=refined.variant_id;"""
 subprocess.run(["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],input=sql,text=True,check=True,stdout=subprocess.DEVNULL)
 print("annotated",len(evidence))
if __name__=="__main__":main()
