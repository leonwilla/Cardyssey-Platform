#!/usr/bin/env python3
"""Exact in-stock Korean NM ordinary-print singles from BlackRoseSkulls.
Public feeds only; require independent official species and consistent product data.
"""
import argparse,html,json,re,time
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
import importlib.util
s=importlib.util.spec_from_file_location("ct",Path(__file__).with_name("resolve-cardtrader-ko-nm-prices.py"));ct=importlib.util.module_from_spec(s);s.loader.exec_module(ct)
ko=ct.ko;retail=ko.retail
HOST="https://www.blackroseskulls.com";SOURCE="WEB_BLACKROSE_KO"
RARITIES={"Common":"C","Uncommon":"U","Rare":"R","Holo Rare":"R","Double Rare":"RR","Ultra Rare":"SR","Illustration Rare":"AR","Art Rare":"AR","Special Illustration Rare":"SAR","Hyper Rare":"UR"}
def fields(product):
 result=defaultdict(list)
 for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>",product.get("body_html",""),re.S):
  plain=html.unescape(re.sub(r"<[^>]+>","",paragraph)).strip()
  if ":" in plain:
   k,v=plain.split(":",1);result[k.strip()].append(v.strip())
 return result
def identity(product):
 title=product.get("title","")
 if "Korean" not in title or not re.search(r"\bNM\b",title) or re.search(r"reverse|master.?ball|pok[eé].?ball|stamp|graded|PSA|BGS|CGC|bundle|lot|jumbo|signed|edition",title,re.I):return None
 nums=re.findall(r"(?<!\d)(\d+)/(\d+)(?!\d)",title)
 codes=re.findall(r"\b((?:SV|SM|S|XY|M)\d+[A-Za-z]*)\b",title,re.I)
 if len(nums)!=1 or len(codes)!=1:return None
 f=fields(product)
 if f["Language"]!=["Korean"] or f["Condition"]!=["Near Mint"] or len(f["Rarity"])!=1 or f["Rarity"][0] not in RARITIES:return None
 if f["Card Number"]!=["/".join(nums[0])] or len(f["Set"])!=1 or not re.match(re.escape(codes[0])+r"(?:\s|$)",f["Set"][0],re.I):return None
 if len(f["Finish"])!=1:return None
 rarity=RARITIES[f["Rarity"][0]]
 if (rarity in ("C","U") and f["Finish"][0] not in ("Regular","Non-Holo")) or (rarity not in ("C","U") and f["Finish"][0] not in ("Holo","Holofoil")):return None
 if product.get("product_type")!="Collectible Trading Cards - Pokemon":return None
 return dict(code=codes[0],number=int(nums[0][0]),total=int(nums[0][1]),rarity=rarity,finish=f["Finish"][0])
def reject_catalog(row,product,names):
 i=identity(product)
 if i is None or row.get("language_code")!="ko" or row.get("identity_count")!=1 or not row.get("card_id","").startswith("official_ko_"):return "identity"
 if ko.normalize(i["code"])!=ko.normalize(row["set_id"]) or i["number"]!=int(row["local_id"]) or i["total"]!=row["official_count"] or i["rarity"]!=row["rarity"]:return "set_number_denominator_rarity"
 hits=[n for n in names if re.search(r"(?<![A-Za-z0-9])"+re.escape(n["9"])+r"(?![A-Za-z0-9])",product["title"],re.I)]
 if not hits:return "species"
 hits=[n for n in hits if len(n["9"])==max(len(x["9"]) for x in hits)]
 if len(hits)!=1 or ko.normalize(hits[0]["6"])!=ko.normalize(row["german_species"]) or ko.normalize(hits[0]["3"]) not in ko.normalize(row["native_name"]):return "species"
 return None
