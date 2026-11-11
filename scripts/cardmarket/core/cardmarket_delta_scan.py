#!/usr/bin/env python3
"""Guide change-detection gate for a *later* weekly Cardmarket browser queue.

Fail-closed:
* A product-wide guide change is not a fresh DE/EN/NM price.
* Independently human-confirmed standard print + same-product complete
  language-filtered NM browser evidence from <=28 days is required.
* No modifications to tcg_price_cache.updated_at or tcg_price_history.
* Unpriced, high-value, special, manually requested and uncertain rows scan.
* The new guide snapshot becomes next week's comparison baseline even if
  there were no eligible skips. No first-run speculative skipping.
* Never mutate queues while their Windows scanner is actively running.
"""
from __future__ import annotations
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse,csv,fcntl,json,os,re,subprocess,tempfile
from collections import Counter
from datetime import datetime,timezone,timedelta
from decimal import Decimal,InvalidOperation
from pathlib import Path
from cardmarket_game_profile import load_game_profile
from price_feed_client import fetch_json

BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
STATE=BASE/'cardmarket-guide-delta-state.json'
MAX_AGE_DAYS=28
THRESHOLD=Decimal('0.10')
HIGH_VALUE=Decimal('15')
def parsed_time(value):
    if not value:return None
    try:
        x=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except (ValueError,TypeError):return None

def positive_decimal(value):
    if isinstance(value,bool):return None
    try:
        x=Decimal(str(value))
        return x if x.is_finite() and x>0 else None
    except (InvalidOperation,ValueError,TypeError):return None

def is_plain_standard(row):
    return (str(row.get('drucktyp') or '').casefold() in ('normal','nonholo','common')
       and not str(row.get('foil') or '').strip()
       and not str(row.get('sonderdruck') or '').strip()
       and str(row.get('stempel') or '') in ('','[]','null'))

def guide_pair(item):
    if not isinstance(item,dict):return None
    a=positive_decimal(item.get('avg30'))
    t=positive_decimal(item.get('trend'))
    if a is None or t is None:return None
    return {'avg30':str(a),'trend':str(t)}

def percent_change(old,new):
    prev=guide_pair(old);today=guide_pair(new)
    if not prev or not today:return None
    return max(abs(Decimal(today[k])-Decimal(prev[k]))/Decimal(prev[k])
               for k in ('avg30','trend'))

def load_verified_browser_evidence(path):
    """Latest event per variant; old successful event cannot bypass a newer failure."""
    latest={}
    if path.exists():
        with path.open(encoding='utf-8-sig') as f:
            for line in f:
                try:
                    obj=json.loads(line)
                    key=(str(obj['card_id']),str(obj['variant_id']))
                    latest[key]=obj
                except (KeyError,ValueError,TypeError):continue
    return latest

def can_skip(row,cache,observation,old,new,now,previous_guide_time,current_guide_time,language):
    """Return reason, or None. Treat all missing/ambiguous fields as scan."""
    if not is_plain_standard(row):return None
    if str(row.get('manual_scan_requested_at') or '').strip():return None
    if str(row.get('needs_price'))!='NO':return None
    amount=positive_decimal(cache.get('price'))
    if (cache.get('status')!='PRICE_FOUND' or amount is None
        or amount>=HIGH_VALUE):return None
    if not (cache.get('manual_confirmed') is True and
            cache.get('primary_provider')=='CARDMARKET' and
            cache.get('verification_state')=='VERIFIED_PRODUCT_ID'):return None
    product=str(cache.get('product_id') or '')
    if not re.fullmatch('[0-9]{4,12}',product):return None
    if str(cache.get('selected_product_id') or '')!=product:return None
    ids=[p for p in str(row.get('cardmarket_ids') or '').split(',') if p]
    if ids!=[product]:return None
    if not (isinstance(observation,dict)
            and observation.get('language')==language
            and observation.get('identity_confirmed') is True
            and observation.get('all_pages_complete') is True
            and observation.get('status')=='COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED'
            and str(observation.get('product_id'))==product
            and not observation.get('pagination_failure')
            and positive_decimal(observation.get('verified_lang_nm_offers')) is not None
            and str(observation.get('access_mode'))=='AUTHENTICATED'):
        return None
    when=parsed_time(observation.get('seen_at'))
    if not when or when>now+timedelta(minutes=5) or now-when>=timedelta(days=MAX_AGE_DAYS):
        return None
    if (not previous_guide_time or not current_guide_time or
        current_guide_time<=previous_guide_time or
        current_guide_time>now+timedelta(days=1) or
        now-current_guide_time>timedelta(days=2) or
        now-previous_guide_time>timedelta(days=28)):
        return None
    change=percent_change(old,new)
    if change is None or change>=THRESHOLD:return None
    return 'GUIDE_STABLE_STANDARD_LAST_VERIFIED_WITHIN_28D'

