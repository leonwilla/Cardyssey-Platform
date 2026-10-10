#!/usr/bin/env python3
"""Review the fifteen English leftovers against exact public source identities.

Preview by default. A source-specific temporary deferral is not a claim that no
price exists anywhere. Current prices and concurrent catalogue changes survive.
Unreleased/non-English prints are held explicitly without inventing a price.
"""
import argparse
import importlib.util
import json
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

spec=importlib.util.spec_from_file_location("western_review",Path(__file__).with_name("resolve-cardtrader-western-safe.py"))
western=importlib.util.module_from_spec(spec);spec.loader.exec_module(western)
retail=western.retail
REVIEW_PREFIX="EN_EXACT_SOURCE_REVIEW:"
# card: expansion, blueprint, TCGplayer product, exact blueprint version,
# exact TCGplayer title, variant type/size/stamps.
SPEC={
 "tk-xy-b-3": (1945,132389,98149,"Non-Holo | Trainer Kit 3/30","Metal Energy (#3)","normal","standard",[]),
 "tk-xy-b-12":(1945,132398,98161,"Non-Holo | Trainer Kit 12/30","Bidoof","normal","standard",[]),
 "tk-xy-b-18":(1945,132404,98156,"Non-Holo | Trainer Kit 18/30","Metal Energy (#18)","normal","standard",[]),
 "tk-xy-w-6": (1946,132602,98181,"Non-Holo | Trainer Kit 6/30","Fairy Energy (#6)","normal","standard",[]),
 "tk-xy-w-7": (1946,132603,98182,"Non-Holo | Trainer Kit 7/30","Fairy Energy (#7)","normal","standard",[]),
 "tk-xy-w-21":(1946,132617,98187,"Non-Holo | Trainer Kit 21/30","Fairy Energy (#21)","normal","standard",[]),
 "np-5":(1929,123977,87608,"Holo Promo | 5","Mudkip - 005 (POP Tournament)","holo","standard",["pop-tournament"]),
 "np-6":(1929,123978,89952,"Holo Promo | 6","Torchic - 006 (POP Tournament)","holo","standard",["pop-tournament"]),
 "np-7":(1929,123979,90036,"Holo Promo | 7","Treecko - 007 (POP Tournament)","holo","standard",["pop-tournament"]),
 "np-23":(1929,124000,87374,"Non-Holo Promo | 23","Metang - 023 (Stadium Challenge 2004)","normal","standard",["stadium-challenge"]),
 "np-11":(1929,123983,87231,"Non-Holo Promo | 11","Marshtomp - 011 (e-League) [Winner]","normal","standard",["winner"]),
}
GROUPS={1945:1533,1946:1533,1929:1423}
NON_ENGLISH={
 "bwp-BW78":("Raichu","BW78","English promo was planned but never released","https://bulbapedia.bulbagarden.net/wiki/Raichu_(BW_Promo_78)"),
 "dpp-DP54":("Beginning Door","DP54","DP54 promotional print was released exclusively in French","https://bulbapedia.bulbagarden.net/wiki/Beginning_Door_(Arceus_82)"),
 "dpp-DP55":("Ultimate Zone","DP55","DP55 promotional print was released exclusively in French","https://bulbapedia.bulbagarden.net/wiki/Ultimate_Zone_(Arceus_91)"),
}
FUTURE_URL="https://www.pokemon.com/uk/news/pokemon-tcg-30th-celebration-product-showcase"

def expected_variant(row, spec):
    v=row["variant"]
    return (row["language_code"]=="en" and v.get("id")==row["variant_id"]
      and v.get("type")==spec[5] and v.get("size","standard")==spec[6]
      and v.get("stamps",[])==spec[7] and not v.get("subtype") and not v.get("foil")
      and row["legacy_variant"]=={"normal":"NORMAL","holo":"HOLO"}[spec[5]])

def exact_blueprint(row, b, spec):
    return (expected_variant(row,spec) and b.get("id")==spec[1] and b.get("expansion_id")==spec[0]
      and b.get("game_id")==5 and b.get("category_id")==73 and b.get("version")==spec[3]
      and b.get("name")==row["name"] and b.get("tcg_player_id")==spec[2]
      and western.num((b.get("fixed_properties") or {}).get("collector_number"))==western.num(row["local_id"]))

