#!/usr/bin/env python3
"""Stage verified-set but ambiguous Cardmarket matches as a focused admin review batch."""
import argparse,json,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--triage",type=Path,required=True)
 p.add_argument("--apply",action="store_true")
 a=p.parse_args()
 rows=[x for x in json.loads(a.triage.read_text())["cases"] if x["next_action"]=="VERIFY_CARDMARKET_PRINT_IDENTITY"]
 payload=json.dumps(rows,ensure_ascii=False)
 sql="""WITH selected AS (SELECT jsonb_array_elements('"""+payload.replace("'","''")+"""'::jsonb) x)
 UPDATE price_review_cases r SET
   search_status='CARDMARKET_PRINT_REVIEW',
   candidates=COALESCE((SELECT jsonb_agg(v) FROM jsonb_array_elements(r.candidates) v
      WHERE v->>'match_type'<>'CARDMARKET_PRINT_REVIEW'),'[]'::jsonb)
    ||jsonb_build_array(jsonb_build_object('match_type','CARDMARKET_PRINT_REVIEW',
      'status','MANUAL_PRINT_IDENTITY_REQUIRED','provider','CARDMARKET',
      'instruction','Set match exists; confirm exact language, number, edition, foil and stamp before assigning product ID.'))
 FROM selected
 WHERE r.language_code=selected.x->>'language'
 AND r.card_id=selected.x->>'card_id' AND r.variant_id=selected.x->>'variant_id'
 AND EXISTS (SELECT 1 FROM tcg_price_cache c WHERE c.language_code=r.language_code
  AND c.card_id=r.card_id AND c.variant_id=r.variant_id AND c.resolution_status<>'PRICE_FOUND')
 RETURNING r.language_code,r.card_id,r.variant_id;"""
 if a.apply:
  cmd=["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","|","-c",sql]
  results=subprocess.run(cmd,check=True,capture_output=True,text=True).stdout
  print("staged",len([r for r in results.splitlines() if r.count("|")==2]))
 else:print("preview",len(rows))
if __name__=="__main__":main()