def match_offer(row,feed,detail,ajax,names,currency):
 for p in (feed,detail):
  reason=reject_catalog(row,p,names)
  if reason:return None,reason
 if currency!="GBP":return None,"currency"
 if any(p.get("id")!=feed.get("id") or p.get("title")!=feed["title"] or p.get("handle")!=feed["handle"] for p in (detail,ajax)):return None,"product_identity"
 if fields(feed)!=fields(detail):return None,"body_changed"
 handle=feed["handle"]
 if not re.fullmatch(r"[a-z0-9-]+",handle) or ajax.get("url")!="/products/"+handle:return None,"url"
 for p in (feed,detail):
  options=p.get("options",[])
  if len(options)!=1 or options[0].get("name")!="Title":return None,"options"
 variants=[p.get("variants",[]) for p in (feed,detail,ajax)]
 if any(len(v)!=1 for v in variants):return None,"variant"
 fv,dv,av=[v[0] for v in variants]
 if any(v.get("title")!="Default Title" or v.get("option1")!="Default Title" or v.get("option2") is not None or v.get("option3") is not None for v in (fv,dv,av)):return None,"variant"
 if fv.get("available") is not True or av.get("available") is not True or ajax.get("available") is not True:return None,"stock"
 if type(fv.get("id")) is not int or not fv.get("sku") or any(v.get("id")!=fv["id"] or v.get("sku")!=fv["sku"] for v in (dv,av)):return None,"offer_identity"
 amount=retail.positive_decimal(fv.get("price"))
 if amount is None or dv.get("price_currency")!="GBP" or amount!=retail.positive_decimal(dv.get("price")) or type(av.get("price")) is not int or amount*100!=av["price"]:return None,"price"
 rule=av.get("quantity_rule") or {}
 if rule.get("min")!=1 or rule.get("increment")!=1 or av.get("requires_selling_plan") or av.get("selling_plan_allocations") or av.get("quantity_price_breaks") or ajax.get("price_varies") is not False:return None,"bundle"
 return dict(source=SOURCE,currency="GBP",amount=str(amount),title=feed["title"],url=HOST+"/products/"+handle,
             product_id=feed["id"],offer_variant_id=fv["id"],sku=fv["sku"],condition="Near Mint",language="ko",
             rarity=row["rarity"],printing="ordinary",basis_description="in-stock single-card retail asking price",
             identity_method="explicit-Korean-NM/exact-set-number-denominator-rarity/independent-official-species"),None
def collection():
 products=[];seen=set()
 for page in range(1,21):
  batch=retail.get_json(HOST+"/collections/trading-card-games-tcg/products.json?limit=250&page="+str(page))["products"]
  for p in batch:
   if p.get("id") in seen:raise ValueError("repeated pagination")
   seen.add(p["id"])
  products+=batch
  if len(batch)<250:return products
  time.sleep(.5)
 raise ValueError("pagination limit")
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");p.add_argument("--missing-only",action="store_true");p.add_argument("--report",type=Path,required=True);args=p.parse_args()
 names=ko.species_names();rows=ct.extra.load_targets(SOURCE)+ct.pinned.load_targets(ko,SOURCE,names)
 if args.missing_only:rows=ct.missing.filter_targets(rows,retail)
 by_key=defaultdict(list)
 for row in rows:by_key[(ko.normalize(row["set_id"]),int(row["local_id"]))].append(row)
 products=collection();currency=retail.get_json(HOST+"/cart.js").get("currency")
 if currency!="GBP":raise ValueError("currency unavailable")
 fxdata=retail.get_json("https://api.frankfurter.dev/v2/rate/GBP/EUR");fx=retail.positive_decimal(fxdata.get("rate"))
 if fx is None or not fxdata.get("date"):raise ValueError("FX unavailable")
 updates={};rejected=Counter();errors=[];observed=datetime.now(timezone.utc).isoformat();checked=0
 for product in products:
  i=identity(product)
  if i is None:continue
  targets=[row for row in by_key[(ko.normalize(i["code"]),i["number"])] if reject_catalog(row,product,names) is None]
  if not targets:rejected["no_eligible_missing_target"]+=1;continue
  try:
   handle=product["handle"]
   if not re.fullmatch(r"[a-z0-9-]+",handle):raise ValueError("invalid handle")
   detail=retail.get_json(HOST+"/products/"+handle+".json")["product"];ajax=retail.get_json(HOST+"/products/"+handle+".js")
   for row in targets:
    offer,reason=match_offer(row,product,detail,ajax,names,currency)
    if reason:rejected[reason]+=1;continue
    if Decimal(offer["amount"])*fx>100:rejected["high_asking_price_review"]+=1;continue
    offer.update(fx_to_eur=str(fx),fx_date=fxdata["date"])
    u=dict(row=row,offer=offer,observed_at=observed,base_eur=str((Decimal(offer["amount"])*fx/retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP)))
    old=updates.get(row["card_id"])
    if old is None or Decimal(offer["amount"])<Decimal(old["offer"]["amount"]):updates[row["card_id"]]=u
  except Exception as e:errors.append(dict(product_id=product["id"],error=type(e).__name__))
  checked+=1
  if checked%20==0:print(json.dumps(dict(checked=checked,matched=len(updates))),flush=True)
  ct.write_report(args.report,dict(complete=False,updates=list(updates.values()),errors=errors))
 report=dict(complete=True,candidates=len(rows),products=len(products),checked=checked,matched=len(updates),rejected=dict(rejected),errors=errors,updates=list(updates.values()),
             applied=ko.apply_updates(list(updates.values()),SOURCE,missing_only=args.missing_only) if args.apply and not errors else dict(variants=0,prices=0,history=0))
 ct.write_report(args.report,report);print(json.dumps({k:v for k,v in report.items() if k!="updates"}),flush=True)
 if errors:raise SystemExit(1)
if __name__=="__main__":main()
