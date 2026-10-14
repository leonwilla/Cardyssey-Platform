#!/usr/bin/env python3
"""Audit exact externally linked TCGplayer products against CardTrader live single stock.

Strictly diagnostic: CardTrader crosswalk and price listings are NOT automatic
print-identity, condition, or sold-price evidence.
"""
import argparse,importlib.util,json,collections
from pathlib import Path
import requests
spec=importlib.util.spec_from_file_location("western",Path(__file__).with_name("resolve-cardtrader-western-safe.py"))
western=importlib.util.module_from_spec(spec);spec.loader.exec_module(western)
env=Path("/home/tv/cardshop/platform/.env").read_text()
token=next(x.split("=",1)[1].strip() for x in env.splitlines() if x.startswith("CARDTRADER_API_TOKEN="))
headers={"Authorization":"Bearer "+token,"User-Agent":"Cardyssey/1.0 https://cardyssey.de","Accept":"application/json"}
def req(path,params=None):
 r=requests.get("https://api.cardtrader.com/api/v2"+path,headers=headers,params=params,timeout=25)
 r.raise_for_status()
 return r.json()
parser=argparse.ArgumentParser()
parser.add_argument("--input",type=Path,default=Path("/tmp/cardyssey-current-fallback.json"))
parser.add_argument("--output",type=Path,default=Path("/tmp/cardyssey-cardtrader-exact-stock-audit.json"))
args=parser.parse_args()
rows=json.loads(args.input.read_text())["unresolved"]
targets=[x for x in rows if x.get("exact_variant_provider_ids",{}).get("tcgplayer")]
expansions=req("/expansions")
expansion_by_id={e["id"]:e for e in expansions if e.get("game_id")==5}
# Only fetch exports for expansions selected by explicit tcgplayer product linkage.
# For legacy sets, scan candidate expansions using their set code/name, not arbitrary full exports.
lookup_sets={"ex8":["ex deoxys"],"np":["nintendo promos","nintendo promo","nintendo black star promos"],"basep":["wizards black star promos","wizards promos"],"mep":["mega evolution black star promos","mega evolution promo"]}
result=[]
for row in targets:
 pid=row["exact_variant_provider_ids"]["tcgplayer"]
 set_name=row["set_code"]
 possible=[e for e in expansion_by_id.values() if any(hint in str(e.get("name","")).lower() for hint in lookup_sets.get(set_name,[]))]
 if set_name=="mep":possible=[e for e in possible if "mega" in str(e.get("name","")).lower()]
 matches=[]
 for e in possible[:5]:
  try:
   blueprints=req("/blueprints/export",{"expansion_id":e["id"]})
   matches.extend([(e,b) for b in blueprints if str(b.get("tcg_player_id"))==str(pid)])
  except requests.RequestException:continue
 if len(matches)!=1:
  result.append(dict(language=row["language"],card_id=row["card_id"],variant_id=row["variant_id"],tcgplayer_id=pid,status="NO_UNIQUE_CROSSWALK",possible_expansions=len(possible),blueprint_matches=len(matches)))
  continue
 e,b=matches[0]
 try: stock=req("/marketplace/products",{"blueprint_id":b["id"],"language":row["language"]})
 except requests.RequestException as exc:
  result.append(dict(language=row["language"],card_id=row["card_id"],variant_id=row["variant_id"],tcgplayer_id=pid,status="MARKETPLACE_REQUEST_FAILED",blueprint_id=b["id"],error=type(exc).__name__))
  continue
 products=stock.get(str(b["id"]),[])
 eligible=[float(western.listing_amount(p,b["id"])) for p in products if western.listing_amount(p,b["id"]) is not None] if row["language"]=="en" else []
 result.append(dict(language=row["language"],card_id=row["card_id"],variant_id=row["variant_id"],tcgplayer_id=pid,blueprint_id=b["id"],blueprint_name=b.get("name"),blueprint_version=b.get("version"),expansion=e.get("name"),listings=len(products),eligible_en_nm_stock=len(eligible),min_en_nm_asking_eur=min(eligible) if eligible else None,status="HAS_EN_NM_OFFERS_VERIFY_PRINT" if eligible else "NO_ELIGIBLE_EN_NM_STOCK"))
 print(row["language"],row["card_id"],pid,result[-1]["status"],flush=True)
args.output.write_text(json.dumps({"cases":result},indent=2,ensure_ascii=False))
print("SUMMARY",dict(collections.Counter(x["status"] for x in result)),flush=True)