def db_evidence(language):
    if language not in ('de','en'):raise ValueError('unsupported language')
    sql="""SELECT COALESCE(json_agg(x),'[]'::json)::text FROM (
      SELECT p.card_id,p.variant_id,p.resolution_status AS status,
        p.base_eur AS price,route.primary_provider,
        route.verification_state,route.provider_product_id AS product_id,
        review.selected_product_id,
        (review.status='CONFIRMED_PRINT') AS manual_confirmed
      FROM tcg_price_cache p
      LEFT JOIN price_source_routing route ON route.card_id=p.card_id
         AND route.variant_id=p.variant_id AND route.language_code=p.language_code
      LEFT JOIN cardmarket_print_identity_review review ON review.card_id=p.card_id
         AND review.variant_id=p.variant_id AND review.language_code=p.language_code
      WHERE p.language_code='%s'
    ) x"""%language
    p=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-qAt','-v','ON_ERROR_STOP=1',
      '-U','cardyssey','-d','cardyssey','-c',sql],capture_output=True,text=True,timeout=45)
    if p.returncode:raise RuntimeError('DB evidence unavailable: '+p.stderr[-250:])
    a=json.loads(p.stdout.strip() or '[]')
    return {(str(x['card_id']),str(x['variant_id'])):x for x in a}

def compile_guide(feed):
    rows=feed.get('priceGuides')
    if not isinstance(rows,list) or len(rows)<50000:raise ValueError('incomplete guide')
    date=parsed_time(feed.get('createdAt'))
    if not date:raise ValueError('undated guide')
    entries={}
    for obj in rows:
        pid=str(obj.get('idProduct') or '')
        if pid.isdigit():
            item=guide_pair(obj)
            if item:
                if pid in entries and entries[pid]!=item:
                    raise ValueError('conflicting duplicate product guide')
                entries[pid]=item
    if len(entries)<10000:raise ValueError('guide price coverage incomplete')
    return {'createdAt':date.isoformat(),'gameId':6,'products':entries}

def evaluate(rows,cache,latest,old_guide,new_guide,now,language):
    result=[];reasons=Counter()
    prev=parsed_time((old_guide or {}).get('createdAt'))
    current=parsed_time(new_guide.get('createdAt'))
    if (old_guide or {}).get('gameId') not in (6,None) or new_guide.get('gameId')!=6:
        raise ValueError('wrong game guide')
    old_prices=(old_guide or {}).get('products') or {}
    new_prices=new_guide['products']
    for original in rows:
        row=dict(original)
        row['delta_browser_skip']='NO'
        row['delta_reason']=''
        # This flag may only DISABLE extra browser work; it can NEVER turn a
        # missing price into PRICE_FOUND or mark an S3 value as a DE price.
        key=(row['cardyssey_karte'],row['variante_id'])
        state=cache.get(key,{})
        pid=str(state.get('product_id') or '')
        accepted=can_skip(row,state,latest.get(key),old_prices.get(pid),
                          new_prices.get(pid),now,prev,current,language)
        if accepted:
            row['delta_browser_skip']='YES'
            row['delta_reason']=accepted
            row['needs_price']='NO'
            reasons['guide_stable_skip']+=1
        else:reasons['scan_or_existing_feed_policy']+=1
        result.append(row)
    if len(result)!=len(rows):raise AssertionError('lost queue rows')
    return result,dict(reasons)

