#!/usr/bin/env python3
"""Exact Japanese print recovery using full-card raster evidence between pinned peers.

Images only disambiguate otherwise exact native-name/set/number/denominator
identities. No cross-language or artwork-only pricing. Preview by default.
"""
import concurrent.futures
import argparse,hashlib,json,re,subprocess,tempfile,time,urllib.request,urllib.error
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
import importlib.util

def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+".py"))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
bulk=load("resolve-japanese-bulk-retail-prices");ja=bulk.ja;pinned=bulk.pinned
SOURCES=[s["source"] for s in bulk.SHOPS.values()]
REVERSE=dict(ja.VARIANT,type="reverse",legacyVariant="REVERSE")
VARIANTS={"ordinary":ja.VARIANT,"reverse":REVERSE,
          "pokeball":dict(REVERSE,foil="pokeball"),"masterball":dict(REVERSE,foil="masterball")}
BODY=(16,165,201,265)
ART=(16,41,201,147)
MAX_ART_ERROR=3.5
MIN_RIVAL_ART=16
MAX_ERROR=2.5
# A rival must differ substantially in the full frame and a fixed local region,
# and at least four times more than the best recompression-level match.
MIN_RIVAL_WHOLE=8
MIN_RIVAL_BODY=8
MIN_RIVAL_RATIO=4

def parsed_identity(tag,p):
    title=p.get("title","")
    if re.search(r"PSA|BGS|CGC|鑑定|未開封|韓国|中国|英語版|海外|stamp|jumbo|bundle",title,re.I):return None
    tags=" ".join(p.get("tags",[]))
    if re.search(r"鑑定|韓国|中国|海外|English|Korean|Chinese",tags,re.I):return None
    ordinary=bulk.parsed_identity(tag,p)
    if ordinary:return dict(ordinary,printing="ordinary")
    if tag=="hareruya":
        m=re.fullmatch(r"(.+):(モンスターボールミラー|マスターボールミラー)\(([^)]+)\)\{[^}]+\}〈(\d+)/(\d+)〉\[([A-Za-z0-9]+)-(Mo|Ma)\]",title)
        if not m or "状態表記の無いカードは状態A" not in (p.get("body_html") or p.get("description") or ""):return None
        name,finish,rarity,num,total,code,suffix=m.groups()
        if (finish,suffix) not in (("モンスターボールミラー","Mo"),("マスターボールミラー","Ma")):return None
        printing="pokeball" if suffix=="Mo" else "masterball"
    elif tag=="toreca":
        if "ポケモンカードシングル" not in p.get("tags",[]):return None
        m=re.fullmatch(r"(マスターボール\))?(.+?) ミラー\s+(?:(C|U|R|RR|RRR|SR|HR|UR|AR|SAR|S|SSR|CHR|CSR)\s+)?([A-Za-z0-9]+)\s+(\d+)/(\d+)",title)
        if not m:return None
        master,name,rarity,code,num,total=m.groups();printing="masterball" if master else "reverse"
    else:return None
    if re.search(r"ミラー|マスター|モンスターボール|reverse",name,re.I):return None
    return dict(name=name,rarity=rarity,code=code,number=int(num),total=total,printing=printing)

def identity_key(i):
    return (ja.ko.normalize(i["code"]),int(i["number"]),i["total"],ja.ko.normalize(i["name"]))

def row_key(r):
    return identity_key(dict(code=r["printed_code"],number=r["local_id"],total=r["printed_total"],name=r["native_name"]))

def metadata_matches(row,tag,product):
    i=parsed_identity(tag,product)
    if not i or row.get("language_code")!="ja" or not row.get("card_id","").startswith("official_ja_"):return False
    if identity_key(i)!=row_key(row):return False
    rarity=row.get("rarity")
    if rarity is not None and ja.OFFICIAL_RARITIES.get(rarity) is None:return False
    # An omitted retailer rarity is proved by the full official print image,
    # never copied into catalogue metadata. Explicit contradictory rarity holds.
    if rarity is not None and i["rarity"] is not None and i["rarity"]!=ja.OFFICIAL_RARITIES[rarity]:return False
    if row["set_id"] in pinned.PROMO_CODES and i["rarity"]!="PROMO":return False
    return True

