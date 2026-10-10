#!/usr/bin/env python3
"""Recover ordinary Japanese booster prints from exact CardTrader NM offers.

Preview by default. No cross-language quotations, played-price extrapolation, bundles,
unlabelled language, special printing or ambiguous blueprints are accepted.
"""
import argparse
import hashlib
import subprocess
import html
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
ko=extra.ko;SOURCE="CARDTRADER_JP_NM";BASE="https://api.cardtrader.com/api/v2"
RARITY={
 "R":{"Holo Rare"},"C":{"Common"},"U":{"Uncommon"},"RR":{"Ultra Rare","Double Rare"},
 "RRR":{"Ultra Rare","Triple Rare"},"AR":{"Art Rare","Illustration Rare"},
 "SR":{"Secret Rare","Super Rare","Full Art"},
 "SAR":{"Special Illustration Rare","Special Art Rare"},
 "UR":{"Hyper Rare","Ultra Rare","Secret Rare"},
 "HR":{"Hyper Rare","Rainbow Rare","Secret Rare"},
 "S":{"Shiny Rare","Shiny","Shiny Holo Rare"},"SSR":{"Shiny Ultra Rare","Shiny Secret Rare","Secret Rare"},
}
SET_ALIASES={'XY1-Bx': ('xy1', 'コレクションX'), 'XY1-By': ('xy1y', 'コレクションY'), 'XY2': ('xy2', 'ワイルドブレイズ'), 'XY3': ('xy3', 'ライジングフィスト'), 'XY4': ('xy4', 'ファントムゲート'), 'XY5-Bg': ('xy5', 'ガイアボルケーノ'), 'XY5-Bt': ('xy5t', 'タイダルストーム'), 'XY6-B': ('xy6', 'エメラルドブレイク'), 'XY7-B': ('xy7', 'バンデットリング'), 'XY8-Bb': ('xy8', '青い衝撃'), 'XY8-Br': ('xy8r', '赤い閃光'), 'XY9-B': ('xy9', '破天の怒り'), 'XY10-B': ('xy10', 'めざめる超王'), 'XY11-Bb': ('xy11f', '爆熱の闘士'), 'XY11-Br': ('xy11', '冷酷の反逆者')}
def regular_set(code):
 return code in SET_ALIASES or re.fullmatch(r"(?:SM|SV|S)\d+[A-Za-z]*",str(code),re.I) is not None
def blueprint_matches(row,bp,expansion,names):
 if row.get("language_code")!="ja" or row.get("identity_count")!=1 or not row.get("card_id","").startswith("official_ja_"):return False
 if not regular_set(row["set_id"]) or expansion.get("game_id")!=5 or ko.normalize(expansion.get("code",""))!=ko.normalize(row.get("market_code",row["set_id"])):return False
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
 if len(languages)!=1 or "jp" not in languages[0].get("possible_values",[]):return False
 name=str(bp.get("name",""))
 hits=[n for n in names if n["9"].casefold() in name.casefold() and re.search(r"(?<![A-Za-z0-9])"+re.escape(n["9"])+r"(?![A-Za-z0-9])",name,re.I)]
 if not hits:return False
 hits=[n for n in hits if len(n["9"])==max(len(x["9"]) for x in hits)]
 return len(hits)==1 and ko.normalize(hits[0]["6"])==ko.normalize(row["german_species"]) and ko.normalize(hits[0]["1"]) in ko.normalize(row["native_name"])
def false(value):
 return value is False or value=="false"