def lock_queue_active(base,now):
    """Windows progress is maintained per card, so a recent RUNNING state blocks writes."""
    for language in ('de','en'):
        p=base/f'progress-{language}.json'
        if not p.exists():continue
        try:progress=json.loads(p.read_text(encoding='utf-8-sig'))
        except (ValueError,OSError):raise RuntimeError('unreadable scan progress')
        if (progress.get('status')=='RUNNING' and
            (last:=parsed_time(progress.get('updated_at'))) and
            now-last<timedelta(minutes=15)):
            raise RuntimeError('active scanner: do not regenerate weekly queue')

def write_atomic(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='cm-delta-',suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(content);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def apply(base=BASE,feed=None,old=None,cache_by_language=None,now=None,dry_run=True):
    now=now or datetime.now(timezone.utc)
    profile=load_game_profile()
    if profile['game_id']!=6:raise ValueError('unsupported TCG for existing Cardyssey IDs')
    current=compile_guide(feed if feed is not None else fetch_json(profile['price_url'],max_age=20*3600))
    old=old if old is not None else (
        json.loads((base/'cardmarket-guide-delta-state.json').read_text(encoding='utf-8-sig'))
        if (base/'cardmarket-guide-delta-state.json').exists() else None)
    if old and old.get('gameId')!=6:raise ValueError('incompatible previous guide')
    if not dry_run:lock_queue_active(base,now)
    output={}
    new_queues={}
    for lang in ('de','en'):
        path=base/f'queue-{lang}.csv'
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);fields=list(reader.fieldnames or []);rows=list(reader)
        if not rows:raise ValueError('empty '+lang+' queue')
        if 'delta_browser_skip' not in fields:fields+=['delta_browser_skip','delta_reason']
        db=(cache_by_language or {}).get(lang) if cache_by_language is not None else db_evidence(lang)
        latest=load_verified_browser_evidence(base/f'browser-observations-{lang}.jsonl')
        amended,stats=evaluate(rows,db,latest,old,current,now,lang)
        keys={(r['cardyssey_karte'],r['variante_id']) for r in amended}
        if len(keys)!=len(rows):raise ValueError('duplicate queue keys')
        import io
        buf=io.StringIO(newline='')
        writer=csv.DictWriter(buf,fieldnames=fields);writer.writeheader();writer.writerows(amended)
        new_queues[lang]=buf.getvalue().encode('utf-8-sig')
        output[lang]={'queueRows':len(rows),'safeSkips':stats.get('guide_stable_skip',0),
                      'scanOrOriginalPolicy':stats.get('scan_or_existing_feed_policy',0)}
    # Atomic within each file, no combined rewrite; do NOT apply during
    # active scanner runs. Weekly job is scheduled during maintenance.
    if not dry_run:
        for lang in ('de','en'):
            write_atomic(base/f'queue-{lang}.csv',new_queues[lang])
        write_atomic(base/'cardmarket-guide-delta-state.json',
                    (json.dumps(current,ensure_ascii=False,separators=(',',':'))+'\n').encode())
    return {'mode':'DRY_RUN' if dry_run else 'APPLIED',
            'guideDate':current['createdAt'],
            'previousGuideDate':(old or {}).get('createdAt'),
            'cacheTouched':False,'pricesPublished':0,
            'priceUpdatedAtTouched':False,'languages':output}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    print(json.dumps(apply(dry_run=not args.apply),ensure_ascii=False))
