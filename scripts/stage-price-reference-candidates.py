#!/usr/bin/env python3
"""Stage API-derived reference quotes, never overwrite verified price cache."""
import argparse,json,subprocess
from pathlib import Path

def sql_literal(value):
 return "'"+str(value).replace("'","''")+"'"

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--report",type=Path,required=True)
 parser.add_argument("--apply",action="store_true")
 args=parser.parse_args()
 payload=json.loads(args.report.read_text())
 rows=[]
 for item in payload["variants"]:
  if item["language"]!="en" or not isinstance(item.get("index_eur"),(int,float)) or item["index_eur"]<=0:continue
  response=payload["cards"].get(item["card_id"],{}).get("data",{})
  data=response.get("data") or {}
  quotes=data.get("quotes") or []
  meta=response.get("meta") or {}
  rows.append(dict(language_code="en",card_id=item["card_id"],variant_id=item["variant_id"],
   provider="POKEMONTCGAPI_REFERENCE",price_eur=item["index_eur"],
   evidence=dict(index=(data.get("index") or {}),quotes=quotes,meta=meta,
    warning="Card-level English reference, physical printing and condition NOT verified",
    audit_status=item["audit_status"]),
   verification_status="UNVERIFIED_PRINT"))
 print("reference_candidates",len(rows),"unique_cards",len({r["card_id"] for r in rows}),"apply",args.apply,flush=True)
 if not args.apply:return
 payload_json=json.dumps(rows,ensure_ascii=False)
 query=f"""WITH input AS(SELECT jsonb_array_elements({sql_literal(payload_json)}::jsonb) AS x)
 INSERT INTO price_reference_candidates(language_code,card_id,variant_id,provider,price_eur,evidence,verification_status)
 SELECT x->>'language_code',x->>'card_id',x->>'variant_id',x->>'provider',(x->>'price_eur')::numeric,
 x->'evidence',x->>'verification_status' FROM input
 ON CONFLICT(language_code,card_id,variant_id,provider) DO UPDATE SET price_eur=EXCLUDED.price_eur,
 evidence=EXCLUDED.evidence,verification_status=EXCLUDED.verification_status,observed_at=NOW()"""
 subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1"],
 input=query,text=True,check=True,stdout=subprocess.DEVNULL)
 print("saved",len(rows))
if __name__=="__main__":main()