def listing_amount(p,bp,expansion):
 props=p.get("properties_hash") or {}
 if p.get("blueprint_id")!=bp["id"] or not false(p.get("graded")) or p.get("on_vacation") is not False:return None
 if (p.get("expansion") or {}).get("id")!=expansion["id"] or p.get("name_en")!=bp["name"]:return None
 if props.get("pokemon_language")!="jp" or props.get("condition") not in ("Near Mint","Mint"):return None
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
 if not offers:return None,"no_exact_japanese_nm_single"
 amount,p=min(offers,key=lambda x:(x[0],x[1]["id"]))
 if amount>100:return None,"high_asking_price_review"
 return dict(source=SOURCE,currency="EUR",amount=str(amount),url="https://www.cardtrader.com/cards/"+str(bp["id"]),
             title=bp["name"]+" | "+bp["version"],official_url=row["official_url"],official_rarity=row["official_rarity"],official_number=row["official_number"],source_record_revision=row["source_revision"],identity_evidence="cached parsed official record; current marketplace offer",blueprint_id=bp["id"],expansion_id=expansion["id"],
             product_id=p["id"],condition=p["properties_hash"]["condition"],language="jp",
             rarity=row["rarity"],printing="ordinary",qualifying_offers=len(offers),
             identity_method="unique-exact-booster-set-number-denominator-rarity/species/explicit-Japanese-NM/pinned-official-record",
             basis_description="lowest qualifying in-stock single-card asking offer"),None
def write_report(path,report):
 temporary=path.with_name(path.name+".tmp")
 temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10))
 temporary.replace(path)
missing_spec=importlib.util.spec_from_file_location("missing_prices",Path(__file__).with_name("missing-price-targets.py"))
missing=importlib.util.module_from_spec(missing_spec);missing_spec.loader.exec_module(missing)
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--apply",action="store_true");parser.add_argument("--report",type=Path)
 parser.add_argument("--missing-only",action="store_true",help="Only cards without any positive cached price; weekly default still refreshes")
 parser.add_argument("--sets",nargs="*",help="Optional exact catalogue set codes; default all regular Japanese boosters")
 args=parser.parse_args()
 token=next((x.split("=",1)[1].strip() for x in Path("/home/tv/cardshop/platform/.env").read_text().splitlines() if x.startswith("CARDTRADER_API_TOKEN=")),"")
 if not token:raise SystemExit("CardTrader identity credentials unavailable")
 last=0
 def get(path):
  nonlocal last
  time.sleep(max(0,1.1-(time.monotonic()-last)));last=time.monotonic()
  req=urllib.request.Request(BASE+path,headers={"Authorization":"Bearer "+token,"Accept":"application/json","User-Agent":"Cardyssey/0.5 exact-ja-NM"})
  with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
 rows=load_targets(SOURCE)
 if args.missing_only:rows=missing.filter_targets(rows,ko.retail)
 rows=[r for r in rows if regular_set(r["set_id"]) and (not args.sets or r["set_id"] in args.sets)]
 names=species_names()
 catalog_candidates=len(rows)
 rows,official_rejected=cached_official_rows(rows,names)
 expansions=get("/expansions");index=defaultdict(list)
 for e in expansions:
  if e.get("game_id")==5:index[ko.normalize(e.get("code",""))].append(e)
 groups=defaultdict(list);rejected=Counter(official_rejected)
 for row in rows:
  hits=index[ko.normalize(row.get("market_code",row["set_id"]))]
  if len(hits)!=1:rejected["expansion_missing_or_ambiguous"]+=1;continue
  groups[hits[0]["id"]].append(row)
 by_id={e["id"]:e for e in expansions};updates=[];errors=[];observed=datetime.now(timezone.utc).isoformat()
 for eid,group in sorted(groups.items()):
  try:
   blueprints=get("/blueprints/export?expansion_id="+str(eid))
   products=get("/marketplace/products?expansion_id="+str(eid)+"&language=jp")
   if not isinstance(blueprints,list) or not isinstance(products,dict) or any(not k.isdigit() or not isinstance(v,list) for k,v in products.items()):raise ValueError("unexpected provider payload")
   for row in group:
    offer,reason=match(row,blueprints,products,by_id[eid],names)
    if reason:rejected[reason]+=1;continue
    updates.append(dict(row=row,offer=offer,observed_at=observed,
                        base_eur=str((Decimal(offer["amount"])/ko.retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP))))
   print(json.dumps(dict(set=group[0]["set_id"],catalog_candidates=len(group),matched_total=len(updates))),flush=True)
  except Exception as e:errors.append(dict(expansion_id=eid,error=type(e).__name__))
  if args.report:
   checkpoint=dict(complete=False,candidates=catalog_candidates,verified_official=len(rows),expansions=len(groups),matched=len(updates),
                   rejected=dict(rejected),errors=errors,updates=updates,
                   applied=dict(variants=0,prices=0,history=0))
   write_report(args.report,checkpoint)

 report=dict(complete=True,candidates=catalog_candidates,verified_official=len(rows),expansions=len(groups),matched=len(updates),rejected=dict(rejected),errors=errors,updates=updates,
             applied=apply_updates(updates,SOURCE,missing_only=args.missing_only) if args.apply and not errors else dict(variants=0,prices=0,history=0))
 if args.report:write_report(args.report,report)
 print(json.dumps({k:v for k,v in report.items() if k!="updates"}),flush=True)
 if errors:raise SystemExit(1)