def listing_amount(p,b):
    props=p.get("properties_hash") or {}
    if p.get("blueprint_id")!=b["id"] or p.get("name_en")!=b["name"] or (p.get("expansion") or {}).get("id")!=b["expansion_id"]:
        return None
    if not western.explicitly_false(p.get("graded")) or p.get("on_vacation") is not False:
        return None
    if props.get("pokemon_language")!="en" or props.get("condition") not in ("Near Mint","Mint"):
        return None
    if not all(western.explicitly_false(props.get(k)) for k in ("signed","altered")):
        return None
    for k in ("first_edition","pokemon_reverse"):
        if k in props and not western.explicitly_false(props[k]):
            return None
        if any(x.get("name")==k for x in b.get("editable_properties",[])) and not western.explicitly_false(props.get(k)):
            return None
    if props.get("collector_number")!=(b.get("fixed_properties") or {}).get("collector_number") or props.get("pokemon_rarity")!=(b.get("fixed_properties") or {}).get("pokemon_rarity"):
        return None
    if type(p.get("quantity")) is not int or p["quantity"]!=1 or p.get("description") not in (None,""):
        return None
    if any(k in p and (type(p[k]) is not int or p[k]!=1) for k in ("bundle_size","bundled_quantity")):
        return None
    price=p.get("price") or {}
    cents=price.get("cents")
    if type(cents) is not int or cents<=0 or price.get("currency")!="EUR":
        return None
    if type(p.get("price_cents")) is not int or p["price_cents"]!=cents or p.get("price_currency")!="EUR" or type(p.get("id")) is not int:
        return None
    return Decimal(cents)/100

def load_targets():
    ids=','.join(retail.quote(c) for c in list(SPEC)+list(NON_ENGLISH)+["mep-104"])
    return json.loads(retail.db("""SELECT COALESCE(jsonb_agg(to_jsonb(t)),'[]') FROM (
      SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.name,c.image_source_url old_image,
        c.variants old_variants,v.value variant,p.variant_id,p.legacy_variant,
        p.updated_at old_updated,p.resolution_status old_status
      FROM catalog_cards_mirror c JOIN tcg_price_cache p USING(card_id,language_code)
      JOIN LATERAL jsonb_array_elements(c.variants) v(value) ON v.value->>'id'=p.variant_id
      WHERE c.language_code='en' AND c.card_id IN ("""+ids+""")
        AND (p.resolution_status IN ('NO_PRICE','NO_PUBLIC_PRICE') OR p.failure_detail LIKE '"""+REVIEW_PREFIX+"""%')
    ) t"""))

def apply_sql(updates):
    payload=retail.quote(json.dumps(updates,ensure_ascii=False))
    return """WITH inputs AS (
      SELECT item->'row' r,item->>'status' status,item->>'source' source,item->>'base_eur' base,
        item->>'detail' detail,item->>'next_attempt_at' next_attempt FROM jsonb_array_elements("""+payload+"""::jsonb) item
    ), written AS (
      UPDATE tcg_price_cache p SET resolution_status=i.status,source=i.source,base_eur=i.base::numeric,
        failure_detail=i.detail,next_attempt_at=i.next_attempt::timestamptz,
        updated_at=CASE WHEN i.status='PRICE_FOUND' THEN NOW() ELSE p.updated_at END
      FROM inputs i JOIN catalog_cards_mirror c ON c.card_id=i.r->>'card_id' AND c.language_code='en'
      WHERE p.card_id=c.card_id AND p.language_code='en' AND p.variant_id=i.r->>'variant_id'
        AND p.resolution_status IS NOT DISTINCT FROM i.r->>'old_status'
        AND p.updated_at IS NOT DISTINCT FROM (i.r->>'old_updated')::timestamptz
        AND c.set_id=i.r->>'set_id' AND c.local_id=i.r->>'local_id' AND c.name=i.r->>'name'
        AND c.image_source_url IS NOT DISTINCT FROM i.r->>'old_image'
        AND c.variants=i.r->'old_variants' AND p.legacy_variant=i.r->>'legacy_variant'
        AND EXISTS(SELECT 1 FROM jsonb_array_elements(c.variants) v WHERE v=i.r->'variant')
        AND (p.resolution_status<>'PRICE_FOUND' OR p.failure_detail LIKE '"""+REVIEW_PREFIX+"""%')
        AND (i.status='PRICE_FOUND' OR p.failure_detail IS DISTINCT FROM i.detail OR p.next_attempt_at IS DISTINCT FROM i.next_attempt::timestamptz)
      RETURNING p.*
    ), history AS (
      INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
      SELECT card_id,language_code,variant_id,source,base_eur,updated_at FROM written WHERE resolution_status='PRICE_FOUND' RETURNING 1
    ) SELECT jsonb_build_object('reviewed_variants',(SELECT COUNT(*) FROM written),
      'prices',(SELECT COUNT(*) FROM written WHERE resolution_status='PRICE_FOUND'),'history',(SELECT COUNT(*) FROM history));"""

