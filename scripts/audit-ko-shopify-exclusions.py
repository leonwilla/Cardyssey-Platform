#!/usr/bin/env python3
"""Audit Korean Shopify exclusions without importing prices or guessing printings."""
import argparse,collections,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("shopify_ko",ROOT/"resolve-shopify-ko-prices.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
 p=argparse.ArgumentParser();p.add_argument("--shop",choices=sorted(m.SHOPS),required=True);p.add_argument("--report",type=Path)
 a=p.parse_args();shop=m.SHOPS[a.shop];products=m.collection(shop)
 ct=m.ko.module("resolve-cardtrader-ko-nm-prices");names=m.ko.species_names()
 targets=ct.extra.load_targets(shop["source"])+ct.pinned.load_targets(m.ko,shop["source"],names)
 targetkeys={(m.ko.normalize(r["set_id"]),int(r["local_id"])) for r in targets}
 rows=json.loads(m.ko.retail.db("""SELECT COALESCE(jsonb_agg(row_to_json(t)),'[]') FROM
  (SELECT c.set_id,c.local_id,c.card_id,c.rarity,c.variants->0->>'id' variant_id,
   EXISTS(SELECT 1 FROM tcg_price_cache p WHERE p.card_id=c.card_id
   AND p.language_code='ko' AND p.base_eur>0) priced
   FROM catalog_cards_mirror c WHERE c.language_code='ko') t;"""))
 bykey=collections.defaultdict(list)
 for r in rows:
  try:bykey[(m.ko.normalize(r["set_id"]),int(r["local_id"]))].append(r)
  except (TypeError,ValueError):pass
 counts=collections.Counter();review=[];examples=collections.defaultdict(list)
 for product in products:
  v=m.korean_variant(product);hit=m.TITLE.fullmatch(product.get("title",""))
  if not v or v.get("available") is not True or not hit:continue
  key=(m.ko.normalize(hit[3]),int(hit[4]))
  if key in targetkeys:counts["existing_import_target"]+=1;continue
  matches=bykey.get(key,[])
  if not matches:status="no_catalog_identity"
  elif len(matches)!=1:status="ambiguous_catalog_identity"
  elif matches[0]["priced"]:status="already_priced"
  elif matches[0]["variant_id"]:status="unpriced_with_variant"
  else:status="unpriced_without_variant"
  counts[status]+=1
  record=dict(title=product["title"],status=status,set=hit[3],number=int(hit[4]),
              card_id=matches[0]["card_id"] if len(matches)==1 else None,
              rarity=matches[0]["rarity"] if len(matches)==1 else None)
  if len(examples[status])<5:examples[status].append(record)
  if status in ("unpriced_with_variant","unpriced_without_variant"):review.append(record)
 result=dict(shop=a.shop,products=len(products),counts=dict(counts),samples=dict(examples),
             review_queue=review,prices_imported=0,read_only=True)
 if a.report:a.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
 print(json.dumps({k:v for k,v in result.items() if k not in ("samples","review_queue")},ensure_ascii=False))
if __name__=="__main__":main()
