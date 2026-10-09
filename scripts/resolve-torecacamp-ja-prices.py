#!/usr/bin/env python3
"""Curated exact Japanese classic-edition cards, TorecaCamp condition A.

Japanese titles and provider English aliases are explicitly reviewed mappings.
No unmarked editions, A-minus prices, or general card-level quotations are used.
Product JSON declares major-unit JPY; Ajax data is used for live stock only.
"""
import argparse
import importlib.util
import json
import re
import urllib.request
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

spec = importlib.util.spec_from_file_location("ja", Path(__file__).with_name("resolve-hareruya-ja-prices.py"))
ja = importlib.util.module_from_spec(spec); spec.loader.exec_module(ja)
retail = ja.retail
SOURCE = "WEB_TORECACAMP_JP"
HOST = "https://torecacamp-pokemon.com"
VARIANT_ID = "2fnyg4g532wu2uft0spaa3eefrz"
MANIFEST = {
    "VS1-104": dict(number=104, blueprint=141106, english="Falkner's TM 02",
                   title="ハヤトのワザマシン02 VS 104/141 【1ED】", product=8884468547758),
    "VS1-115": dict(number=115, blueprint=141117, english="Pryce's TM 01",
                   title="ヤナギのワザマシン01 VS 115/141 【1ED】", product=8884476608686),
    "VS1-126": dict(number=126, blueprint=141128, english="Karen's TM 02",
                   title="カリンのワザマシン02 VS 126/141 【1ED】", product=8884538671278),
    "VS1-133": dict(number=133, blueprint=141135, english="Pokémon Reverse",
                   title="ポケモンリバース VS 133/141 【1ED】", product=8912641130670),
}


MANIFEST.update(json.loads(Path(__file__).with_name("torecacamp-ja-classic-identities.json").read_text()))

def collector_matches(value, number, total):
    parts=str(value or "").split("/")
    return (len(parts) in (1,2) and all(p.isdigit() for p in parts)
            and int(parts[0])==number and (len(parts)==1 or int(parts[1])==total))


def match_offer(row, product, detail, ajax, blueprint):
    m = MANIFEST.get(row["card_id"])
    if not m or row["language_code"] != "ja" or row["set_id"] != m.get("set_id","VS1") or int(row["local_id"]) != m["number"] or row["official_count"] != m.get("official_count",141):
        return None, "catalog_identity"
    v = row["variant"]
    if row["variant_id"] != m.get("variant_id",VARIANT_ID) or row["legacy_variant"] != m.get("legacy_variant","NORMAL") or v.get("type") != m.get("legacy_variant","NORMAL").lower() or ja.edition(v, row["all_variants"]) != m.get("edition","first"):
        return None, "edition_or_printing"
    if sum(ja.edition(x,row["all_variants"])==m.get("edition","first") for x in row["all_variants"]) != 1:
        return None, "ambiguous_printing"
    if (row.get("blueprint_id") != m["blueprint"] or row.get("expansion_id") != m.get("expansion",1984)
            or row.get("identity_method") != "ja-classic-"+("1st" if m.get("edition","first")=="first" else "unlimited") or blueprint.get("id") != m["blueprint"]
            or blueprint.get("name") != m["english"] or blueprint.get("expansion_id") != m.get("expansion",1984)
            or blueprint.get("game_id") != 5 or blueprint.get("category_id") != 73
            or not collector_matches((blueprint.get("fixed_properties") or {}).get("collector_number"),m["number"],m.get("official_count",141))):
        return None, "provider_identity"
    if any(p.get("id") != m["product"] or p.get("title") != m["title"] for p in (product,detail,ajax)):
        return None, "retail_identity"
    if m.get("primary_tag","#VS_ポケモンカードVS") not in product.get("tags",[]) or "ポケモンカードシングル" not in product.get("tags",[]):
        return None, "set_language"
    if len(product.get("options",[])) != 1 or product["options"][0].get("name") != "コンディション":
        return None, "options"
    chosen = []
    for p in (product,detail,ajax):
        candidates=[x for x in p.get("variants",[]) if x.get("title")=="【状態A】" and x.get("option1")=="【状態A】"
                    and x.get("option2") is None and x.get("option3") is None]
        if len(candidates)!=1:
            return None,"condition"
        chosen.append(candidates[0])
    fv,dv,av=chosen
    if fv.get("available") is not True or av.get("available") is not True:
        return None,"stock"
    if any(x.get("id")!=fv.get("id") or x.get("sku")!=fv.get("sku") for x in (dv,av)) or type(fv.get("id")) is not int:
        return None,"offer_identity"
    if dv.get("price_currency")!="JPY":
        return None,"currency"
    amount=retail.positive_decimal(dv.get("price"))
    if amount is None or amount!=retail.positive_decimal(fv.get("price")):
        return None,"price"
    if (av.get("quantity_rule") or {}).get("min")!=1 or (av.get("quantity_rule") or {}).get("increment")!=1 or av.get("requires_selling_plan") or av.get("quantity_price_breaks"):
        return None,"bundle"
    handle=product.get("handle","")
    if not re.fullmatch(r"[a-z0-9_]+",handle) or ajax.get("url")!="/products/"+handle:
        return None,"product_url"
    return dict(source=SOURCE,currency="JPY",amount=str(amount),title=m["title"],
                url=HOST+"/products/"+handle+"?variant="+str(fv["id"]),product_id=m["product"],
                offer_variant_id=fv["id"],condition="TorecaCamp condition A (Japanese pre-BW guide)",
                identity_method="curated-Japanese-title/exact-set-number/explicit-edition/verified-provider-alias",
                blueprint_id=m["blueprint"]),None


