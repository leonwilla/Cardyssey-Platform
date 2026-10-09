#!/usr/bin/env python3
"""Recover ordinary Korean booster prints from exact CardTrader NM offers.

Preview by default. No Japanese quotations, played-price extrapolation, bundles,
unlabelled language, special printing or ambiguous blueprints are accepted.
"""
import argparse
import importlib.util
import json
import re
import time
import urllib.request
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
spec=importlib.util.spec_from_file_location("extra",Path(__file__).with_name("resolve-extra-ko-prices.py"))
extra=importlib.util.module_from_spec(spec);spec.loader.exec_module(extra)
ko=extra.ko;SOURCE="CARDTRADER_KO_NM";BASE="https://api.cardtrader.com/api/v2"
RARITY={
 "R":{"Holo Rare"},"C":{"Common"},"U":{"Uncommon"},"RR":{"Ultra Rare","Double Rare"},
 "RRR":{"Ultra Rare","Triple Rare"},"AR":{"Art Rare","Illustration Rare"},
 "SR":{"Secret Rare","Super Rare","Full Art"},
 "SAR":{"Special Illustration Rare","Special Art Rare"},
 "UR":{"Hyper Rare","Ultra Rare","Secret Rare"},
 "HR":{"Hyper Rare","Rainbow Rare","Secret Rare"},
 "S":{"Shiny Rare","Shiny","Shiny Holo Rare"},"SSR":{"Shiny Ultra Rare","Shiny Secret Rare","Secret Rare"},
}
def regular_set(code):
 return re.fullmatch(r"(?:SM|SV|S|XY|M)\d+[A-Za-z]*",str(code),re.I) is not None
def blueprint_matches(row,bp,expansion,names):
 if row.get("language_code")!="ko" or row.get("identity_count")!=1 or not row.get("card_id","").startswith("official_ko_"):return False
 if not regular_set(row["set_id"]) or expansion.get("game_id")!=5 or ko.normalize(expansion.get("code",""))!=ko.normalize(row["set_id"]):return False
 if bp.get("game_id")!=5 or bp.get("category_id")!=73 or bp.get("expansion_id")!=expansion["id"]:return False
 fixed=bp.get("fixed_properties") or {}
 if not str(fixed.get("collector_number","")).isdigit() or int(fixed["collector_number"])!=int(row["local_id"]):return False
 version=str(bp.get("version",""))
 number=re.findall(r"(?<!\d)(\d+)/(\d+)(?!\d)",version)
 if len(number)!=1 or tuple(map(int,number[0]))!=(int(row["local_id"]),row["official_count"]):return False
 if re.search(r"reverse|master.?ball|pok[eé].?ball|promo|stamp|edition|staff|winner|signed|world|error|jumbo|oversized|non.?holo|cosmos|cracked|sheen",version,re.I):return False
 if fixed.get("pokemon_rarity") not in RARITY.get(row.get("rarity"),set()):return False
 # Ordinary R prints require an explicit holo blueprint; generic Rare is insufficient.
 if row.get("rarity")=="R" and not re.fullmatch(r"Holo Rare \| \d+/\d+",version):return False
 languages=[p for p in bp.get("editable_properties",[]) if p.get("name")=="pokemon_language"]
 if len(languages)!=1 or "kr" not in languages[0].get("possible_values",[]):return False
 name=str(bp.get("name",""))
 hits=[n for n in names if n["9"].casefold() in name.casefold() and re.search(r"(?<![A-Za-z0-9])"+re.escape(n["9"])+r"(?![A-Za-z0-9])",name,re.I)]
 if not hits:return False
 hits=[n for n in hits if len(n["9"])==max(len(x["9"]) for x in hits)]
 return len(hits)==1 and ko.normalize(hits[0]["6"])==ko.normalize(row["german_species"]) and ko.normalize(hits[0]["3"]) in ko.normalize(row["native_name"])
def false(value):
 return value is False or value=="false"
def listing_amount(p,bp,expansion):
 props=p.get("properties_hash") or {}
 if p.get("blueprint_id")!=bp["id"] or not false(p.get("graded")) or p.get("on_vacation") is not False:return None
 if (p.get("expansion") or {}).get("id")!=expansion["id"] or p.get("name_en")!=bp["name"]:return None
 if props.get("pokemon_language")!="kr" or props.get("condition") not in ("Near Mint","Mint"):return None
 if not all(false(props.get(k)) for k in ("signed","altered")):return None
 editable={x.get("name") for x in bp.get("editable_properties",[])}
 for key in ("first_edition","pokemon_reverse"):
  if key in editable and not false(props.get(key)):return None
  if key in props and not false(props[key]):return None
 if any("reverse" in str(k).lower() and not false(v) for k,v in props.items()):return None
 if props.get("collector_number")!=(bp.get("fixed_properties") or {}).get("collector_number") or props.get("pokemon_rarity")!=(bp.get("fixed_properties") or {}).get("pokemon_rarity"):return None
 # Marketplace response describes physical units and stock quantity, not the
 # inventory-export bundle schema. Limit to stock=1, empty description and
 # category-73 single-card blueprints; reject any explicit non-unit bundle.
 if type(p.get("quantity")) is not int or p["quantity"]!=1 or p.get("description") not in (None,""):return None
 if any(k in p and (type(p[k]) is not int or p[k]!=1) for k in ("bundle_size","bundled_quantity")):return None
 price=p.get("price") or {};cents=price.get("cents")
 if type(cents) is not int or cents<=0 or price.get("currency")!="EUR":return None
 if type(p.get("price_cents")) is not int or p.get("price_cents")!=cents or p.get("price_currency")!="EUR":return None
 if type(p.get("id")) is not int:return None
 return Decimal(cents)/100
