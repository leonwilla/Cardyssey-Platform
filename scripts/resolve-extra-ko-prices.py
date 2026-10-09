#!/usr/bin/env python3
"""Exact Korean retail singles from Level Up Games and ShinyCardboard4U.

Preview by default. Public stock, NM condition, language, set/number/denominator,
species and currency must agree. Special prints and ambiguous rare foils excluded.
"""
import argparse
import html
import importlib.util
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
spec=importlib.util.spec_from_file_location("ko",Path(__file__).with_name("resolve-uturi-ko-prices.py"))
ko=importlib.util.module_from_spec(spec);spec.loader.exec_module(ko)
SHOPS={
 "level":dict(host="https://levelupgames.shop",collection="korean-pokemon",source="WEB_LEVELUP_KO",currency="USD"),
 "shiny":dict(host="https://shinycardboard4u.com",collection="all-korean-cards",source="WEB_SHINY_KO",currency="GBP"),
}
SETS={
 "151":("sv2a",165), "Fusion Arts":("s8",100), "Eevee Heroes":("s6a",69),
 "Terastal Festival ex":("sv8a",187), "Glory of Team Rocket":("sv10",98),
 "Crimson Haze":("sv5a",66), "Heat Wave Arena":("sv9a",63),
 "Battle Partners":("sv9",100), "Super Electric Breaker":("sv8",106),
 "Paradise Dragona":("sv7a",64), "Stellar Miracle":("sv7",102),
 "Mask of Change":("sv6",101), "Cyber Judge":("sv5m",71),
 "Wild Force":("sv5k",71), "Night Wanderer":("sv6a",64),
 "Scarlet ex":("sv1s",78), "Raging Surf":("sv3a",62),
 "Rapid Strike Master":("s5r",70), "Towering Perfection":("s7d",67),
 "Blue Sky Stream":("s7r",67), "Paradigm Trigger":("s12",98),
 "Incandescent Arcana":("s11a",68),
}
REGULAR_RARITIES=frozenset(("C","U","RR","RRR","AR","SAR","SR","UR","HR","S","SSR"))
RARITY_LABELS={"Common":"C","Uncommon":"U","Rare":"R","Double Rare":"RR","Triple Rare":"RRR",
               "Art Rare":"AR","Illustration Rare":"AR","Special Art Rare":"SAR",
               "Super Rare":"SR","Ultra Rare":"UR"}
def identity(title,shop):
 if shop=="level":
  m=re.fullmatch(r"(.+) (\d+)/(\d+) - (.+) \(Korean\)",title)
  if not m or m[4] not in SETS:return None
  name,num,total,setname=m.groups();rarity=None
 else:
  m=re.fullmatch(r"KOR (.+) (\d+)/(\d+) (.+) \| Near Mint",title)
  if not m:return None
  name,num,total,tail=m.groups()
  hits=[(s,r,label) for s in SETS for label,r in RARITY_LABELS.items()
        if tail in (s+" "+label,s+" "+label+" Holo")]
  if len(hits)!=1:return None
  setname,rarity,_=hits[0]
 code,expected=SETS[setname]
 if int(total)!=expected or re.search(r"reverse|master.?ball|pok[eé].?ball|stamp|graded|PSA|BGS|CGC|1st|signed|oversized",name,re.I):return None
 return dict(name=name,number=int(num),total=int(total),set_code=code,rarity=rarity,set_name=setname)
def reject_catalog(row,p,names,shop):
 i=identity(p.get("title",""),shop)
 if (not i or row.get("language_code")!="ko" or row.get("identity_count")!=1
     or not row.get("card_id","").startswith("official_ko_")):return "catalog_identity"
 if ko.normalize(row["set_id"])!=ko.normalize(i["set_code"]) or int(row["local_id"])!=i["number"] or row["official_count"]!=i["total"]:return "set_number"
 if row["rarity"] not in REGULAR_RARITIES and not (shop=="shiny" and row["rarity"]=="R"):return "ambiguous_rarity"
 if i["rarity"] and row["rarity"]!=i["rarity"]:return "rarity"
 hits=[n for n in names if re.search(r"(?<![A-Za-z0-9])"+re.escape(n["9"])+r"(?![A-Za-z0-9])",i["name"],re.I)]
 if not hits:return "species"
 hits=[n for n in hits if len(n["9"])==max(len(x["9"]) for x in hits)]
 if len(hits)!=1 or ko.normalize(hits[0]["6"])!=ko.normalize(row["german_species"]) or ko.normalize(hits[0]["3"]) not in ko.normalize(row["native_name"]):return "species"
 return None
