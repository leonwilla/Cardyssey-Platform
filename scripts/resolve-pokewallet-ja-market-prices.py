#!/usr/bin/env python3
"""Japanese ordinary-print market estimates from authenticated PokéWallet.
Require pinned official identity and an independently matched CardTrader TCGplayer ID.
"""
import argparse,importlib.util,json,re,time
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ja=load("resolve-cardtrader-ja-nm-prices");wallet=load("pokewallet-client");retail=ja.retail
SOURCE="POKEWALLET_JP_MARKET"
def market_offer(row,bp,record,provider_set,observed):
 info=record.get("card_info") or {}
 if provider_set.get("language")!="jap" or info.get("product_type")!="card":return None,"language_or_product"
 if str(info.get("set_id"))!=str(provider_set.get("set_id")) or ja.ko.normalize(info.get("set_code",""))!=ja.ko.normalize(row.get("market_code",row["set_id"])):return None,"set"
 if info.get("name")!=bp.get("name") or info.get("rarity") not in ja.RARITY.get(row["rarity"],set()):return None,"name_rarity"
 number=info.get("card_number","")
 if not re.fullmatch(r"\d+/\d+",number) or tuple(map(int,number.split("/")))!=(int(row["local_id"]),row["official_count"]):return None,"number_denominator"
 hp=retail.positive_decimal(info.get("hp"))
 if hp is None or hp!=int(hp):return None,"pokemon_hp"
 tcg=record.get("tcgplayer") or {};url=tcg.get("url","")
 if not str(bp.get("tcg_player_id","")).isdigit() or not re.fullmatch(r"https://www\.tcgplayer\.com/product/"+str(bp["tcg_player_id"])+r"(?:/[a-z0-9-]+)?",url):return None,"independent_product_id"
 finish="Normal" if row["rarity"] in ("C","U") else "Holofoil"
 quotes=[q for q in tcg.get("prices",[]) if q.get("sub_type_name")==finish]
 if len(quotes)!=1:return None,"finish_missing_or_ambiguous"
 quote=quotes[0];amount=retail.positive_decimal(quote.get("market_price"))
 if amount is None:return None,"no_market_price"
 try:
  updated=datetime.fromisoformat(quote["updated_at"])
  # PokéWallet examples omit timezone; provider timestamps are treated as UTC.
  if updated.tzinfo is None:updated=updated.replace(tzinfo=timezone.utc)
  age=(observed-updated).total_seconds()
  if not 0<=age<=8*86400:return None,"stale_or_future_quote"
 except (ValueError,KeyError,TypeError):return None,"quote_timestamp"
 if not isinstance(record.get("id"),str) or not re.fullmatch(r"pk_[0-9a-f]+",record["id"]):return None,"record_id"
 return dict(source=SOURCE,currency="USD",amount=str(amount),url=url,title=info["name"],
             basis="MARKET_ESTIMATE",in_stock=None,condition="aggregate-market",language="ja",
             finish=finish,printing="ordinary",blueprint_id=bp["id"],tcg_player_id=bp["tcg_player_id"],
             provider_card_id=record["id"],provider_set_id=provider_set["set_id"],quote_updated_at=quote["updated_at"],
             official_url=row["official_url"],official_number=row["official_number"],official_rarity=row["official_rarity"],
             source_record_revision=row["source_revision"],
             identity_method="pinned-official-ja/unique-CardTrader-blueprint/exact-TCGplayer-ID/number-denominator-rarity/Japanese-provider-set",
             basis_description="TCGplayer aggregate market estimate via PokéWallet; not a live NM offer"),None
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");p.add_argument("--missing-only",action="store_true");p.add_argument("--report",type=Path,required=True);p.add_argument("--max-requests",type=int,default=50);args=p.parse_args()
 if not 1<=args.max_requests<=80:raise ValueError("request budget outside permitted range")
 client=wallet.Client();calls=0
 def get(path,params=None):
  nonlocal calls
  if calls>=args.max_requests:raise wallet.ProviderError("run request budget exhausted")
  calls+=1;return client.get(path,params)
 names=ja.species_names();rows=ja.load_targets(SOURCE)
 if args.missing_only:rows=ja.missing.filter_targets(rows,retail)
 rows=[r for r in rows if ja.regular_set(r["set_id"])]
 rows,rejected=ja.cached_official_rows(rows,names)
 sets=get("/sets");assert sets.get("success") is True
 index=defaultdict(list)
 for entry in sets["data"]:
  if entry.get("language")=="jap":index[ja.ko.normalize(entry.get("set_code",""))].append(entry)
 token=next((x.split("=",1)[1].strip() for x in Path("/home/tv/cardshop/platform/.env").read_text().splitlines() if x.startswith("CARDTRADER_API_TOKEN=")),"")
 if not token:raise ValueError("identity provider credentials unavailable")
 last=0
 def ct(path):
  nonlocal last
  import urllib.request
  time.sleep(max(0,1.1-(time.monotonic()-last)));last=time.monotonic()
  req=urllib.request.Request(ja.BASE+path,headers={"Authorization":"Bearer "+token,"User-Agent":"Cardyssey/0.5 exact-ja-identity"})
  with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
 expansions=ct("/expansions");expindex=defaultdict(list)
 for exp in expansions:
  if exp.get("game_id")==5:expindex[ja.ko.normalize(exp.get("code",""))].append(exp)
 fxdata=retail.get_json("https://api.frankfurter.dev/v2/rate/USD/EUR");fx=retail.positive_decimal(fxdata.get("rate"))
 if fx is None or not fxdata.get("date"):raise ValueError("FX unavailable")
 groups=defaultdict(list)
 for row in rows:groups[ja.ko.normalize(row.get("market_code",row["set_id"]))].append(row)
 updates=[];errors=[];limited=False;observed=datetime.now(timezone.utc)
 # Largest blocks first. Leave enough allowance for a complete paginated set.
 for code,targets in sorted(groups.items(),key=lambda item:(-len(item[1]),item[0])):
  if len(index[code])!=1 or len(expindex[code])!=1:rejected["provider_set_or_expansion_ambiguous"]+=len(targets);continue
  provider_set=index[code][0];exp=expindex[code][0]
  expected_pages=(int(provider_set.get("card_count",0))+int(provider_set.get("sealed_count",0))+99)//100
  if calls+max(expected_pages,1)>args.max_requests:limited=True;continue
  try:
   bps=ct("/blueprints/export?expansion_id="+str(exp["id"]));records=[];page=1;total_pages=None
   while True:
    data=get("/search",dict(q=str(provider_set["set_id"]),page=page,limit=100))
    pagination=data.get("pagination") or {}
    if not isinstance(data.get("results"),list) or pagination.get("page")!=page or not isinstance(pagination.get("total_pages"),int):raise ValueError("unexpected pagination")
    if total_pages is None:total_pages=pagination["total_pages"]
    if pagination["total_pages"]!=total_pages or total_pages>10:raise ValueError("unstable or excessive pagination")
    records+=data["results"]
    if page>=total_pages:break
    page+=1
   if len({x.get("id") for x in records})!=len(records) or len(records)!=pagination.get("total"):raise ValueError("incomplete or duplicate provider page")
   for row in targets:
    matches=[bp for bp in bps if ja.blueprint_matches(row,bp,exp,names)]
    if len(matches)!=1:rejected["blueprint_missing_or_ambiguous"]+=1;continue
    bp=matches[0]
    candidates=[record for record in records if str((record.get("card_info") or {}).get("card_number","")).split("/")[0].lstrip("0")==str(int(row["local_id"]))]
    offers=[];reasons=[]
    for record in candidates:
     offer,reason=market_offer(row,bp,record,provider_set,observed)
     if offer:offers.append(offer)
     else:reasons.append(reason)
    if len(offers)!=1:rejected["quote_missing_or_ambiguous"]+=1;continue
    offer=offers[0]
    if Decimal(offer["amount"])*fx>100:rejected["high_market_price_review"]+=1;continue
    offer.update(fx_to_eur=str(fx),fx_date=fxdata["date"])
    updates.append(dict(row=row,offer=offer,observed_at=observed.isoformat(),base_eur=str((Decimal(offer["amount"])*fx/retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP))))
   print(json.dumps(dict(set=code,candidates=len(targets),matched_total=len(updates),requests=calls)),flush=True)
  except wallet.ProviderError as e:
   if "budget" in str(e) or "rate limit" in str(e):limited=True;break
   errors.append(dict(set=code,error=str(e)));break
  except Exception as e:errors.append(dict(set=code,error=type(e).__name__))
  ja.write_report(args.report,dict(complete=False,updates=updates,errors=errors))
 if len({u["row"]["card_id"] for u in updates})!=len(updates):raise ValueError("duplicate target")
 report=dict(complete=True,budget_limited=limited,candidates=len(rows),matched=len(updates),requests=calls,rejected=dict(rejected),errors=errors,updates=updates,
             applied=ja.apply_updates(updates,SOURCE,missing_only=args.missing_only) if args.apply and not errors else dict(variants=0,prices=0,history=0))
 ja.write_report(args.report,report);print(json.dumps({k:v for k,v in report.items() if k!="updates"}),flush=True)
 if errors:raise SystemExit(1)
if __name__=="__main__":main()
