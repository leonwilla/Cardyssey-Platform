#!/usr/bin/env python3
"""Exact Korean AR Near Mint singles from True Unicorn; preview by default."""
import argparse,importlib.util,json,re,time
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
s=importlib.util.spec_from_file_location("ctko",Path(__file__).with_name("resolve-cardtrader-ko-nm-prices.py"));ct=importlib.util.module_from_spec(s);s.loader.exec_module(ct)
ko=ct.ko;retail=ko.retail
SOURCE="WEB_UNICORN_KO";HOST="https://trueunicorntcg.com"
TITLE=re.compile(r"(.+) (\d+)/(\d+) - Korean Art Rare Holo - (SV\d+[A-Za-z]*): (.+) - Near Mint")
def detail_agrees(product,detail):
 if any(product.get(k)!=detail.get(k) for k in ("id","handle","title","product_type")):return False
 tags=detail.get("tags",[])
 if isinstance(tags,str):tags=[x.strip() for x in tags.split(",")]
 if set(tags)!=set(product.get("tags",[])):return False
 pv=product.get("variants",[]);dv=detail.get("variants",[])
 if len(pv)!=1 or len(dv)!=1:return False
 if any(pv[0].get(k)!=dv[0].get(k) for k in ("id","product_id","title","sku","price")):return False
 return dv[0].get("price_currency")=="USD" and (dv[0].get("quantity_rule") or {}).get("min")==1 and (dv[0].get("quantity_rule") or {}).get("increment")==1

def match_offer(row,product,ajax,names):
 m=TITLE.fullmatch(product.get("title",""))
 if not m or row.get("language_code")!="ko" or row.get("identity_count")!=1 or not row["card_id"].startswith("official_ko_"):return None,"identity"
 name,num,total,code,setname=m.groups()
 if ko.normalize(row["set_id"])!=ko.normalize(code) or int(row["local_id"])!=int(num) or row["official_count"]!=int(total) or row["rarity"]!="AR":return None,"printing"
 if re.search(r"reverse|master.?ball|pok[eé].?ball|stamp|signed|graded|jumbo|bundle|lot",name,re.I):return None,"special"
 hits=[n for n in names if re.search(r"(?<![A-Za-z0-9])"+re.escape(n["9"])+r"(?![A-Za-z0-9])",name,re.I)]
 if not hits:return None,"species"
 hits=[n for n in hits if len(n["9"])==max(len(x["9"]) for x in hits)]
 if len(hits)!=1 or ko.normalize(hits[0]["6"])!=ko.normalize(row["german_species"]) or ko.normalize(hits[0]["3"]) not in ko.normalize(row["native_name"]):return None,"species"
 if product.get("product_type")!="Raw Single" or not {"Korean","Near Mint","Art Rare","Holo",num+"/"+total,code}.issubset(set(product.get("tags",[]))):return None,"tags"
 if ajax.get("price_varies") is not False or ajax.get("requires_selling_plan") is not False:return None,"bundle_or_subscription"
 if product.get("id")!=ajax.get("id") or product.get("handle")!=ajax.get("handle") or product["title"]!=ajax.get("title"):return None,"product"
 variants=product.get("variants",[]);actual=ajax.get("variants",[])
 if len(variants)!=1 or len(actual)!=1:return None,"variant"
 v,a=variants[0],actual[0]
 if v.get("title")!="Near Mint" or a.get("title")!="Near Mint" or v.get("id")!=a.get("id") or not v.get("sku") or v["sku"]!=a.get("sku"):return None,"condition"
 if v.get("available") is not True or a.get("available") is not True or ajax.get("available") is not True:return None,"stock"
 amount=retail.positive_decimal(v.get("price"))
 if amount is None or type(a.get("price")) is not int or amount*100!=a["price"]:return None,"price"
 return dict(source=SOURCE,currency="USD",amount=str(amount),url=HOST+"/products/"+product["handle"],
             title=product["title"],product_id=product["id"],offer_variant_id=v["id"],sku=v["sku"],
             condition="Near Mint",language="ko",rarity="AR",printing="ordinary",
             identity_method="unique-ko-set-number-denominator-rarity/independent-species/explicit-Korean-NM",
             basis_description="in-stock single-card retail asking price"),None
def collection():
 products=[]
 for page in range(1,21):
  batch=retail.get_json(HOST+"/products.json?limit=250&page="+str(page))["products"];products+=batch
  if len(batch)<250:return products
  time.sleep(.5)
 raise ValueError("pagination limit")
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");p.add_argument("--missing-only",action="store_true");p.add_argument("--report",type=Path);args=p.parse_args()
 names=ko.species_names();rows=ct.extra.load_targets(SOURCE)+ct.pinned.load_targets(ko,SOURCE,names)
 if args.missing_only:rows=ct.missing.filter_targets(rows,retail)
 products=collection();updates=[];rejected={};observed=datetime.now(timezone.utc).isoformat()
 if retail.get_json(HOST+"/cart.js").get("currency")!="USD":raise ValueError("currency mismatch")
 fxdata=retail.get_json("https://api.frankfurter.dev/v2/rate/USD/EUR");fx=retail.positive_decimal(fxdata.get("rate"))
 if fx is None or not fxdata.get("date"):raise ValueError("FX unavailable")
 for product in products:
  m=TITLE.fullmatch(product.get("title",""))
  if not m:continue
  candidates=[r for r in rows if ko.normalize(r["set_id"])==ko.normalize(m[4]) and int(r["local_id"])==int(m[2])]
  if not candidates:continue
  handle=product.get("handle","")
  if not re.fullmatch(r"[a-z0-9-]+",handle):continue
  ajax=retail.get_json(HOST+"/products/"+handle+".js")
  detail=retail.get_json(HOST+"/products/"+handle+".json")["product"]
  if not detail_agrees(product,detail):raise ValueError("product price or identity changed during observation")
  for row in candidates:
   offer,reason=match_offer(row,product,ajax,names)
   if reason:rejected[reason]=rejected.get(reason,0)+1;continue
   if Decimal(offer["amount"])*fx>100:rejected["high_asking_price_review"]=rejected.get("high_asking_price_review",0)+1;continue
   offer.update(fx_to_eur=str(fx),fx_date=fxdata["date"])
   updates.append(dict(row=row,offer=offer,observed_at=observed,base_eur=str((Decimal(offer["amount"])*fx/retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP))))
 if len({u["row"]["card_id"] for u in updates})!=len(updates):raise ValueError("ambiguous offers")
 report=dict(complete=True,candidates=len(rows),retail_products=len(products),matched=len(updates),rejected=rejected,updates=updates,
             applied=ko.apply_updates(updates,SOURCE,missing_only=args.missing_only) if args.apply else dict(variants=0,prices=0,history=0))
 if args.report:ct.write_report(args.report,report)
 print(json.dumps({k:v for k,v in report.items() if k!="updates"}),flush=True)
if __name__=="__main__":main()
