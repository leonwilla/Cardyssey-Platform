#!/usr/bin/env python3
"""Recover Korean C/U prints using pinned native identity and independent artwork.

Blueprint artwork establishes the card rather than assuming translated names.
Only explicit Korean NM/Mint single-card EUR offers supply the price. No
Japanese quotation is transferred. Ambiguous catalogue/blueprint prints stay held.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
from PIL import Image,ImageChops,ImageStat

spec=importlib.util.spec_from_file_location('reader',Path(__file__).with_name('resolve-cardtrader-ko-nm-prices.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Two disjoint illustrated patches avoid native title/rules and the official
# diagonal watermark. This route cannot establish foils/full-art/rare prints.
PATCHES=((20,45,195,92),(20,92,58,132))
MAX_ERROR=6.0
MIN_RIVAL_ERROR=18.0
MIN_RATIO=4.0
CACHE=Path('/home/tv/.cache/cardyssey-catalog/source')


def pinned_record(row,raw,revision):
    url=row.get('source_url','');hit=re.fullmatch(r'https://pokemoncard\.co\.kr/cards/detail/([A-Za-z0-9]+)',url)
    if not hit or row.get('source_revision')!=revision or row.get('identity_count')!=1:return None
    if row.get('language_code')!='ko' or row.get('rarity') not in ('C','U') or not m.regular_set(row.get('set_id')):return None
    if row.get('card_id')!='official_ko_'+hashlib.sha256(url.encode()).hexdigest()[:24]:return None
    for key,value in [('url',url),('ko_id',hit[1]),('lang','ko'),('name',row.get('native_name')),('img',row.get('image_source_url')),('set_name',row.get('set_id')),('rarity',row.get('rarity'))]:
        if raw.get(key)!=value:return None
    if str(raw.get('number'))!=row.get('local_id') or not str(raw.get('set_total','')).isdigit() or int(raw['set_total'])<=0:return None
    return dict(row,official_count=int(raw['set_total']))


def load_targets():
    sql="""WITH counts AS(SELECT set_id,LTRIM(local_id,'0') num,COUNT(*) identity_count FROM catalog_cards_mirror WHERE language_code='ko' GROUP BY set_id,LTRIM(local_id,'0'))
    SELECT COALESCE(jsonb_agg(to_jsonb(t)),'[]') FROM(SELECT c.card_id,c.language_code,c.set_id,c.local_id,c.rarity,c.raw_payload->>'name' native_name,c.image_source_url,c.variants old_variants,counts.identity_count,p.updated_at old_updated,p.resolution_status old_status,s.source_url,s.source_revision
      FROM catalog_cards_mirror c JOIN counts ON counts.set_id=c.set_id AND counts.num=LTRIM(c.local_id,'0')
      LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code='ko' AND p.variant_id='generated'
      JOIN LATERAL(SELECT MIN(source_url) source_url,MIN(source_revision) source_revision FROM catalog_supplemental_cards s WHERE s.canonical_card_id=c.card_id AND s.language_code='ko' HAVING COUNT(DISTINCT source_url)=1 AND COUNT(DISTINCT source_revision)=1)s ON TRUE
      WHERE c.language_code='ko' AND c.details_complete AND c.local_id~'^[0-9]+$' AND c.rarity IN('C','U') AND counts.identity_count=1
      AND c.variants='[]'::jsonb AND (p.card_id IS NULL OR p.resolution_status='NO_PRICE')
      AND NOT EXISTS(SELECT 1 FROM tcg_price_cache priced WHERE priced.card_id=c.card_id AND priced.base_eur>0))t;"""
    rows=json.loads(m.ko.retail.db(sql));revision=subprocess.run(['git','-C',str(CACHE),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    needed={r['source_url'] for r in rows};records={};duplicate=set()
    for p in (CACHE/'data_ko').rglob('*.json'):
        raw=json.loads(p.read_text());url=raw.get('url')
        if url not in needed:continue
        if url in records:duplicate.add(url)
        records[url]=raw
    verified=[]
    for row in rows:
        if row['source_url'] in duplicate:continue
        hit=pinned_record(row,records.get(row['source_url'],{}),revision)
        if hit:verified.append(hit)
    return verified


def blueprint_matches(row,bp,e):
    if row.get('rarity') not in ('C','U') or row.get('identity_count')!=1:return False
    if e.get('game_id')!=5 or m.ko.normalize(e.get('code',''))!=m.ko.normalize(row['set_id']):return False
    if bp.get('game_id')!=5 or bp.get('category_id')!=73 or bp.get('expansion_id')!=e['id']:return False
    f=bp.get('fixed_properties') or {};n=str(f.get('collector_number',''))
    if not n.isdigit() or int(n)!=int(row['local_id']) or f.get('pokemon_rarity') not in m.RARITY[row['rarity']]:return False
    # A bare number/denominator describes the ordinary C/U blueprint. Any
    # extra finish/edition/version label is held rather than guessed away.
    version=re.fullmatch(r'(\d+)/(\d+)',str(bp.get('version','')))
    if not version or tuple(map(int,version.groups()))!=(int(row['local_id']),row['official_count']):return False
    language=[p for p in bp.get('editable_properties',[]) if p.get('name')=='pokemon_language']
    return len(language)==1 and 'kr' in language[0].get('possible_values',[])


def image_url(bp):
    path=(bp.get('image') or {}).get('url','')
    if not isinstance(path,str) or not path.startswith('/uploads/blueprints/image/') or '..' in path:return None
    return 'https://cardtrader.com'+urllib.parse.quote(path,safe='/()-_.')


def prepare(data):
    with Image.open(__import__('io').BytesIO(data)) as image:
        w,h=image.size
        if w<300 or h<400 or not .69<w/h<.73:raise ValueError('incomplete card render')
        return image.convert('RGB').resize((217,303),Image.Resampling.LANCZOS)


def score(a,b):
    return [sum(ImageStat.Stat(ImageChops.difference(a.crop(p),b.crop(p))).mean)/3 for p in PATCHES]


def separated(selected,rivals):
    return len(selected)==len(PATCHES) and bool(rivals) and all(0<=x<=MAX_ERROR for x in selected) and all(len(r)==len(PATCHES) and all(x>=MIN_RIVAL_ERROR and x>=MIN_RATIO*max(best,.1) for best,x in zip(selected,r)) for r in rivals)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--report',type=Path,required=True);parser.add_argument('--inventory-dir',type=Path,required=True)
    args=parser.parse_args();rows=load_targets();bycode=defaultdict(list)
    for row in rows:bycode[m.ko.normalize(row['set_id'])].append(row)
    raw=[json.loads(p.read_text()) for p in args.inventory_dir.glob('*.json')];expindex=defaultdict(list)
    for d in raw:expindex[m.ko.normalize(d['expansion'].get('code',''))].append(d)
    selected=[];held=Counter();errors=[];image_failures=[]
    for code,group in bycode.items():
        hits=expindex[code]
        if len(hits)!=1:held['expansion_missing_or_ambiguous']+=len(group);continue
        d=hits[0];e=d['expansion'];candidates=[]
        for row in group:
            bp=[b for b in d['blueprints'] if blueprint_matches(row,b,e)]
            if len(bp)!=1:held['blueprint_missing_or_ambiguous']+=1;continue
            if not any(m.listing_amount(p,bp[0],e) is not None for p in d['products'].get(str(bp[0]['id']),[])):held['checkpoint_without_qualifying_offer']+=1;continue
            candidates.append(row)
        if candidates:selected.append((e,candidates))
    token=next((s.split('=',1)[1].strip() for s in Path('/home/tv/cardshop/platform/.env').read_text().splitlines() if s.startswith('CARDTRADER_API_TOKEN=')),'');assert token
    last=0
    def get(path):
        nonlocal last
        time.sleep(max(0,1.1-(time.monotonic()-last)));last=time.monotonic()
        request=urllib.request.Request(m.BASE+path,headers={'Authorization':'Bearer '+token,'Accept':'application/json','User-Agent':'Cardyssey/0.5 Korean-native-art-proof'})
        with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
    work=args.report.parent/(args.report.stem+'-images');work.mkdir(exist_ok=True)
    def download(url):
        host=urllib.parse.urlsplit(url).hostname
        if urllib.parse.urlsplit(url).scheme!='https' or host not in ('cardtrader.com','cards.image.pokemonkorea.co.kr','pokemoncard.co.kr'):raise ValueError('untrusted image host')
        path=work/(hashlib.sha256(url.encode()).hexdigest()+'.img')
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Cardyssey/0.5 exact-print-proof'}),timeout=25) as response:
                data=response.read(12*1024*1024+1)
            if len(data)>12*1024*1024:raise ValueError('oversized image')
            path.write_bytes(data)
        data=path.read_bytes();return prepare(data),hashlib.sha256(data).hexdigest()
    report=dict(complete=False,pinned_targets=len(rows),expansions=len(selected),checked=0,matched=0,updates=[],rejected=dict(held),errors=[],image_failures=[],applied=dict(variants=0,prices=0,history=0));m.write_report(args.report,report)
    updates=[]
    for e,group in selected:
        try:
            bp=get('/blueprints/export?expansion_id='+str(e['id']));products=get('/marketplace/products?expansion_id='+str(e['id'])+'&language=kr')
            if not isinstance(bp,list) or not isinstance(products,dict):raise ValueError('provider payload')
        except Exception as exc:
            errors.append(dict(expansion=e['id'],error=type(exc).__name__,http_status=getattr(exc,'code',None)))
            if getattr(exc,'code',None) in (401,403,429):break
            continue
        for row in group:
            report['checked']+=1
            matches=[b for b in bp if blueprint_matches(row,b,e)]
            if len(matches)!=1:held['live_blueprint_missing_or_ambiguous']+=1;continue
            b=matches[0];offers=[(m.listing_amount(p,b,e),p) for p in products.get(str(b['id']),[]) if m.listing_amount(p,b,e) is not None]
            if not offers:held['live_no_korean_nm_single']+=1;continue
            amount,p=min(offers,key=lambda x:(x[0],x[1]['id']))
            if amount>100:held['high_asking_price_review']+=1;continue
            # Independent negative controls: nearest three ordinary C/U card
            # blueprints with other printed numbers, same expansion/denominator.
            rivals=[]
            for rival in bp:
                f=rival.get('fixed_properties') or {};num=str(f.get('collector_number',''))
                v=re.fullmatch(r'(\d+)/(\d+)',str(rival.get('version','')))
                if rival['id']!=b['id'] and rival.get('game_id')==5 and rival.get('category_id')==73 and num.isdigit() and v and int(v[2])==row['official_count'] and f.get('pokemon_rarity') in ('Common','Uncommon') and image_url(rival):rivals.append(rival)
            rivals=sorted(rivals,key=lambda r:(abs(int(r['fixed_properties']['collector_number'])-int(row['local_id'])),r['id']))[:3]
            if len(rivals)<3 or not image_url(b):held['insufficient_image_controls']+=1;continue
            try:
                native,ndigest=download(row['image_source_url']);image,digest=download(image_url(b));best=score(native,image);controls=[]
                for rival in rivals:
                    other,odigest=download(image_url(rival));controls.append(dict(blueprint_id=rival['id'],url=image_url(rival),sha256=odigest,scores=score(native,other)))
                if not separated(best,[x['scores'] for x in controls]):held['artwork_not_distinct']+=1;continue
                offer=dict(source=m.SOURCE,currency='EUR',amount=str(amount),url='https://www.cardtrader.com/cards/'+str(b['id']),title=b['name']+' | '+b['version'],blueprint_id=b['id'],expansion_id=e['id'],product_id=p['id'],condition=p['properties_hash']['condition'],language='kr',rarity=row['rarity'],printing='ordinary',qualifying_offers=len(offers),identity_method='pinned-unique-official-Korean-CU/set-number-denominator-rarity/two-art-patches/three-negative-controls/explicit-Korean-NM-single',basis_description='lowest qualifying in-stock single-card asking offer',primary_url=row['source_url'],source_record_revision=row['source_revision'],image_evidence=dict(native_url=row['image_source_url'],native_sha256=ndigest,blueprint_url=image_url(b),blueprint_sha256=digest,normalized_size=[217,303],patches=PATCHES,scores=best,controls=controls,max_error=MAX_ERROR,min_rival_error=MIN_RIVAL_ERROR,min_ratio=MIN_RATIO))
                updates.append(dict(row=row,offer=offer,observed_at=datetime.now(timezone.utc).isoformat(),base_eur=str((amount/m.ko.retail.NM_FACTOR).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP))))
            except Exception as exc:
                # No update is created for this card. Its failed image proof
                # cannot invalidate independently completed proofs on other cards.
                held['image_validation_failed']+=1
                image_failures.append(dict(card_id=row['card_id'],error=type(exc).__name__,detail=str(exc),http_status=getattr(exc,'code',None)))
        report.update(matched=len(updates),updates=updates,rejected=dict(held),errors=errors,image_failures=image_failures);m.write_report(args.report,report)
        print(json.dumps(dict(set=e['code'],checked=report['checked'],matched=len(updates),errors=len(errors))),flush=True)
    report.update(complete=not errors,errors=errors,image_failures=image_failures,rejected=dict(held),import_gate=m.missing.import_gate(updates,m.ko.retail.db,missing_only=True,errors=errors))
    if args.apply and report['import_gate']['allowed']:report['applied']=m.ko.apply_updates(updates,m.SOURCE,missing_only=True)
    m.write_report(args.report,report);print(json.dumps({k:v for k,v in report.items() if k!='updates'}),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
