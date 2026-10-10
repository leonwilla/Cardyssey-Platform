#!/usr/bin/env python3
"""Bulk exact modern Japanese deck, booster and numbered promo asking references.

Rarity-less identities remain rarity-less. Match exact native name, printed set,
number and denominator against a unique pinned official print. Validate condition
A, unit quantity, stock and JPY amount across public feed and live Ajax, with the documented cart currency contract.
"""
import argparse,concurrent.futures,importlib.util,json,re,threading,time,urllib.parse,urllib.request,urllib.error,http.cookiejar
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
def load(name):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ja=load("resolve-cardtrader-ja-nm-prices");pinned=load("ja-pinned-print-targets")
SHOPS={"hareruya":dict(host="https://www.hareruya2.com",source="WEB_HARERUYA_JP"),
       "toreca":dict(host="https://torecacamp-pokemon.com",source="WEB_TORECACAMP_JP")}
lock=threading.Lock();last=[0.];backoff=[0.]
openers={shop["host"]:urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())) for shop in SHOPS.values()}
def get(url):
    opener=next((o for host,o in openers.items() if url.startswith(host+"/")),urllib.request.build_opener())
    for attempt in range(4):
        with lock:
            delay=max(.65-(time.monotonic()-last[0]),backoff[0]-time.monotonic())
            if delay>0:time.sleep(delay)
            last[0]=time.monotonic()
        request=urllib.request.Request(url,headers={"User-Agent":"Cardyssey/0.5 exact-Japanese-public-print-audit"})
        try:
            with opener.open(request,timeout=20) as response:return json.load(response)
        except urllib.error.HTTPError as e:
            if e.code not in (429,502,503,504) or attempt==3:raise
            retry=e.headers.get("Retry-After","")
            seconds=max(90,int(retry) if retry.isdigit() else 0)
            with lock:backoff[0]=max(backoff[0],time.monotonic()+seconds)
            print(json.dumps(dict(http_status=e.code,provider_backoff_seconds=seconds)),flush=True)
    raise RuntimeError("retry exhaustion")
def parsed_identity(tag,p):
    title=p.get("title","")
    if re.search(r"PSA|BGS|CGC|鑑定|未開封|ミラー|マスター|モンスターボール|ピカチュウ.*切手|韓国|中国|英語版|海外|reverse|stamp|jumbo|bundle",title,re.I):
        return None
    tags=" ".join(p.get("tags",[]))
    if re.search(r"鑑定|韓国|中国|海外|English|Korean|Chinese",tags,re.I):return None
    if tag=="hareruya":
        m=re.fullmatch(r"(.+)\(([^)]+)\)\{[^}]+\}〈(\d+)/(\d+|[A-Za-z]+-P)〉\[([A-Za-z0-9-]+)\]",title)
        if not m or "状態表記の無いカードは状態A" not in (p.get("body_html") or p.get("description") or ""):return None
        name,rarity,number,total,code=m.groups()
    else:
        m=re.fullmatch(r"(.+?)\s+(?:(C|U|R|RR|RRR|SR|HR|UR|AR|SAR|S|SSR|CHR|CSR)\s+)?([A-Za-z0-9]+)\s+(\d+)/(\d+)",title)
        if m:name,rarity,code,number,total=m.groups()
        else:
            m=re.fullmatch(r"(.+?)\s+PROMO\s+(\d+)/([A-Za-z]+-P)",title)
            if not m:return None
            name,number,total=m.groups();code=total;rarity="PROMO"
        if "ポケモンカードシングル" not in p.get("tags",[]):return None
    return dict(name=name,rarity=rarity,code=code,number=int(number),total=total)
def condition_variant(tag,p):
    expected="Default Title" if tag=="hareruya" else "【状態A】"
    variants=p.get("variants") or []
    if tag=="hareruya" and len(variants)!=1:return None
    found=[v for v in variants if v.get("title")==expected and v.get("option1")==expected
           and v.get("option2") is None and v.get("option3") is None]
    if len(found)!=1:return None
    options=p.get("options") or []
    if len(options)!=1 or options[0].get("name")!=("Title" if tag=="hareruya" else "コンディション"):return None
    return found[0]
