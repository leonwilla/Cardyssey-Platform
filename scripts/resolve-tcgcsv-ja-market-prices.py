#!/usr/bin/env python3
"""Recover missing Japanese ordinary-print market estimates from free TCGCSV.
Require pinned official identity, exact CardTrader blueprint and Japanese product ID.
"""
import argparse,importlib.util,json,re,time,urllib.request
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
s=importlib.util.spec_from_file_location("ja",Path(__file__).with_name("resolve-cardtrader-ja-nm-prices.py"));ja=importlib.util.module_from_spec(s);s.loader.exec_module(ja)
SOURCE="TCGCSV_JP_MARKET";BASE="https://tcgcsv.com/tcgplayer/85";retail=ja.retail
def matching_product(row,bp,product,group_id):
 if product.get("categoryId")!=85 or product.get("groupId")!=group_id or type(product.get("productId")) is not int:return False
 if str(bp.get("tcg_player_id"))!=str(product["productId"]):return False
 name=str(product.get("name",""))
 suffix=re.search(r" - (\d+)/(\d+)$",name)
 if suffix:
  if tuple(map(int,suffix.groups()))!=(int(row["local_id"]),row["official_count"]):return False
  name=name[:suffix.start()]
 if name!=bp.get("name"):return False
 data=product.get("extendedData",[]);fields=defaultdict(list)
 for x in data:fields[x.get("name")].append(x.get("value"))
 if len(fields["Number"])!=1 or not re.fullmatch(r"\d+/\d+",fields["Number"][0]):return False
 if tuple(map(int,fields["Number"][0].split("/")))!=(int(row["local_id"]),row["official_count"]):return False
 if len(fields["Rarity"])!=1 or fields["Rarity"][0] not in ja.RARITY.get(row["rarity"],set()):return False
 if len(fields["HP"])!=1 or not str(fields["HP"][0]).isdigit() or int(fields["HP"][0])<=0:return False
 if (product.get("presaleInfo") or {}).get("isPresale") is not False:return False
 return True