import urllib.parse
# Primary page fixtures and pinned parsed official records validate denominator/rarity in memory.
# Require a unique rarity-labelled official print. Unlabelled mirror records are
# held; native title/image, printed number, rarity badge and source must agree.
OFFICIAL_RARITIES={
 "rare_c_c":"C","rare_c":"C","rare_u_c":"U","rare_u":"U",
 "rare_r_c":"R","rare_r":"R","rare_rr":"RR","rare_rrr":"RRR",
 "rare_sr_c":"SR","rare_sr":"SR","rare_hr":"HR",
 "rare_ur_c":"UR","rare_ur":"UR","rare_ar":"AR","rare_sar":"SAR",
 "rare_s":"S","rare_s_2":"S","rare_ssr":"SSR",
}
def official_page(row,text):
 headings=re.findall(r'<h1[^>]*>(.*?)</h1>',text,re.S)
 if len(headings)!=1 or ko.normalize(html.unescape(re.sub(r"<[^>]+>","",headings[0])))!=ko.normalize(row["native_name"]):return None,"official_title"
 images=re.findall(r'<img[^>]*class="fit"[^>]*src="([^"]+)"',text)
 if len(images)!=1 or urllib.parse.urljoin("https://www.pokemon-card.com",html.unescape(images[0]))!=row["image_source_url"]:return None,"official_image"
 blocks=re.findall(r'<div class="subtext Text-fjalla">(.*?)</div>',text,re.S)
 if len(blocks)!=1:return None,"official_block"
 block=blocks[0];codes=re.findall(r'class="img-regulation" alt="([^"]+)"',block)
 if len(codes)!=1 or ko.normalize(codes[0])!=ko.normalize(row["set_id"]):return None,"official_set"
 number=re.findall(r"(?<![0-9])([0-9]+)\s*/\s*([0-9]+)(?![0-9])",html.unescape(re.sub(r"<[^>]+>"," ",block)))
 if len(number)!=1 or int(number[0][0])!=int(row["local_id"]) or int(number[0][1])<=0:return None,"official_number"
 rarities=re.findall(r"/rarity/ic_(rare_[a-z0-9_]+)\.(?:gif|png|svg)",block)
 if len(rarities)!=1 or rarities[0] not in OFFICIAL_RARITIES:return None,"official_rarity"
 if row["set_id"] in SET_ALIASES:
  market_code,set_title=SET_ALIASES[row["set_id"]]
  if "拡張パック「"+set_title+"」" not in html.unescape(re.sub(r"<[^>]+>"," ",text)):return None,"official_expansion_title"
 else:market_code=row["set_id"]
 result=dict(row,market_code=market_code,official_count=int(number[0][1]),rarity=OFFICIAL_RARITIES[rarities[0]],
             official_rarity=rarities[0],official_number="/".join(number[0]))
 return result,None