def identity_matches(row,tag,p):
    identity=parsed_identity(tag,p)
    if row.get("language_code")!="ja" or row.get("identity_count")!=1 or not identity:return False
    if not row.get("card_id","").startswith("official_ja_"):return False
    if ja.ko.normalize(identity["code"])!=ja.ko.normalize(row["printed_code"]):return False
    if identity["number"]!=int(row["local_id"]) or identity["total"]!=row["printed_total"]:return False
    if ja.ko.normalize(identity["name"])!=ja.ko.normalize(row["native_name"]):return False
    rarity=row.get("rarity")
    if rarity is not None:
        official=ja.OFFICIAL_RARITIES.get(rarity)
        if official is None or identity["rarity"]!=official:return False
    if row["set_id"] in pinned.PROMO_CODES and identity["rarity"]!="PROMO":return False
    return True
def match_offer(row,tag,feed,detail,ajax):
    for product in (feed,detail):
        if not identity_matches(row,tag,product):return None,"print_identity"
    if any(p.get("id")!=feed.get("id") or p.get("title")!=feed.get("title") or p.get("handle")!=feed.get("handle") for p in (detail,ajax)):
        return None,"product_identity"
    handle=feed.get("handle","")
    if not re.fullmatch(r"[a-z0-9_-]+",handle) or ajax.get("url")!="/products/"+handle:return None,"product_url"
    fv,dv,av=[condition_variant(tag,p) for p in (feed,detail,ajax)]
    if not fv or not dv or not av:return None,"condition"
    if type(fv.get("id")) is not int or not fv.get("sku") or any(v.get("id")!=fv["id"] or v.get("sku")!=fv["sku"] for v in (dv,av)):
        return None,"offer_identity"
    if fv.get("available") is not True or av.get("available") is not True:return None,"stock"
    amount=ja.retail.positive_decimal(fv.get("price"))
    if amount is None or amount!=ja.retail.positive_decimal(dv.get("price")) or dv.get("price_currency")!="JPY":
        return None,"currency_or_price"
    # Shopify appends two zeroes even for currencies without physical subunits.
    if type(av.get("price")) is not int or amount*100!=av["price"]:return None,"ajax_price"
    for v in (dv,av):
        rule=v.get("quantity_rule") or {}
        if rule.get("min")!=1 or rule.get("increment")!=1 or v.get("requires_selling_plan") or v.get("selling_plan_allocations") or v.get("quantity_price_breaks"):
            return None,"bundle_or_subscription"
    if ajax.get("requires_selling_plan"):return None,"subscription"
    shop=SHOPS[tag];identity=parsed_identity(tag,feed)
    return dict(source=shop["source"],currency="JPY",amount=str(amount),title=feed["title"],
                url=shop["host"]+"/products/"+handle+"?variant="+str(fv["id"]),product_id=feed["id"],
                offer_variant_id=fv["id"],sku=fv["sku"],condition=("Hareruya condition A" if tag=="hareruya" else "TorecaCamp condition A"),
                language="ja",printing="ordinary",retailer_rarity=identity["rarity"],
                official_url=row["official_url"],official_number=row["official_number"],source_record_revision=row["source_revision"],
                identity_method="exact-full-native-name/set-number-denominator/unique-pinned-official-print",
                basis_description="in-stock single-card condition-A retail asking reference"),None