def market_offer(row,bp,product,prices,group_id):
 if not matching_product(row,bp,product,group_id):return None,"product_identity"
 # Only the exact ordinary finish; no first edition, reverse or graded product.
 finish="Normal" if row["rarity"] in ("C","U") else "Holofoil"
 quotes=[p for p in prices if p.get("productId")==product["productId"] and p.get("subTypeName")==finish]
 if len(quotes)!=1:return None,"finish_price_missing_or_ambiguous"
 amount=retail.positive_decimal(quotes[0].get("marketPrice"))
 if amount is None:return None,"market_quote_missing"
 url=product.get("url","")
 if not re.fullmatch(r"https://www\.tcgplayer\.com/product/"+str(product["productId"])+r"/pokemon-japan-[a-z0-9-]+",url):return None,"product_url"
 return dict(source=SOURCE,currency="USD",amount=str(amount),url=url,title=product["name"],basis="MARKET_ESTIMATE",in_stock=None,
             language="ja",condition="aggregate-market",finish=finish,printing="ordinary",
             category_id=85,group_id=group_id,tcg_player_id=product["productId"],blueprint_id=bp["id"],
             official_url=row["official_url"],official_number=row["official_number"],official_rarity=row["official_rarity"],
             source_record_revision=row["source_revision"],identity_method="pinned-official-ja/unique-CardTrader-blueprint/exact-Japanese-TCGplayer-ID/number-denominator-rarity",
             basis_description="TCGplayer published market estimate for Japanese ordinary printing; not a live NM offer"),None
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");p.add_argument("--missing-only",action="store_true");p.add_argument("--report",type=Path);args=p.parse_args()
 names=ja.species_names();rows=ja.load_targets(SOURCE)
 if args.missing_only:rows=ja.missing.filter_targets(rows,retail)
 rows=[r for r in rows if ja.regular_set(r["set_id"])]
 rows,rejected=ja.cached_official_rows(rows,names)
 token=next((x.split("=",1)[1].strip() for x in Path("/home/tv/cardshop/platform/.env").read_text().splitlines() if x.startswith("CARDTRADER_API_TOKEN=")),"")
 if not token:raise ValueError("CardTrader credentials unavailable")
 last=0
 def ct(path):
  nonlocal last
  time.sleep(max(0,1.1-(time.monotonic()-last)));last=time.monotonic()
  with urllib.request.urlopen(urllib.request.Request(ja.BASE+path,headers={"Authorization":"Bearer "+token,"User-Agent":"Cardyssey/0.5 exact-ja-market"}),timeout=30) as r:return json.load(r)
 groups=retail.get_json(BASE+"/groups");assert groups["success"] and not groups["errors"]
 index=defaultdict(list)
 for g in groups["results"]:
  m=re.match(r"((?:SM|SV|S|XY)\d+[A-Za-z]*): ",g.get("name",""))
  if m:index[ja.ko.normalize(m[1])].append(g)
 expansions=ct("/expansions");expindex=defaultdict(list)
 for e in expansions:
  if e.get("game_id")==5:expindex[ja.ko.normalize(e.get("code",""))].append(e)
 by_code=defaultdict(list)
 for r in rows:by_code[ja.ko.normalize(r.get("market_code",r["set_id"]))].append(r)
 fxdata=retail.get_json("https://api.frankfurter.dev/v2/rate/USD/EUR");fx=retail.positive_decimal(fxdata.get("rate"))
 if fx is None or not fxdata.get("date"):raise ValueError("FX unavailable")
 updates=[];errors=[];observed=datetime.now(timezone.utc).isoformat()
 for code,targets in sorted(by_code.items()):
  if len(index[code])!=1 or len(expindex[code])!=1:rejected["group_or_expansion_ambiguous"]+=len(targets);continue
  group=index[code][0];exp=expindex[code][0];gid=group["groupId"]
  try:
   blueprints=ct("/blueprints/export?expansion_id="+str(exp["id"]))
   products=retail.get_json(BASE+"/"+str(gid)+"/products");prices=retail.get_json(BASE+"/"+str(gid)+"/prices")
   assert products["success"] and prices["success"] and not products["errors"] and not prices["errors"]
   by_id=defaultdict(list)
   for product in products["results"]:by_id[str(product["productId"])].append(product)
   for row in targets:
    bps=[bp for bp in blueprints if ja.blueprint_matches(row,bp,exp,names)]
    if len(bps)!=1:rejected["blueprint_missing_or_ambiguous"]+=1;continue
    bp=bps[0];hits=by_id[str(bp.get("tcg_player_id"))]
    if len(hits)!=1:rejected["japanese_product_id_missing"]+=1;continue
    offer,reason=market_offer(row,bp,hits[0],prices["results"],gid)
    if reason:rejected[reason]+=1;continue
    if Decimal(offer["amount"])*fx>100:rejected["high_market_price_review"]+=1;continue
    offer.update(fx_to_eur=str(fx),fx_date=fxdata["date"],feed_prices_updated_at=prices.get("lastUpdated"),feed_products_updated_at=products.get("lastUpdated"))
    updates.append(dict(row=row,offer=offer,observed_at=observed,base_eur=str((Decimal(offer["amount"])*fx/retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP))))
   print(json.dumps(dict(set=code,candidates=len(targets),matched_total=len(updates))),flush=True)
  except Exception as e:errors.append(dict(code=code,error=type(e).__name__))
  if args.report:ja.write_report(args.report,dict(complete=False,matched=len(updates),updates=updates,errors=errors))
 if len({u["row"]["card_id"] for u in updates})!=len(updates):raise ValueError("duplicate target")
 report=dict(complete=True,candidates=len(rows),matched=len(updates),rejected=dict(rejected),errors=errors,updates=updates,
             applied=ja.apply_updates(updates,SOURCE,missing_only=args.missing_only) if args.apply and not errors else dict(variants=0,prices=0,history=0))
 if args.report:ja.write_report(args.report,report)
 print(json.dumps({k:v for k,v in report.items() if k!="updates"}),flush=True)
 if errors:raise SystemExit(1)
if __name__=="__main__":main()