def match(row,blueprints,products,expansion,names):
 candidates=[b for b in blueprints if blueprint_matches(row,b,expansion,names)]
 if len(candidates)!=1:return None,"blueprint_missing_or_ambiguous"
 bp=candidates[0];offers=[]
 for p in products.get(str(bp["id"]),[]):
  amount=listing_amount(p,bp,expansion)
  if amount is not None:offers.append((amount,p))
 if not offers:return None,"no_exact_korean_nm_single"
 amount,p=min(offers,key=lambda x:(x[0],x[1]["id"]))
 if amount>100:return None,"high_asking_price_review"
 return dict(source=SOURCE,currency="EUR",amount=str(amount),url="https://www.cardtrader.com/cards/"+str(bp["id"]),
             title=bp["name"]+" | "+bp["version"],blueprint_id=bp["id"],expansion_id=expansion["id"],
             product_id=p["id"],condition=p["properties_hash"]["condition"],language="kr",
             rarity=row["rarity"],printing="ordinary",qualifying_offers=len(offers),
             identity_method="unique-exact-booster-set-number-denominator-rarity/species/explicit-Korean-NM",
             basis_description="lowest qualifying in-stock single-card asking offer"),None
def write_report(path,report):
 temporary=path.with_name(path.name+".tmp")
 temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10))
 temporary.replace(path)
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--apply",action="store_true");parser.add_argument("--report",type=Path)
 parser.add_argument("--sets",nargs="*",help="Optional exact catalogue set codes; default all regular Korean boosters")
 args=parser.parse_args()
 token=next((x.split("=",1)[1].strip() for x in Path("/home/tv/cardshop/platform/.env").read_text().splitlines() if x.startswith("CARDTRADER_API_TOKEN=")),"")
 if not token:raise SystemExit("CardTrader identity credentials unavailable")
 last=0
 def get(path):
  nonlocal last
  time.sleep(max(0,1.1-(time.monotonic()-last)));last=time.monotonic()
  req=urllib.request.Request(BASE+path,headers={"Authorization":"Bearer "+token,"Accept":"application/json","User-Agent":"Cardyssey/0.5 exact-ko-NM"})
  with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
 rows=extra.load_targets(SOURCE)
 rows=[r for r in rows if regular_set(r["set_id"]) and (not args.sets or r["set_id"] in args.sets)]
 names=ko.species_names();expansions=get("/expansions");index=defaultdict(list)
 for e in expansions:
  if e.get("game_id")==5:index[ko.normalize(e.get("code",""))].append(e)
 groups=defaultdict(list);rejected=Counter()
 for row in rows:
  hits=index[ko.normalize(row["set_id"])]
  if len(hits)!=1:rejected["expansion_missing_or_ambiguous"]+=1;continue
  groups[hits[0]["id"]].append(row)
 by_id={e["id"]:e for e in expansions};updates=[];errors=[];observed=datetime.now(timezone.utc).isoformat()
 for eid,group in sorted(groups.items()):
  try:
   blueprints=get("/blueprints/export?expansion_id="+str(eid))
   products=get("/marketplace/products?expansion_id="+str(eid)+"&language=kr")
   if not isinstance(blueprints,list) or not isinstance(products,dict) or any(not k.isdigit() or not isinstance(v,list) for k,v in products.items()):raise ValueError("unexpected provider payload")
   for row in group:
    offer,reason=match(row,blueprints,products,by_id[eid],names)
    if reason:rejected[reason]+=1;continue
    updates.append(dict(row=row,offer=offer,observed_at=observed,
                        base_eur=str((Decimal(offer["amount"])/ko.retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP))))
   print(json.dumps(dict(set=group[0]["set_id"],catalog_candidates=len(group),matched_total=len(updates))),flush=True)
  except Exception as e:errors.append(dict(expansion_id=eid,error=type(e).__name__))
  if args.report:
   checkpoint=dict(complete=False,candidates=len(rows),expansions=len(groups),matched=len(updates),
                   rejected=dict(rejected),errors=errors,updates=updates,
                   applied=dict(variants=0,prices=0,history=0))
   write_report(args.report,checkpoint)

 report=dict(complete=True,candidates=len(rows),expansions=len(groups),matched=len(updates),rejected=dict(rejected),errors=errors,updates=updates,
             applied=ko.apply_updates(updates,SOURCE) if args.apply and not errors else dict(variants=0,prices=0,history=0))
 if args.report:write_report(args.report,report)
 print(json.dumps({k:v for k,v in report.items() if k!="updates"}),flush=True)
 if errors:raise SystemExit(1)
if __name__=="__main__":main()
