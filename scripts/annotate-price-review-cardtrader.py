#!/usr/bin/env python3
"""Persist exact CardTrader stock findings in the unresolved admin cases."""
import argparse,json,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--report",type=Path,required=True)
 p.add_argument("--apply",action="store_true")
 args=p.parse_args()
 entries=json.loads(args.report.read_text())["cases"]
 print("cases",len(entries),"apply",args.apply)
 if not args.apply:return
 payload=json.dumps(entries,ensure_ascii=False).replace("'","''")
 query=f"""WITH cases AS(SELECT jsonb_array_elements('{payload}'::jsonb) x),
 merge AS(
 SELECT q.language_code,q.card_id,q.variant_id,
 COALESCE((SELECT jsonb_agg(z) FROM jsonb_array_elements(q.candidates) z
 WHERE z->>'match_type'<>'CARDTRADER_EXACT_STOCK_AUDIT'),'[]'::jsonb) ||
 jsonb_build_array(jsonb_build_object('match_type','CARDTRADER_EXACT_STOCK_AUDIT',
 'status',cases.x->>'status','tcgplayer_id',cases.x->'tcgplayer_id',
 'cardtrader_blueprint_id',cases.x->'blueprint_id',
 'eligible_nm_stock',cases.x->'eligible_en_nm_stock',
 'lowest_asking_eur',cases.x->'min_en_nm_asking_eur')) updated_candidates
 FROM price_review_cases q JOIN cases
 ON q.language_code=cases.x->>'language' AND q.card_id=cases.x->>'card_id'
 AND q.variant_id=cases.x->>'variant_id')
 UPDATE price_review_cases q SET candidates=merge.updated_candidates FROM merge
 WHERE q.language_code=merge.language_code AND q.card_id=merge.card_id
 AND q.variant_id=merge.variant_id;"""
 subprocess.run(["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],input=query,text=True,check=True,stdout=subprocess.DEVNULL)
 print("saved",len(entries))
if __name__=="__main__":main()