def match_ajax_offer(row,tag,feed,ajax,currency):
    if currency!="JPY":return None,"currency"
    for product in (feed,ajax):
        if not identity_matches(row,tag,product):return None,"print_identity"
    if ajax.get("id")!=feed.get("id") or ajax.get("title")!=feed.get("title") or ajax.get("handle")!=feed.get("handle"):
        return None,"product_identity"
    handle=feed.get("handle","")
    if not re.fullmatch(r"[a-z0-9_-]+",handle) or ajax.get("url")!="/products/"+handle:return None,"product_url"
    fv,av=[condition_variant(tag,p) for p in (feed,ajax)]
    if not fv or not av:return None,"condition"
    if type(fv.get("id")) is not int or not fv.get("sku") or av.get("id")!=fv["id"] or av.get("sku")!=fv["sku"]:
        return None,"offer_identity"
    if fv.get("available") is not True or av.get("available") is not True:return None,"stock"
    amount=ja.retail.positive_decimal(fv.get("price"))
    # Primary Shopify contract: Ajax monetary values use cart.js currency;
    # product.price appends two zeroes for JPY as well. Both feeds must agree.
    if amount is None or type(av.get("price")) is not int or amount*100!=av["price"]:
        return None,"price_units"
    rule=av.get("quantity_rule") or {}
    if rule.get("min")!=1 or rule.get("increment")!=1 or av.get("requires_selling_plan") or av.get("selling_plan_allocations") or av.get("quantity_price_breaks") or ajax.get("requires_selling_plan"):
        return None,"bundle_or_subscription"
    shop=SHOPS[tag];identity=parsed_identity(tag,ajax)
    return dict(source=shop["source"],currency=currency,amount=str(amount),title=ajax["title"],
                url=shop["host"]+"/products/"+handle+"?variant="+str(fv["id"]),product_id=feed["id"],
                offer_variant_id=fv["id"],sku=fv["sku"],condition=("Hareruya condition A" if tag=="hareruya" else "TorecaCamp condition A"),
                language="ja",printing="ordinary",retailer_rarity=identity["rarity"],
                official_url=row["official_url"],official_number=row["official_number"],source_record_revision=row["source_revision"],
                identity_method="exact-full-native-name/set-number-denominator/unique-pinned-official-print",
                currency_evidence="same anonymous session cart.js presentment currency, Shopify Ajax product price units",
                currency_contract="https://shopify.dev/docs/api/ajax/reference/product",
                basis_description="in-stock single-card condition-A retail asking reference"),None
