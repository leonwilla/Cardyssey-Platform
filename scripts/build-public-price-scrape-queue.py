#!/usr/bin/env python3
"""Create a conservative queue only from preidentified TCGplayer product IDs."""
import argparse,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--output",type=Path,required=True)
a=p.parse_args()
sql="""SELECT r.language_code,r.card_id,r.variant_id,r.candidates::text
 FROM price_review_cases r
 LEFT JOIN tcg_price_cache p ON p.language_code=r.language_code
 AND p.card_id=r.card_id AND p.variant_id=r.variant_id
 WHERE (p.resolution_status IS NULL OR p.resolution_status<>'PRICE_FOUND')
 AND r.candidates::text LIKE '%EXACT_VARIANT_EXTERNAL_ID_NOT_PRICE_PROOF%'"""
cmd=["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql]
data=subprocess.run(cmd,check=True,text=True,capture_output=True).stdout
records=[]
for line in data.splitlines():
 try:
  language,card_id,variant_id,candidates=line.split("\t",3)
  products=[x for x in json.loads(candidates) if x.get("match_type")=="EXACT_VARIANT_EXTERNAL_ID_NOT_PRICE_PROOF" and x.get("provider")=="tcgplayer"]
  for item in products:
   n=str(item.get("provider_id") or "")
   if re.fullmatch(r"[0-9]{1,10}",n):
    records.append(dict(language=language,card_id=card_id,variant_id=variant_id,url="https://www.tcgplayer.com/product/"+n))
 except (ValueError,TypeError):continue
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in records))
print("queued",len(records))