def cached_official_record(row,raw,revision):
 url=row.get("official_url","")
 if not re.fullmatch(r"https://www\.pokemon-card\.com/card-search/details\.php/card/[0-9]+",url):return None,"official_url"
 if row.get("source_revision")!=revision:return None,"source_revision"
 if row["card_id"]!="official_ja_"+hashlib.sha256(url.encode()).hexdigest()[:24]:return None,"source_identity"
 if raw.get("url")!=url or type(raw.get("jp_id")) is not int or str(raw["jp_id"])!=url.rsplit("/",1)[1]:return None,"source_identity"
 if raw.get("card_type")!="Pokémon":return None,"official_card_type"
 if any(ko.normalize(raw.get(k,""))!=ko.normalize(row[r]) for k,r in (("name","native_name"),("set_name","set_id"))):return None,"official_title_set"
 if raw.get("img")!=row["image_source_url"]:return None,"official_image"
 if not str(raw.get("number","")).isdigit() or int(raw["number"])!=int(row["local_id"]):return None,"official_number"
 total=raw.get("set_total")
 if not isinstance(total,str) or not total.isdigit() or int(total)<=0:return None,"official_denominator"
 rarity=raw.get("rarity")
 if rarity not in OFFICIAL_RARITIES or raw.get("rarity_img")!="https://www.pokemon-card.com/assets/images/card/rarity/ic_"+rarity+".gif":return None,"official_rarity"
 if raw.get("rarity")!=row.get("rarity"):return None,"catalog_rarity_changed"
 if row["set_id"] in SET_ALIASES:
  market_code,title=SET_ALIASES[row["set_id"]]
  if not any("拡張パック「"+title+"」" in x.get("name","") for x in raw.get("sources",[])):return None,"official_expansion_title"
 else:market_code=row["set_id"]
 return dict(row,official_count=int(total),rarity=OFFICIAL_RARITIES[rarity],official_rarity=rarity,
             official_number=str(raw["number"])+"/"+total,market_code=market_code),None
def independent_species(native_name,names):
 hits=[n for n in names if all(n.get(k) for k in ("1","6","9")) and ko.normalize(n["1"]) in ko.normalize(native_name)]
 if not hits:return None
 longest=max(len(ko.normalize(n["1"])) for n in hits)
 hits=[n for n in hits if len(ko.normalize(n["1"]))==longest]
 return hits[0] if len(hits)==1 else None

def cached_official_rows(rows,names=None):
 root=Path("/home/tv/.cache/cardyssey-catalog/source")
 revision=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
 records=defaultdict(list);urls={x["official_url"] for x in rows}
 for path in (root/"data_jp").rglob("*.json"):
  raw=json.loads(path.read_text())
  if raw.get("url") in urls:records[raw["url"]].append(raw)
 eligible=[];rejected=Counter()
 for row in rows:
  if row["identity_count"]!=1:rejected["official_identity_ambiguous"]+=1;continue
  hits=records[row["official_url"]]
  if len(hits)!=1:rejected["official_record_missing_or_ambiguous"]+=1;continue
  verified,reason=cached_official_record(row,hits[0],revision)
  if reason:rejected[reason]+=1
  else:
   if not verified.get("german_species"):
    species=independent_species(verified["native_name"],names or [])
    if species is None:
     rejected["independent_species_missing_or_ambiguous"]+=1;continue
    verified["german_species"]=species["6"]
    verified["species_identity_method"]="pinned-official-Pokemon-record/independent-PokeAPI-ja-de-en"
   eligible.append(verified)
 print(json.dumps(dict(cached_official_checked=len(rows),cached_official_verified=len(eligible),source_revision=revision,rejected=dict(rejected))),flush=True)
 return eligible,rejected

retail=ko.retail;VARIANT=ko.VARIANT
TRUSTED_JAPANESE_SOURCES=frozenset((SOURCE,"TCGCSV_JP_MARKET"))
def species_names():
 import csv,io
 grouped=defaultdict(dict)
 text=ko.get_text("https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_species_names.csv")
 for row in csv.DictReader(io.StringIO(text)):
  if row["local_language_id"] in ("1","6","9"):grouped[row["pokemon_species_id"]][row["local_language_id"]]=row["name"]
 return [n for n in grouped.values() if all(k in n for k in ("1","6","9"))]