def apply_updates(updates):
    seen=set()
    for u in updates:
        r=u["row"];key=(r["card_id"],r["variant_id"])
        if r["language_code"]!="en" or key in seen or r["card_id"] not in set(SPEC)|set(NON_ENGLISH)|{"mep-104"}:
            raise ValueError("invalid or duplicate English review")
        seen.add(key)
        if u["status"]=="PRICE_FOUND":
            if r["card_id"] not in SPEC or not expected_variant(r,SPEC[r["card_id"]]) or u["source"] not in western.SOURCES or retail.positive_decimal(u["base_eur"]) is None:
                raise ValueError("invalid reviewed English price")
        elif u["status"]!="NO_PUBLIC_PRICE" or u["source"] is not None or u["base_eur"] is not None:
            raise ValueError("invalid deferral")
    return json.loads(retail.db(apply_sql(updates))) if updates else dict(reviewed_variants=0,prices=0,history=0)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--apply",action="store_true");parser.add_argument("--report",type=Path)
    args=parser.parse_args();rows=load_targets();observed=datetime.now(timezone.utc);retry=(observed+timedelta(days=7)).isoformat()
    token=next((x.split("=",1)[1].strip() for x in Path("/home/tv/cardshop/platform/.env").read_text().splitlines() if x.startswith("CARDTRADER_API_TOKEN=")),"")
    if not token:raise SystemExit("CardTrader credentials unavailable")
    last=0
    def get(url,auth=False):
        nonlocal last
        if auth:
            time.sleep(max(0,1.1-(time.monotonic()-last)));last=time.monotonic()
        return western.get_json(url,token if auth else None)
    sources={}
    for eid in sorted({SPEC[r["card_id"]][0] for r in rows if r["card_id"] in SPEC}):
        bps=get(western.BASE+"/blueprints/export?expansion_id="+str(eid),True)
        products=get(western.BASE+"/marketplace/products?expansion_id="+str(eid)+"&language=en",True)
        if not isinstance(bps,list) or not isinstance(products,dict):raise ValueError("unexpected marketplace payload")
        sources[eid]=(bps,products)
    feeds={gid:(get(f"https://tcgcsv.com/tcgplayer/3/{gid}/products")["results"],get(f"https://tcgcsv.com/tcgplayer/3/{gid}/prices")["results"]) for gid in {GROUPS[e] for e in sources}}
    fx=retail.positive_decimal(get("https://api.frankfurter.dev/v2/rate/USD/EUR").get("rate"))
    if fx is None:raise ValueError("FX unavailable")
    updates=[];held=[];evidence=[]
    for r in rows:
        cid=r["card_id"];amount=None;source=None;reason=None;next_at=retry;proof={}
        if cid in NON_ENGLISH:
            title,number,reason,url=NON_ENGLISH[cid]
            if r["name"]!=title or r["local_id"]!=number:held.append(dict(card_id=cid,reason="changed unissued identity"));continue
            next_at=None;proof=dict(kind="not_issued_in_English",reference=url)
        elif cid=="mep-104":
            if r["name"]!="Mewtwo" or r["local_id"]!="104":held.append(dict(card_id=cid,reason="changed future identity"));continue
            if observed>=datetime(2026,11,1,tzinfo=timezone.utc):
                held.append(dict(card_id=cid,reason="release window reached; requires fresh source identity"));continue
            reason="30th Celebration Figure Collection is announced for November 2026; no released English single-card market price imported"
            next_at="2026-11-01T00:00:00+00:00";proof=dict(kind="future_release",reference=FUTURE_URL)
        elif cid=="np-11" and r["variant"].get("size")=="jumbo":
            if r["variant"].get("type")!="normal" or r["variant"].get("stamps")!=["winner"]:
                held.append(dict(card_id=cid,reason="changed jumbo identity"));continue
            bps,market=sources[1929]
            compatible=[b for b in bps if b.get("name")==r["name"] and b.get("game_id")==5
              and b.get("category_id")==78 and b.get("expansion_id")==1929
              and "Jumbo" in b.get("version","") and western.num((b.get("fixed_properties") or {}).get("collector_number"))=="11"
              and any(x.get("name")=="pokemon_language" and "en" in x.get("possible_values",[]) for x in b.get("editable_properties",[]))]
            if compatible:
                held.append(dict(card_id=cid,reason="compatible jumbo identity requires fresh exact stamp review"));continue
            reason="Catalogued Jumbo Winner printing lacks a compatible explicitly English oversized provider identity; no ordinary-size price substituted"
            proof=dict(kind="unsupported_catalog_variant",checked_expansion_id=1929,compatible_English_jumbo_blueprints=0)
        else:
            sp=SPEC[cid]
            bps,market=sources[sp[0]];matches=[b for b in bps if exact_blueprint(r,b,sp)]
            prods,prices=feeds[GROUPS[sp[0]]]
            printed=r["local_id"].zfill(3) if cid.startswith("np-") else r["local_id"]+"/30"
            tcgs=[p for p in prods if p.get("productId")==sp[2] and p.get("groupId")==GROUPS[sp[0]] and p.get("categoryId")==3 and p.get("name")==sp[4]
              and [x.get("value") for x in p.get("extendedData",[]) if x.get("name")=="Number"]==[printed]]
            if len(matches)!=1 or len(tcgs)!=1:
                held.append(dict(card_id=cid,reason="exact source identity changed"));continue
            b=matches[0];listings=market.get(str(b["id"]),[])
            values=[v for p in listings if (v:=listing_amount(p,b)) is not None]
            exact_prices=[p for p in prices if p.get("productId")==sp[2] and western.norm(p.get("subTypeName"))=={"normal":"normal","holo":"holofoil"}[sp[5]]]
            proof=dict(blueprint_id=b["id"],tcgplayer_product_id=sp[2],group_id=GROUPS[sp[0]],marketplace_offers=len(listings),qualifying_nm_offers=len(values),exact_feed_price_rows=len(exact_prices))
            if values and min(values)<=100:
                amount=min(values);source="CARDTRADER_MARKETPLACE";proof.update(basis="lowest qualifying English NM/Mint single-card asking price",amount_eur=str(amount))
            elif len(exact_prices)==1 and retail.positive_decimal(exact_prices[0].get("marketPrice")):
                amount=retail.positive_decimal(exact_prices[0]["marketPrice"])*fx;source="TCGCSV_TCGPLAYER";proof.update(basis="exact marketPrice USD",fx_to_eur=str(fx))
            else:
                reason="Exact CardTrader/TCGplayer identity reviewed; no qualifying current English NM single-card quote in the checked marketplace/feed"
        if r["old_status"]=="PRICE_FOUND" and amount is None:
            held.append(dict(card_id=cid,reason="existing reviewed price retained; current quote unavailable"));continue
        status="PRICE_FOUND" if amount is not None else "NO_PUBLIC_PRICE"
        detail=REVIEW_PREFIX+" "+json.dumps(dict(reason=reason,observed_at=observed.isoformat(),scope="checked sources only; not an exhaustive internet absence claim",**proof),ensure_ascii=False)
        evidence.append(dict(card_id=cid,variant_id=r["variant_id"],status=status,reason=reason,proof=proof))
        updates.append(dict(row=r,status=status,source=source,base_eur=str((amount/western.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP)) if amount is not None else None,detail=detail,next_attempt_at=retry if amount is not None else next_at))
    report=dict(complete=True,cards=len({r["card_id"] for r in rows}),variants=len(rows),price_matches=sum(u["status"]=="PRICE_FOUND" for u in updates),reviewed=len(updates),held=held,evidence=evidence,updates=updates,
      applied=apply_updates(updates) if args.apply else dict(reviewed_variants=0,prices=0,history=0))
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10))
    print(json.dumps({k:v for k,v in report.items() if k not in ("updates","evidence")},ensure_ascii=False))
if __name__=="__main__":main()
