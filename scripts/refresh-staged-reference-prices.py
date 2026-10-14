#!/usr/bin/env python3
"""Weekly low-volume refresh of existing Cardyssey reference quotes.

Only 20 previously staged EN card identities. References NEVER become verified
variant prices, and German comparator quotes remain labeled as English.
"""
import argparse,collections,json,subprocess,time,datetime
from pathlib import Path
import requests

def db(sql):
 return subprocess.check_output(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-c",sql],text=True)

def sqlquote(value):
 return "'"+str(value).replace("'","''")+"'"

def quote_locale(payload):
 body=(payload.get("data") or {})
 ix=body.get("index") or {}
 row=next((v for v in (ix.get("by_locale") or []) if v.get("locale")=="en" and isinstance(v.get("eur"),(int,float)) and v["eur"]>0),None)
 if row is None:return None
 asof=row.get("as_of") or ix.get("as_of")
 try:datetime.date.fromisoformat(asof)
 except (TypeError,ValueError):return None
 return dict(price_eur=row["eur"],as_of=asof,
             evidence={"index":ix,"quotes":body.get("quotes") or [],
                       "meta":payload.get("meta") or {},
                       "warning":"English card-level reference only; printing, condition and edition NOT verified"})

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--apply",action="store_true")
 p.add_argument("--limit",type=int)
 p.add_argument("--report",type=Path,default=Path("/tmp/cardyssey-reference-weekly.json"))
 a=p.parse_args()
 env=Path("/home/tv/cardshop/platform/.env").read_text()
 key=next((x.split("=",1)[1].strip().strip("'").strip('"') for x in env.splitlines() if x.startswith("PTCG_API_KEY=")),"")
 if not key:print("API_KEY_MISSING, existing references retained");return
 ids=db("""SELECT DISTINCT r.card_id FROM price_reference_candidates r
 WHERE r.language_code='en' AND r.provider='POKEMONTCGAPI_REFERENCE'
 ORDER BY r.card_id""").splitlines()
 if a.limit is not None:ids=ids[:max(0,a.limit)]
 statuses=collections.Counter();updates=[]
 for cid in ids:
  try:
   time.sleep(0.4)
   resp=requests.get("https://api.pokemontcgapi.com/v1/cards/"+cid+"/prices",
       headers={"X-Api-Key":key,"User-Agent":"Cardyssey/1.0 (https://cardyssey.de)"},
       timeout=15)
   if resp.status_code==429:
    time.sleep(2)
    resp=requests.get("https://api.pokemontcgapi.com/v1/cards/"+cid+"/prices",
        headers={"X-Api-Key":key,"User-Agent":"Cardyssey/1.0 (https://cardyssey.de)"},timeout=15)
   if resp.status_code!=200:
    statuses["HTTP_"+str(resp.status_code)]+=1
    continue
   picked=quote_locale(resp.json())
   if picked is None:
    statuses["NO_EN_REFERENCE"]+=1;continue
   updates.append(dict(card_id=cid,**picked))
   statuses["EN_REFERENCE_AVAILABLE"]+=1
  except (requests.RequestException,ValueError) as exc:
   statuses[type(exc).__name__]+=1
 report={"source":"POKEMONTCGAPI_REFERENCE","looked_up":len(ids),
         "candidate_updates":len(updates),"status_counts":dict(statuses),"applied":False}
 if a.apply and updates:
  data=sqlquote(json.dumps(updates,ensure_ascii=False))
  sql=f"""WITH incoming AS(SELECT jsonb_array_elements({data}::jsonb) AS x)
  UPDATE price_reference_candidates p SET
   price_eur=(incoming.x->>'price_eur')::numeric,
   evidence=incoming.x->'evidence',
   observed_at=(incoming.x->>'as_of')::date::timestamptz,
   verification_status='UNVERIFIED_PRINT'
  FROM incoming
  WHERE p.language_code='en' AND p.card_id=incoming.x->>'card_id'
    AND p.provider='POKEMONTCGAPI_REFERENCE'
    AND EXISTS(SELECT 1 FROM tcg_price_cache c WHERE c.card_id=p.card_id
      AND c.language_code=p.language_code AND c.variant_id=p.variant_id
      AND c.resolution_status IN ('NO_PRICE','NO_PUBLIC_PRICE','PROVIDER_ERROR'));"""
  print("updated_rows",db(sql).strip())
  report["applied"]=True
 a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