def prepare_image(path):
    with Image.open(path) as src:
        w,h=src.size
        if w<400 or h<600 or not .69<w/h<.73:raise ValueError("full-card image dimensions")
        return src.convert("RGB").resize((217,303),Image.Resampling.LANCZOS)

def distances(image,template):
    diff=ImageChops.difference(image,template)
    return dict(whole=sum(ImageStat.Stat(diff).mean)/3,body=sum(ImageStat.Stat(diff.crop(BODY)).mean)/3,art=sum(ImageStat.Stat(diff.crop(ART)).mean)/3)

def select_print(image,templates):
    if len(templates)<2:return None,[]
    scores=sorted([dict(card_id=cid,**distances(image,im)) for cid,im in templates.items()],key=lambda s:s["whole"]+s["body"])
    best=scores[0]
    if best["whole"]>MAX_ERROR or best["body"]>MAX_ERROR:return None,scores
    if not separated_scores(scores):return None,scores
    return best["card_id"],scores

def separated_scores(scores):
    """Full frame and text/foil body must match; all rivals need local separation.

    Some official holographic prints differ in the illustration while their
    lower text body is identical. That route also requires a close illustration
    match and twice the minimum local rival distance. Neither route accepts
    artwork-only matches or a close competing print.
    """
    if len(scores)<2:return False
    best=scores[0]
    if best["whole"]>MAX_ERROR or best["body"]>MAX_ERROR:return False
    for rival in scores[1:]:
        if rival["whole"]<max(MIN_RIVAL_WHOLE,MIN_RIVAL_RATIO*best["whole"]):return False
        body=rival["body"]>=max(MIN_RIVAL_BODY,MIN_RIVAL_RATIO*best["body"])
        art=best.get("art",float("inf"))<=MAX_ART_ERROR and rival.get("art",0)>=max(MIN_RIVAL_ART,MIN_RIVAL_RATIO*best.get("art",float("inf")))
        if not (body or art):return False
    return True

def image_url(p):
    images=p.get("images") or []
    if not images:return None
    value=images[0].get("src") if isinstance(images[0],dict) else images[0]
    if not isinstance(value,str):return None
    if value.startswith("//"):value="https:"+value
    # Image fetches never send credentials; restrict to the retailer's Shopify CDN.
    if not re.fullmatch(r"https://cdn\.shopify\.com/[^\s]+",value):return None
    return value

def download_image(url,path):
    for attempt in range(4):
        with bulk.lock:
            delay=max(.65-(time.monotonic()-bulk.last[0]),bulk.backoff[0]-time.monotonic())
            if delay>0:time.sleep(delay)
            bulk.last[0]=time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Cardyssey/0.5 exact-Japanese-public-print-audit"}),timeout=20) as response:
                data=response.read(8_000_001)
            if len(data)>8_000_000:raise ValueError("image exceeds size limit")
            path.write_bytes(data);return hashlib.sha256(data).hexdigest()
        except urllib.error.HTTPError as e:
            if e.code not in (429,502,503,504) or attempt==3:raise
            retry=e.headers.get("Retry-After","");seconds=max(90,int(retry) if retry.isdigit() else 0)
            with bulk.lock:bulk.backoff[0]=max(bulk.backoff[0],time.monotonic()+seconds)
            print(json.dumps(dict(http_status=e.code,provider_backoff_seconds=seconds)),flush=True)