def load_targets():
    ids=",".join(retail.quote(k) for k in MANIFEST)
    return json.loads(retail.db("""SELECT COALESCE(jsonb_agg(to_jsonb(x)),'[]') FROM (
      SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.name,c.image_source_url,c.variants all_variants,
        p.variant_id,p.legacy_variant,p.updated_at,p.resolution_status,v.value variant,s.official_count,
        vi.blueprint_id,vi.expansion_id,vi.method identity_method
      FROM catalog_cards_mirror c JOIN tcg_price_cache p USING(card_id,language_code)
      JOIN catalog_sets_mirror s USING(set_id,language_code)
      CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
      LEFT JOIN cardtrader_variant_identity_cache vi ON vi.card_id=c.card_id AND vi.language_code=c.language_code AND vi.variant_id=p.variant_id
      WHERE c.language_code='ja' AND c.card_id IN (""" + ids + """)
        AND v.value->>'id'=p.variant_id
        AND (p.resolution_status='NO_PRICE' OR p.source="""+retail.quote(SOURCE)+""")) x;"""))


def apply_updates(updates):
    if not updates:
        return 0
    if any(u["row"]["language_code"]!="ja" or u["row"]["card_id"] not in MANIFEST or u["offer"]["source"]!=SOURCE
           or retail.positive_decimal(u["base_eur"]) is None for u in updates):
        raise ValueError("invalid curated Japanese update")
    payload=retail.quote(json.dumps(updates))
    sql="""WITH incoming AS (SELECT x->'row' r,x->>'base_eur' base,x->'offer' offer,x->>'fx' fx,x->>'fx_date' fx_date,x->>'observed_at' observed
       FROM jsonb_array_elements("""+payload+"""::jsonb) x),
    written AS (
      UPDATE tcg_price_cache p SET base_eur=i.base::numeric,source="""+retail.quote(SOURCE)+""",
       updated_at=NOW(),resolution_status='PRICE_FOUND',next_attempt_at=NOW()+INTERVAL '7 days',
       failure_detail=(i.offer || jsonb_build_object('basis','ASKING','in_stock',true,'fx_to_eur',i.fx,
                      'fx_date',i.fx_date,'observed_at',i.observed,'nm_base_factor','0.92'))::text
      FROM incoming i JOIN catalog_cards_mirror c ON c.card_id=i.r->>'card_id' AND c.language_code='ja'
      WHERE p.card_id=c.card_id AND p.language_code='ja' AND p.variant_id=i.r->>'variant_id'
        AND p.updated_at=(i.r->>'updated_at')::timestamptz AND p.resolution_status=i.r->>'resolution_status'
        AND p.legacy_variant=i.r->>'legacy_variant' AND c.set_id=i.r->>'set_id' AND c.local_id=i.r->>'local_id'
        AND c.name=i.r->>'name' AND c.image_source_url IS NOT DISTINCT FROM i.r->>'image_source_url'
        AND c.variants=i.r->'all_variants'
      RETURNING p.card_id,p.language_code,p.variant_id,p.source,p.base_eur,p.updated_at
    ), history AS (
      INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at)
      SELECT card_id,language_code,variant_id,source,base_eur,updated_at FROM written RETURNING 1
    ) SELECT COUNT(*) FROM history;"""
    return int(retail.db(sql))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true");parser.add_argument("--report",type=Path)
    args=parser.parse_args()
    rows=[r for r in load_targets() if r["variant_id"]==MANIFEST[r["card_id"]].get("variant_id",VARIANT_ID)]
    if retail.get_json(HOST+"/cart.js").get("currency")!="JPY":
        raise SystemExit("shop currency not JPY")
    fxdata=retail.get_json("https://api.frankfurter.dev/v2/rate/JPY/EUR")
    fx=retail.positive_decimal(fxdata.get("rate"))
    if fx is None or not fxdata.get("date"):
        raise SystemExit("JPY/EUR unavailable")
    token=next((x.split("=",1)[1].strip() for x in Path("/home/tv/cardshop/platform/.env").read_text().splitlines() if x.startswith("CARDTRADER_API_TOKEN=")),"")
    if not token:
        raise SystemExit("provider identity credentials unavailable")
    blueprints={}
    for eid in sorted({MANIFEST[r["card_id"]].get("expansion",1984) for r in rows}):
        req=urllib.request.Request("https://api.cardtrader.com/api/v2/blueprints/export?expansion_id="+str(eid),
                                  headers={"Authorization":"Bearer "+token,"User-Agent":"Cardyssey/0.4 exact-identity-audit"})
        with urllib.request.urlopen(req,timeout=20) as response:
            blueprints.update({p["id"]:p for p in json.load(response)})
    products=[];seen=set()
    for handle in sorted({m.get("collection","vs") for m in MANIFEST.values()}):
        for page in range(1,5):
            batch=retail.get_json(HOST+"/collections/"+urllib.parse.quote(handle)+"/products.json?limit=250&page="+str(page))["products"]
            for p in batch:
                if p["id"] not in seen:
                    products.append(p);seen.add(p["id"])
            if len(batch)<250:
                break
        else:
            raise SystemExit("classic collection pagination limit")
    by_id={p["id"]:p for p in products}
    rejected=Counter();updates=[];review=[];observed=datetime.now(timezone.utc).isoformat()
    for row in rows:
        if row["variant_id"] != MANIFEST[row["card_id"]].get("variant_id",VARIANT_ID):
            continue
        p=by_id.get(MANIFEST[row["card_id"]]["product"])
        if not p:
            rejected["missing_product"]+=1;continue
        url=HOST+"/products/"+p["handle"]
        detail=retail.get_json(url+".json")["product"]
        ajax=retail.get_json(url+".js")
        o,reason=match_offer(row,p,detail,ajax,blueprints.get(row.get("blueprint_id"),{}))
        if reason:
            rejected[reason]+=1;continue
        if Decimal(o["amount"])*fx>Decimal("100"):
            rejected["high_asking_price_review"]+=1;review.append(dict(row=row,offer=o,fx=str(fx),reason="Single asking price exceeds EUR 100"));continue
        updates.append(dict(row=row,offer=o,base_eur=str((Decimal(o["amount"])*fx/retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP)),
                            fx=str(fx),fx_date=fxdata["date"],observed_at=observed))
    report=dict(candidates=len(rows),matched=len(updates),rejected=dict(rejected),updates=updates,review=review,applied=apply_updates(updates) if args.apply else 0)
    if args.report:
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("updates","review")},ensure_ascii=False))


if __name__=="__main__":
    main()