def match_offer(row,feed,detail,ajax,names,key,currency):
 shop=SHOPS[key];reason=reject_catalog(row,feed,names,key)
 if reason:return None,reason
 if currency!=shop["currency"]:return None,"currency"
 if any(p.get("id")!=feed.get("id") or p.get("title")!=feed.get("title") for p in (detail,ajax)):return None,"product_identity"
 handle=feed.get("handle","")
 if not re.fullmatch(r"[a-z0-9-]+",handle) or ajax.get("url")!="/products/"+handle:return None,"product_url"
 if key=="level":
  if feed.get("product_type")!="Single Card" or not {"Language: Korean","Pokémon","Single Card"}.issubset(set(feed.get("tags",[]))):return None,"language"
  i=identity(feed["title"],key)
  body_match=re.match(re.escape(i["name"])+r"\s+(\d+)/(\d+), a Pokémon TCG single from the "+re.escape(i["set_name"])+r" Korean set\.",detail.get("body_html",""))
  if not body_match or tuple(map(int,body_match.groups()))!=(i["number"],i["total"]):return None,"body_identity"
  if "Korean set" not in detail.get("body_html",""):return None,"language"
  condition="Near Mint"
  if any(len(p.get("options",[]))!=1 or p["options"][0].get("name")!="Condition" for p in (feed,detail)):return None,"options"
 else:
  body=detail.get("body_html","")
  i=identity(feed["title"],key)
  fields=defaultdict(list)
  for item in re.findall(r"<li>\s*(.*?)</li>",body,re.S):
   plain=html.unescape(re.sub(r"<[^>]+>","",item)).strip()
   if ":" in plain:
    k,val=plain.split(":",1);fields[k.strip()].append(val.strip())
  if any(fields[k]!=[val] for k,val in [("Language","Korean"),("Condition","Near Mint"),("Reverse Holo","No")]):return None,"body_identity"
  cardnum=[re.fullmatch(r"(\d+)/(\d+)",x) for x in fields["Card Number"]]
  if len(cardnum)!=1 or cardnum[0] is None or tuple(map(int,cardnum[0].groups()))!=(i["number"],i["total"]):return None,"body_identity"
  if not re.search(r"\("+re.escape(i["set_code"])+r"\)",body,re.I):return None,"body_identity"
  finish=fields["Finish"]
  if len(finish)!=1 or finish[0] not in ("Non-Holo","Holo"):return None,"printing"
  if row["rarity"]=="R" and finish[0]!="Holo":return None,"printing"
  condition="Default Title"
  if any(len(p.get("options",[]))!=1 or p["options"][0].get("name")!="Title" for p in (feed,detail)):return None,"options"
 selected=[]
 for p in (feed,detail,ajax):
  vs=[v for v in p.get("variants",[]) if v.get("title")==condition and v.get("option1")==condition and v.get("option2") is None and v.get("option3") is None]
  if len(vs)!=1:return None,"condition"
  selected.append(vs[0])
 fv,dv,av=selected
 if fv.get("available") is not True or av.get("available") is not True:return None,"stock"
 if type(fv.get("id")) is not int or any(v.get("id")!=fv["id"] or v.get("sku")!=fv.get("sku") for v in (dv,av)):return None,"offer_identity"
 amount=ko.retail.positive_decimal(dv.get("price"))
 if (amount is None or dv.get("price_currency")!=shop["currency"] or amount!=ko.retail.positive_decimal(fv.get("price"))
     or type(av.get("price")) is not int or Decimal(av["price"])/100!=amount):return None,"price_currency"
 if (av.get("quantity_rule") or {}).get("min")!=1 or (av.get("quantity_rule") or {}).get("increment")!=1 or av.get("requires_selling_plan") or av.get("selling_plan_allocations") or av.get("quantity_price_breaks"):return None,"bundle"
 return dict(source=shop["source"],currency=shop["currency"],amount=str(amount),title=feed["title"],
             url=shop["host"]+"/products/"+handle+"?variant="+str(fv["id"]),product_id=feed["id"],
             offer_variant_id=fv["id"],condition="Near Mint",rarity=row["rarity"],printing="ordinary",
             identity_method="explicit-Korean-NM/exact-set-number-denominator/independent-species"),None