def load_groups(missing_only):
    sql="""WITH counts AS (SELECT set_id,LTRIM(local_id,'0') num,COUNT(*) identity_count
      FROM catalog_cards_mirror WHERE language_code='ja' GROUP BY set_id,LTRIM(local_id,'0'))
    SELECT COALESCE(jsonb_agg(row_to_json(t)),'[]') FROM (
      SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.rarity,c.details_complete,
        c.raw_payload->>'name' native_name,c.image_source_url,c.image_local_path,c.variants old_variants,
        c.raw_payload->>'_cardyssey_retail_variant_source' variant_source,
        p.updated_at old_updated,p.resolution_status old_status,p.source old_source,counts.identity_count,
        s.official_url,s.source_revision,
        EXISTS(SELECT 1 FROM tcg_price_cache positive WHERE positive.card_id=c.card_id AND positive.base_eur>0) already_priced
      FROM catalog_cards_mirror c JOIN counts ON counts.set_id=c.set_id AND counts.num=LTRIM(c.local_id,'0')
      LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code='ja' AND p.variant_id='generated'
      LEFT JOIN LATERAL (SELECT MIN(source_url) official_url,MIN(source_revision) source_revision
        FROM catalog_supplemental_cards s WHERE s.canonical_card_id=c.card_id AND s.language_code='ja'
        HAVING COUNT(DISTINCT source_url)=1 AND COUNT(DISTINCT source_revision)=1)s ON TRUE
      WHERE c.language_code='ja' AND c.card_id LIKE 'official_ja_%' AND c.local_id ~ '^[0-9]+$' AND counts.identity_count>1)t;"""
    rows=[r for r in json.loads(ja.retail.db(sql)) if pinned.eligible_code(r["set_id"])]
    revision=subprocess.run(["git","-C",str(pinned.CACHE),"rev-parse","HEAD"],check=True,capture_output=True,text=True).stdout.strip()
    needed={r["official_url"] for r in rows};raws=defaultdict(list)
    for path in (pinned.CACHE/"data_jp").rglob("*.json"):
        raw=json.loads(path.read_text())
        if raw.get("url") in needed:raws[raw["url"]].append(raw)
    coarse=defaultdict(list);held=Counter();groups={}
    for r in rows:coarse[(r["set_id"],int(r["local_id"]),r["native_name"])].append(r)
    for peers in coarse.values():
        verified=[]
        for r in peers:
            raw=raws[r["official_url"]]
            proof=pinned.verified_record(r,raw[0],revision,require_unique=False) if len(raw)==1 and r["details_complete"] else None
            if proof and re.fullmatch(r"cards/ja/official_ja_[a-f0-9]+\.jpg",proof.get("image_local_path") or ""):verified.append(proof)
        if len(verified)!=len(peers):held["incomplete_pinned_peer_group"]+=1;continue
        denominators=defaultdict(list)
        for r in verified:
            variant_ok=r["old_variants"]==[] or (r["variant_source"] in SOURCES and r["old_variants"] in [[v] for v in VARIANTS.values()])
            status_ok=r["old_status"] in (None,"NO_PRICE") or r["old_source"] in SOURCES
            r["target_eligible"]=variant_ok and status_ok and (not missing_only or not r["already_priced"])
            denominators[row_key(r)].append(r)
        for k,v in denominators.items():
            if len(v)>=2 and any(r["target_eligible"] for r in v):groups[k]=v
    return groups,held

def export_templates(groups,directory):
    paths=sorted({r["image_local_path"] for peers in groups.values() for r in peers})
    directory.mkdir(parents=True,exist_ok=True)
    listing=directory/"image-paths.txt";listing.write_text("\n".join(paths)+"\n")
    subprocess.run(["docker","cp",str(listing),"cardyssey-api:/tmp/cardyssey-image-price-paths.txt"],check=True,capture_output=True)
    archive=directory/"official-images.tgz"
    with archive.open("wb") as output:
        subprocess.run(["docker","exec","cardyssey-api","tar","-C","/data/catalog","-czf","-","-T","/tmp/cardyssey-image-price-paths.txt"],stdout=output,check=True)
    # Only explicitly validated card paths from our own container are extracted.
    subprocess.run(["tar","-xzf",str(archive),"-C",str(directory)],check=True)
    return directory