def load_targets(source=SOURCE):
    if source not in TRUSTED_JAPANESE_SOURCES:raise ValueError('unsupported Japanese source')
    sql="""WITH counts AS (SELECT set_id,LTRIM(local_id,'0') AS num,COUNT(*) AS identity_count
      FROM catalog_cards_mirror WHERE language_code='ja' AND card_id LIKE 'official_ja_%' AND rarity IS NOT NULL GROUP BY set_id,LTRIM(local_id,'0'))
    SELECT COALESCE(jsonb_agg(row_to_json(t)),'[]') FROM (
      SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.raw_payload->>'name' AS native_name,
      c.image_source_url,c.variants AS old_variants,c.rarity,counts.identity_count,
      species.german_species,species.official_url,species.source_revision,p.updated_at AS old_updated,p.resolution_status AS old_status
      FROM catalog_cards_mirror c JOIN counts ON counts.set_id=c.set_id AND counts.num=LTRIM(c.local_id,'0')
      LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code=c.language_code AND p.variant_id='generated'
      JOIN LATERAL (SELECT MIN(german_species_name) AS german_species,MIN(source_url) AS official_url,MIN(source_revision) AS source_revision FROM catalog_supplemental_cards s
        WHERE s.canonical_card_id=c.card_id AND s.language_code=c.language_code HAVING COUNT(DISTINCT german_species_name) IN (0,1) AND COUNT(DISTINCT source_url)=1 AND COUNT(DISTINCT source_revision)=1) species ON TRUE
      WHERE c.language_code='ja' AND c.details_complete AND c.local_id ~ '^[0-9]+$'
      AND c.image_source_url IS NOT NULL AND c.image_source_url<>''
      AND (COALESCE(jsonb_array_length(c.variants),0)=0 OR (c.variants='"""+json.dumps([VARIANT])+"""'::jsonb AND c.raw_payload->>'_cardyssey_retail_variant_source'='CARDTRADER_JP_NM'))
      AND (p.card_id IS NULL OR p.resolution_status='NO_PRICE' OR (p.source='CARDTRADER_JP_NM' AND (TRUE)))
    ) t;"""
    sql=sql.replace(retail.quote(SOURCE),retail.quote(source))
    rows=json.loads(retail.db(sql))
    totals=json.loads(retail.db("SELECT COALESCE(jsonb_object_agg(set_id,official_count),'{}') FROM catalog_sets_mirror WHERE language_code='ja';"))
    for row in rows:row["official_count"]=totals.get(row["set_id"])
    return rows