def collection(shop):
 products=[];seen=set();deadline=time.monotonic()+100
 for page in range(1,9):
  if time.monotonic()>deadline:raise TimeoutError("collection deadline")
  batch=ko.retail.get_json(shop["host"]+"/collections/"+shop["collection"]+"/products.json?limit=250&page="+str(page))["products"]
  for p in batch:
   if p.get("id") in seen:raise ValueError("repeated pagination")
   seen.add(p["id"])
  products+=batch
  if len(batch)<250:return products
 raise ValueError("pagination limit")
def load_targets(source):
 rows=ko.load_targets(source)
 totals=json.loads(ko.retail.db("SELECT COALESCE(jsonb_object_agg(set_id,official_count),'{}') FROM catalog_sets_mirror WHERE language_code='ko';"))
 for r in rows:r["official_count"]=totals.get(r["set_id"])
 return rows
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--shop",choices=sorted(SHOPS),required=True)
 parser.add_argument("--apply",action="store_true");parser.add_argument("--report",type=Path);args=parser.parse_args()
 shop=SHOPS[args.shop];rows=load_targets(shop["source"]);names=ko.species_names()
 by_key=defaultdict(list)
 for r in rows:by_key[(ko.normalize(r["set_id"]),int(r["local_id"]))].append(r)
 currency=ko.retail.get_json(shop["host"]+"/cart.js").get("currency")
 if currency!=shop["currency"]:raise SystemExit("shop currency mismatch")
 fxdata=ko.retail.get_json("https://api.frankfurter.dev/v2/rate/"+currency+"/EUR");fx=ko.retail.positive_decimal(fxdata.get("rate"))
 if fx is None or not fxdata.get("date"):raise SystemExit("FX unavailable")
 products=collection(shop);rejected=Counter();errors=[];chosen={};observed=datetime.now(timezone.utc).isoformat()
 for p in products:
  i=identity(p.get("title",""),args.shop)
  if not i:continue
  eligible=[r for r in by_key[(ko.normalize(i["set_code"]),i["number"])] if reject_catalog(r,p,names,args.shop) is None]
  if not eligible or not any(v.get("available") for v in p["variants"]):continue
  handle=p.get("handle","")
  if not re.fullmatch(r"[a-z0-9-]+",handle):continue
  try:
   time.sleep(.3)
   detail=ko.retail.get_json(shop["host"]+"/products/"+handle+".json")["product"]
   ajax=ko.retail.get_json(shop["host"]+"/products/"+handle+".js")
  except Exception as e:errors.append(dict(product_id=p["id"],error=type(e).__name__));continue
  for r in eligible:
   offer,reason=match_offer(r,p,detail,ajax,names,args.shop,currency)
   if reason:rejected[reason]+=1;continue
   if Decimal(offer["amount"])*fx>100:rejected["high_asking_price_review"]+=1;continue
   offer.update(fx_to_eur=str(fx),fx_date=fxdata["date"])
   update=dict(row=r,offer=offer,observed_at=observed,base_eur=str((Decimal(offer["amount"])*fx/ko.retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP)))
   old=chosen.get(r["card_id"])
   if old is None or Decimal(offer["amount"])<Decimal(old["offer"]["amount"]):chosen[r["card_id"]]=update
 updates=list(chosen.values())
 report=dict(shop=args.shop,retail_products=len(products),matched=len(updates),rejected=dict(rejected),errors=errors,updates=updates,
             applied=ko.apply_updates(updates,shop["source"]) if args.apply and not errors else dict(variants=0,prices=0,history=0))
 if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
 print(json.dumps({k:v for k,v in report.items() if k!="updates"},ensure_ascii=False),flush=True)
 if errors:raise SystemExit(1)
if __name__=="__main__":main()