_gate_spec=importlib.util.spec_from_file_location("manual_import_gate",Path(__file__).with_name("missing-price-targets.py"))
manual_gate=importlib.util.module_from_spec(_gate_spec);_gate_spec.loader.exec_module(manual_gate)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",choices=["all"]+list(bulk.SHOPS),default="toreca",help="Default retailer supplies exact public card renders; photographed cards remain held by the same image guards")
    p.add_argument("--missing-only",action="store_true");p.add_argument("--apply",action="store_true")
    p.add_argument("--inventory-dir",type=Path);p.add_argument("--image-root",type=Path)
    p.add_argument("--report",type=Path,required=True);args=p.parse_args()
    tags=list(bulk.SHOPS) if args.source=="all" else [args.source]
    groups,held=load_groups(args.missing_only)
    work=args.report.parent/(args.report.stem+"-images");work.mkdir(parents=True,exist_ok=True)
    image_root=args.image_root or export_templates(groups,work/"official")
    templates={}
    for key,peers in groups.items():
        try:templates[key]={r["card_id"]:prepare_image(image_root/r["image_local_path"]) for r in peers}
        except (OSError,ValueError):held["incomplete_peer_images"]+=1
    groups={k:v for k,v in groups.items() if k in templates}
    report=dict(complete=False,groups=len(groups),catalog_candidates=sum(r["target_eligible"] for v in groups.values() for r in v),inventories={},product_candidates=0,checked=0,matched=0,rejected={},errors=[],updates=[],applied={})
    ja.write_report(args.report,report)
    fxdata=bulk.get("https://api.frankfurter.dev/v2/rate/JPY/EUR");fx=ja.retail.positive_decimal(fxdata.get("rate"))
    if fx is None or not fxdata.get("date"):raise ValueError("FX unavailable")
    candidates=[]
    for tag in tags:
        inv=json.loads((args.inventory_dir/("cardyssey-round16-"+tag+"-inventory.json")).read_text()) if args.inventory_dir else bulk.fetch_inventory(tag,[r for v in groups.values() for r in v])
        if inv.get("complete") is not True:raise ValueError("incomplete inventory")
        if bulk.get(bulk.SHOPS[tag]["host"]+"/cart.js").get("currency")!="JPY":raise ValueError("shop currency changed")
        report["inventories"][tag]=len(inv["products"])
        for feed in inv["products"]:
            ident=parsed_identity(tag,feed)
            if not ident:continue
            key=identity_key(ident)
            if key not in groups:continue
            if not all(metadata_matches(r,tag,feed) for r in groups[key]):held["peer_metadata"]+=1;continue
            v=bulk.condition_variant(tag,feed);amount=ja.retail.positive_decimal(v.get("price")) if v else None
            if not v or v.get("available") is not True or amount is None:held["feed_condition_or_stock"]+=1;continue
            if amount*fx>100:held["high_asking_price_review"]+=1;continue
            if not image_url(feed):held["image_url"]+=1;continue
            if not re.fullmatch(r"[a-z0-9_-]+",feed.get("handle", "")):held["product_url"]+=1;continue
            candidates.append((amount,tag,feed,ident,key))
    report["product_candidates"]=len(candidates);selected={}
    def verify(candidate):
        _,tag,feed,ident,key=candidate;reasons=Counter()
        try:
            ajax=bulk.get(bulk.SHOPS[tag]["host"]+"/products/"+feed["handle"]+".js")
            if image_url(ajax)!=image_url(feed):reasons["live_image_changed"]+=1;return None,reasons,None
            # Metadata guard precedes expensive image download; original payloads stay intact.
            if not all(metadata_matches(r,tag,ajax) for r in groups[key]):reasons["live_peer_metadata"]+=1;return None,reasons,None
            path=work/(tag+"-"+str(feed["id"])+".img")
            digest=download_image(image_url(ajax),path)
            try:image=prepare_image(path)
            except (OSError,ValueError):reasons["invalid_full_card_image"]+=1;return None,reasons,None
            cid,scores=select_print(image,templates[key])
            if cid is None:reasons["image_not_distinct"]+=1;return None,reasons,None
            row=next(r for r in groups[key] if r["card_id"]==cid)
            if not row["target_eligible"]:reasons["best_print_ineligible"]+=1;return None,reasons,None
            variant=VARIANTS[ident["printing"]]
            if row["old_variants"] not in ([],[variant]):reasons["existing_variant_disagrees"]+=1;return None,reasons,None
            offer,reason=bulk.match_ajax_offer(row,tag,feed,ajax,"JPY",identity_validator=metadata_matches,identity_parser=parsed_identity)
            if reason:reasons[reason]+=1;return None,reasons,None
            offer.update(fx_to_eur=str(fx),fx_date=fxdata["date"],identity_method="exact-full-native-name/set-number-denominator/pinned-full-card-and-foil-body-raster/body-or-illustration-peer-separation",
                image_evidence=dict(retail_url=image_url(ajax),retail_sha256=digest,scores=scores,
                    normalized_size=[217,303],foil_body_crop=list(BODY),max_match_mae=MAX_ERROR,
                    min_rival_whole_mae=MIN_RIVAL_WHOLE,min_rival_body_mae=MIN_RIVAL_BODY,min_rival_error_ratio=MIN_RIVAL_RATIO,
                    illustration_crop=list(ART),max_match_illustration_mae=MAX_ART_ERROR,min_rival_illustration_mae=MIN_RIVAL_ART,
                    official_templates=[dict(card_id=r["card_id"],url=r["image_source_url"],sha256=hashlib.sha256((image_root/r["image_local_path"]).read_bytes()).hexdigest()) for r in groups[key]]))
            base=(Decimal(offer["amount"])*fx/ja.retail.NM_FACTOR).quantize(Decimal(".0001"),rounding=ROUND_HALF_UP)
            u=dict(row=row,offer=offer,variant=variant,base_eur=str(base),observed_at=datetime.now(timezone.utc).isoformat())
        except Exception as e:
            return None,reasons,dict(source=tag,product_id=feed.get("id"),error=type(e).__name__,http_status=getattr(e,"code",None))
        return u,reasons,None
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for n,(u,reasons,error) in enumerate(pool.map(verify,sorted(candidates,key=lambda x:(x[0],x[1],x[2]["id"]))),1):
            held.update(reasons)
            if error:report["errors"].append(error)
            if u:
                cid=u["row"]["card_id"];variant=u["variant"]
                if cid in selected:
                    previous=selected[cid]
                    if previous is None:pass
                    elif previous["variant"]==variant:pass
                    elif previous["variant"]==REVERSE and variant.get("foil") in ("pokeball","masterball"):selected[cid]=u
                    elif variant==REVERSE and previous["variant"].get("foil") in ("pokeball","masterball"):pass
                    else:selected[cid]=None;held["conflicting_retail_finish"]+=1
                else:selected[cid]=u
            if n%50==0:
                report.update(checked=n,matched=sum(u is not None for u in selected.values()),updates=[u for u in selected.values() if u],rejected=dict(held))
                ja.write_report(args.report,report)
                print(json.dumps(dict(checked=n,total=len(candidates),matched=report["matched"],errors=len(report["errors"]))),flush=True)
    for tag in tags:
        if bulk.get(bulk.SHOPS[tag]["host"]+"/cart.js").get("currency")!="JPY":report["errors"].append(dict(source=tag,error="currency_changed_during_run"))
    updates=[u for u in selected.values() if u]
    report.update(complete=True,checked=len(candidates),matched=len(updates),updates=updates,rejected=dict(held))
    report["import_gate"]=manual_gate.import_gate(updates,ja.retail.db,missing_only=args.missing_only,errors=report["errors"])
    if args.apply and report["import_gate"]["allowed"]:
        batches=defaultdict(list)
        for u in updates:batches[(u["offer"]["source"],u["offer"]["printing"])].append(u)
        for (source,printing),batch in sorted(batches.items()):
            report["applied"][source+"/"+printing]=ja.apply_updates(batch,source,missing_only=args.missing_only,variant=VARIANTS[printing])
    ja.write_report(args.report,report);print(json.dumps({k:v for k,v in report.items() if k!="updates"}),flush=True)
    if report["errors"]:raise SystemExit(1)
    if args.apply and args.missing_only and not report["import_gate"]["allowed"]:raise SystemExit(2)
if __name__=="__main__":main()