def apply_updates(updates, source=SOURCE, *, missing_only=False):
    if source not in TRUSTED_JAPANESE_SOURCES:raise ValueError('unsupported Japanese source')
    if any(u['offer'].get('source')!=source for u in updates):raise ValueError('mixed Japanese sources')
    if any(u['row'].get('language_code')!='ja' or not u['row']['card_id'].startswith('official_ja_') for u in updates):raise ValueError('unsupported Japanese catalogue identity')
    if missing_only and any(u["row"].get("old_status")=="PRICE_FOUND" for u in updates):raise ValueError("missing-only recovery cannot refresh PRICE_FOUND")
    if not updates:return dict(variants=0,prices=0,history=0)
    def q(value):return 'NULL' if value is None else retail.quote(value)
    values=[]
    for update in updates:
        r,o=update['row'],update['offer']
        detail=json.dumps(dict(o,basis=o.get('basis','ASKING'),in_stock=o.get('in_stock',True),observed_at=update['observed_at'],nm_base_factor='0.92'),ensure_ascii=False)
        values.append('('+','.join(map(q,[r['card_id'],r['set_id'],r['local_id'],r['native_name'],r['image_source_url'],json.dumps(r['old_variants']),r['old_updated'],r['old_status'],update['base_eur'],detail]))+')')
    sql="""WITH incoming(card_id,set_id,local_id,native_name,image,old_variants,old_updated,old_status,base_eur,detail) AS (VALUES """+','.join(values)+"""),
    eligible AS (SELECT i.*,jsonb_array_length(c.variants)=0 AS needs_variant FROM incoming i
      JOIN catalog_cards_mirror c ON c.card_id=i.card_id AND c.language_code='ja'
      LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code='ja' AND p.variant_id='generated'
      WHERE c.set_id=i.set_id AND c.local_id=i.local_id AND c.raw_payload->>'name'=i.native_name AND c.image_source_url=i.image
      AND c.variants=i.old_variants::jsonb AND p.updated_at IS NOT DISTINCT FROM i.old_updated::timestamptz
      AND p.resolution_status IS NOT DISTINCT FROM i.old_status),
    catalog_changed AS (UPDATE catalog_cards_mirror c SET variants='"""+json.dumps([VARIANT])+"""'::jsonb,
      raw_payload=jsonb_set(c.raw_payload,'{_cardyssey_retail_variant_source}','\"CARDTRADER_JP_NM\"'::jsonb,true)
      FROM eligible i WHERE i.needs_variant AND c.language_code='ja' AND c.card_id=i.card_id
      AND c.variants=i.old_variants::jsonb AND c.set_id=i.set_id AND c.local_id=i.local_id
      AND c.raw_payload->>'name'=i.native_name AND c.image_source_url=i.image RETURNING c.card_id),
    ready AS (SELECT e.* FROM eligible e WHERE NOT e.needs_variant OR EXISTS(SELECT 1 FROM catalog_changed c WHERE c.card_id=e.card_id)),
    written AS (INSERT INTO tcg_price_cache(card_id,language_code,variant_id,legacy_variant,source,base_eur,updated_at,resolution_status,failure_detail,next_attempt_at)
      SELECT card_id,'ja','generated','NORMAL','CARDTRADER_JP_NM',base_eur::numeric,NOW(),'PRICE_FOUND',detail,NOW()+INTERVAL '7 days' FROM ready
      ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,
      updated_at=EXCLUDED.updated_at,resolution_status=EXCLUDED.resolution_status,failure_detail=EXCLUDED.failure_detail,next_attempt_at=EXCLUDED.next_attempt_at
      WHERE EXISTS(SELECT 1 FROM ready r WHERE r.card_id=EXCLUDED.card_id
        AND tcg_price_cache.updated_at IS NOT DISTINCT FROM r.old_updated::timestamptz
        AND tcg_price_cache.resolution_status IS NOT DISTINCT FROM r.old_status)
      RETURNING card_id,language_code,variant_id,source,base_eur),
    history AS (INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
      SELECT card_id,language_code,variant_id,source,base_eur,NOW() FROM written RETURNING 1)
    SELECT jsonb_build_object('variants',(SELECT COUNT(*) FROM catalog_changed),'prices',(SELECT COUNT(*) FROM written),'history',(SELECT COUNT(*) FROM history));"""
    sql=sql.replace(retail.quote(SOURCE),retail.quote(source))
    sql=sql.replace(retail.quote(json.dumps(SOURCE)),retail.quote(json.dumps(source)))
    if missing_only:
        sql=sql.replace("AND p.resolution_status IS NOT DISTINCT FROM i.old_status)", "AND p.resolution_status IS NOT DISTINCT FROM i.old_status AND NOT EXISTS(SELECT 1 FROM tcg_price_cache existing WHERE existing.card_id=c.card_id AND existing.base_eur>0))")
        sql=sql.replace("WHERE EXISTS(SELECT 1 FROM ready r WHERE r.card_id=EXCLUDED.card_id", "WHERE COALESCE(tcg_price_cache.base_eur,0)<=0 AND EXISTS(SELECT 1 FROM ready r WHERE r.card_id=EXCLUDED.card_id")
    return json.loads(retail.db(sql))

if __name__=="__main__":main()