def fetch_inventory(tag,rows):
    shop=SHOPS[tag];host=shop["host"]
    if tag=="hareruya":
        handles=["sv","ss","sm"]
        if any(r["set_id"]=="XYP" for r in rows):handles.append("xy")
    else:
        registry=[]
        for page in range(1,11):
            batch=get(host+"/collections.json?limit=250&page="+str(page))["collections"];registry+=batch
            if len(batch)<250:break
        else:raise ValueError("collection registry pagination cap")
        codes={r["set_id"].lower() for r in rows}
        promo_handles={"xy-promo" for r in rows if r["set_id"]=="XYP"}|{"sv-promo" for r in rows if r["set_id"]=="SV-P"}
        handles=sorted({c["handle"] for c in registry if c["handle"] in promo_handles or re.split(r"[-_/\s]",c["handle"])[0].lower() in codes})
    products={}
    for handle in handles:
        seen=set()
        for page in range(1,101):
            batch=get(host+"/collections/"+urllib.parse.quote(handle,safe="")+"/products.json?limit=250&page="+str(page))["products"]
            ids=[p["id"] for p in batch]
            if len(set(ids))!=len(ids) or seen.intersection(ids):raise ValueError("repeated inventory pagination")
            seen.update(ids)
            for p in batch:products[p["id"]]=p
            if len(batch)<250:break
        else:raise ValueError("collection pagination cap")
    return dict(complete=True,scope=handles,products=list(products.values()))
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",choices=["all"]+list(SHOPS),default="all")
    parser.add_argument("--missing-only",action="store_true");parser.add_argument("--apply",action="store_true")
    parser.add_argument("--inventory-dir",type=Path,help="Optional checkpointed public feeds; every selected quotation is still verified live")
    parser.add_argument("--report",type=Path,required=True);args=parser.parse_args()
    tags=list(SHOPS) if args.source=="all" else [args.source]
    rows,pinned_rejected=pinned.load_targets(ja,[SHOPS[t]["source"] for t in tags],args.missing_only)
    index=defaultdict(list)
    for row in rows:index[(ja.ko.normalize(row["printed_code"]),int(row["local_id"]),row["printed_total"],ja.ko.normalize(row["native_name"]))].append(row)
    fxdata=get("https://api.frankfurter.dev/v2/rate/JPY/EUR");fx=ja.retail.positive_decimal(fxdata.get("rate"))
    if fx is None or not fxdata.get("date"):raise ValueError("FX unavailable")
    candidates=defaultdict(list);inventory_counts={};rejected=Counter(pinned_rejected)
    for tag in tags:
        inventory=json.loads((args.inventory_dir/("cardyssey-round16-"+tag+"-inventory.json")).read_text()) if args.inventory_dir else fetch_inventory(tag,rows)
        if inventory.get("complete") is not True:raise ValueError("incomplete inventory checkpoint")
        if get(SHOPS[tag]["host"]+"/cart.js").get("currency")!="JPY":raise ValueError("shop currency changed")
        inventory_counts[tag]=len(inventory["products"])
        for product in inventory["products"]:
            ident=parsed_identity(tag,product)
            if not ident:continue
            key=(ja.ko.normalize(ident["code"]),ident["number"],ident["total"],ja.ko.normalize(ident["name"]))
            targets=[r for r in index.get(key,[]) if identity_matches(r,tag,product)]
            if len(targets)!=1:continue
            variant=condition_variant(tag,product);amount=ja.retail.positive_decimal(variant.get("price")) if variant else None
            if not variant or variant.get("available") is not True or amount is None:rejected["feed_condition_or_stock"]+=1;continue
            if amount*fx>100:rejected["high_asking_price_review"]+=1;continue
            candidates[targets[0]["card_id"]].append((amount,tag,targets[0],product))
    observed=datetime.now(timezone.utc).isoformat();updates=[];errors=[]
    def verify(options):
        reasons=[]
        for _,tag,row,feed in sorted(options,key=lambda x:(x[0],x[1],x[3]["id"])):
            try:
                handle=feed["handle"]
                if not re.fullmatch(r"[a-z0-9_-]+",handle):raise ValueError("invalid handle")
                url=SHOPS[tag]["host"]+"/products/"+handle
                ajax=get(url+".js")
                offer,reason=match_ajax_offer(row,tag,feed,ajax,"JPY")
                if reason:reasons.append(reason);continue
                offer.update(fx_to_eur=str(fx),fx_date=fxdata["date"])
                base=(Decimal(offer["amount"])*fx/ja.retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP)
                return dict(row=row,offer=offer,base_eur=str(base),observed_at=datetime.now(timezone.utc).isoformat()),reasons,None
            except Exception as e:return None,reasons,dict(card_id=row["card_id"],source=tag,error=type(e).__name__,http_status=getattr(e,"code",None))
        return None,reasons,None
    report=dict(complete=False,catalog_candidates=len(rows),inventories=inventory_counts,product_candidates=len(candidates),matched=0,rejected={},errors=[],updates=[],applied={})
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for n,(update,reasons,error) in enumerate(pool.map(verify,candidates.values()),1):
            rejected.update(reasons)
            if error:errors.append(error)
            if update:updates.append(update)
            if n%50==0:
                report.update(checked=n,matched=len(updates),rejected=dict(rejected),errors=errors,updates=updates)
                ja.write_report(args.report,report)
                print(json.dumps(dict(checked=n,total=len(candidates),matched=len(updates),errors=len(errors))),flush=True)
    for tag in tags:
        if get(SHOPS[tag]["host"]+"/cart.js").get("currency")!="JPY":
            errors.append(dict(source=tag,error="currency_changed_during_run"))
    report.update(complete=True,checked=len(candidates),matched=len(updates),rejected=dict(rejected),errors=errors,updates=updates)
    if args.apply and not errors:
        for source in sorted({u["offer"]["source"] for u in updates}):
            batch=[u for u in updates if u["offer"]["source"]==source]
            report["applied"][source]=ja.apply_updates(batch,source,missing_only=args.missing_only)
    ja.write_report(args.report,report)
    print(json.dumps({k:v for k,v in report.items() if k!="updates"}),flush=True)
    if errors:raise SystemExit(1)
if __name__=="__main__":main()
