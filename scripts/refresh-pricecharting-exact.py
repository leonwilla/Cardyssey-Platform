#!/usr/bin/env python3
"""Refresh *explicitly verified* PriceCharting Pokemon variant IDs.

PriceCharting official API is paid. No credentials => report skip (never
scrape bulk public pages). Ungraded is interpreted as NM baseline according
to Cardyssey policy, NOT a PriceCharting condition guarantee.
"""
import argparse,csv,json,os,re,subprocess,urllib.parse,urllib.request
from decimal import Decimal,InvalidOperation
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
MAPPING=ROOT/"config/pricecharting-exact-variants.csv"
FIELDS=("language","card_id","variant_id","pricecharting_id","identity_verified","evidence_url")
def db(sql):
 return subprocess.run(["docker","exec","cardyssey-db","psql","-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey","-At","-c",sql],capture_output=True,text=True,check=True).stdout.strip()
def q(value):return "'"+str(value).replace("'","''")+"'"
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Cardyssey/0.3 exact-pricecharting"})
 with urllib.request.urlopen(req,timeout=15) as res:return json.load(res)
def parse_ungraded(payload):
 try:
  amount=Decimal(str(payload.get("loose-price")))/Decimal(100)
  if not amount.is_finite() or not Decimal("0.01")<=amount<=Decimal("1000000"):return None
  return amount
 except (InvalidOperation,TypeError,ValueError):return None
def product_matches(row,payload):
 return (payload.get("status")=="success" and str(payload.get("id"))==row["pricecharting_id"]
         and "pokemon" in str(payload.get("console-name") or "").lower())
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--apply",action="store_true")
 p.add_argument("--report",type=Path,default=Path("/tmp/cardyssey-pricecharting-exact-report.json"))
 p.add_argument("--limit",type=int,default=1000)
 args=p.parse_args()
 records=list(csv.DictReader(MAPPING.open())) if MAPPING.exists() else []
 token=os.environ.get("PRICECHARTING_API_KEY","").strip()
 report={"provider":"PRICECHARTING_UNGRADED","checked":0,"written":0,"skipped":0,"errors":[],"state":"ready"}
 if not token:
  report["state"]="NO_PAID_API_KEY"
 elif not records:
  report["state"]="NO_VERIFIED_PRODUCT_IDS"
 else:
  try:
   fx=Decimal(str(fetch("https://api.frankfurter.dev/v2/rate/USD/EUR")["rate"]))
   if not Decimal("0.1")<=fx<=Decimal("2"):raise ValueError("invalid conversion rate")
  except Exception as exc:
   report["state"]="NO_USD_EUR_FX"
   report["errors"].append(type(exc).__name__)
  if report["state"]=="ready":
   for row in records[:max(0,args.limit)]:
    report["checked"]+=1
    try:
     if not all(row.get(k) for k in FIELDS) or row["identity_verified"].lower()!="true" or row["language"] not in ("de","en","ja","ko","zh-cn","zh-tw"):
      report["skipped"]+=1;continue
     if not re.fullmatch(r"[0-9]{1,12}",row["pricecharting_id"]) or not row["evidence_url"].startswith("https://www.pricecharting.com/"):
      report["skipped"]+=1;continue
     exists=db("SELECT COUNT(*) FROM catalog_cards_mirror c CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value) WHERE c.card_id="+q(row["card_id"])+" AND c.language_code="+q(row["language"])+" AND v.value->>'id'="+q(row["variant_id"]))
     if exists!="1":report["skipped"]+=1;continue
     payload=fetch("https://www.pricecharting.com/api/product?"+urllib.parse.urlencode({"t":token,"id":row["pricecharting_id"]}))
     if not product_matches(row,payload):report["skipped"]+=1;continue
     usd=parse_ungraded(payload)
     if usd is None:report["skipped"]+=1;continue
     eur=(usd*fx).quantize(Decimal("0.0001"))
     if not args.apply:continue
     detail=("PriceCharting exact product "+row["pricecharting_id"]+
      "; Ungraded USD="+str(usd)+"; interpreted as NM baseline (Cardyssey assumption); "+
      "product evidence "+row["evidence_url"])
     sql="""WITH written AS (
      INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
      SELECT {cid},{lang},{vid},COALESCE(v.value->>'legacyVariant','NORMAL'),'PRICECHARTING_UNGRADED', {eur},NOW(),'PRICE_FOUND',{detail},NOW()+INTERVAL '7 days'
      FROM catalog_cards_mirror c CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
      WHERE c.card_id={cid} AND c.language_code={lang} AND v.value->>'id'={vid}
      ON CONFLICT(card_id,language_code,variant_id) DO UPDATE
      SET source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,updated_at=NOW(),resolution_status='PRICE_FOUND',
          failure_detail=EXCLUDED.failure_detail,next_attempt_at=EXCLUDED.next_attempt_at
      WHERE tcg_price_cache.resolution_status<>'PRICE_FOUND' OR tcg_price_cache.source='PRICECHARTING_UNGRADED'
      RETURNING card_id,language_code,variant_id,base_eur)
      INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
      SELECT card_id,language_code,variant_id,'PRICECHARTING_UNGRADED',base_eur,NOW() FROM written
      RETURNING card_id;""".format(cid=q(row["card_id"]),lang=q(row["language"]),vid=q(row["variant_id"]),eur=eur,detail=q(detail))
     output=db(sql)
     if output:report["written"]+=1
    except Exception as exc:
     report["errors"].append({"card_id":row.get("card_id"),"error":type(exc).__name__})
 report["finished_at"]=datetime.now(timezone.utc).isoformat()
 args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
