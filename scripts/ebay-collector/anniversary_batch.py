#!/usr/bin/env python3
"""Resumable, serial DE 30th anniversary collection and conservative cache import."""
import argparse,collections,fcntl,json,os,re,statistics,subprocess,time
from datetime import date,datetime,timezone,timedelta
from pathlib import Path
from import_preview import db,sql
from ebay_sold import atomic_json
from price_history import save_sales, stored_sales, choose_median
from incremental_scan import scan_window,mark_success
from offer_references import store_offer_candidates
from purchase_history import audit_purchase_history

ROOT=Path(__file__).resolve().parent
QUERY="""SELECT jsonb_agg(to_jsonb(c) ORDER BY priority,card_id) FROM (
 SELECT card_id,name,local_id,set_id,variants,
 CASE WHEN set_id='mep' THEN 0 WHEN set_id='30th-c' THEN 1 ELSE 2 END AS priority
 FROM catalog_cards_mirror WHERE language_code='de' AND
 (set_id IN ('30th','30th-c') OR (set_id='mep' AND local_id BETWEEN '094' AND '101'))
) c;"""
def search_query(card):
    """Search by print identity, not the generic Pokémon name and ordinal alone.

    eBay ignores generic terms such as `pokemon` and matches unrelated cards if
    queried for `Glurak 1 pokemon`. Include the printed number, denominator
    and distinct promo prefix to increase exact matches before filtering.
    """
    number=str(card['local_id'])
    if card['set_id']=='mep':
        return f"{card['name']} MEP {int(number):03d} deutsch"
    if card['set_id']=='30th-c':
        return f"{card['name']} {int(number):03d}/030 30 Jahre"
    if card['set_id'] not in ('30th','30th-c','mep'):
        return f"{card['name']} {int(number):03d}/{int(card['denominator'])} {card['set_name']} deutsch"
    return f"{card['name']} {int(number):03d}/128 30 Jahre"

def exact_number(title,card):
    if not str(card['local_id']).isdigit():
        return False
    num=int(card['local_id'])
    if card['set_id']=='mep':
        return bool(re.search(r'\bMEP[ -]?0*'+str(num)+r'(?![\w/])',title,re.I) or re.search(r'\b(?:MEP|Mega Entwicklung Promo)[ -]+0*'+str(num)+r'(?![\w/])',title,re.I)) and not bool(re.search(r'\b(?:SVP|SWSH|SM)[ -]?0*'+str(num)+r'(?![\w/])',title,re.I))
    denominator=30 if card['set_id']=='30th-c' else int(card.get('denominator',128))
    if num > denominator:
        return False
    if re.search(r'(?<![\w/])0*'+str(num)+r'\s*/\s*0*'+str(denominator)+r'(?!\w)',title):
        return True
    # Modern eBay titles often use "#64" or "Nr. 64" without the printed
    # denominator. Accept only when BOTH the set identity and exact number
    # are explicit. Never accept bare "64" or a conflicting slash number.
    if card['set_id'] not in ('sv01','sv02'):
        return False
    if re.search(r'(?<![\w/])\d+\s*/\s*\d+(?!\w)',title):
        return False
    set_name=card.get('set_name','')
    set_codes=('SVI','SV01') if card['set_id']=='sv01' else ('PAL','SV02')
    if not ((set_name and set_name.casefold() in title.casefold()) or
            any(re.search(r'(?<!\w)'+re.escape(code)+r'(?!\w)',title,re.I) for code in set_codes)):
        return False
    markers=re.findall(r'(?<!\w)(?:#|nr\.?\s*|no\.?\s*)(0*\d{1,3})(?!\w)',title,re.I)
    return len(markers)==1 and int(markers[0])==num

def contradictory_print_or_multi_card(title,card):
    # Do not confuse one card with collection sets, lots or multiple numbered prints.
    if re.search(r'\b(?:komplettset|komplett[ -]?set|complete[ -]?set|full[ -]?set|master[ -]?set|30\s+karten|mehrere\s+karten|konvolut|sammlung|kartenpaket|lot|bundle|auswahl|aussuchen|auswählen|einzelkarten|choose|select\s+your|pick\s+your)\b',title,re.I):
        return True
    denominator=int(card.get('denominator',128))
    numbers=re.findall(r'(?<![\w/])(\d{1,3})\s*/\s*0*'+str(denominator)+r'(?!\w)',title)
    if card['set_id']!='mep':
        if any(int(n)!=int(card['local_id']) for n in numbers):return True
        # Multiple printed card numbers in one sale title are not single-card evidence.
        all_numbers=re.findall(r'(?<![\w/])\d{1,3}\s*/\s*\d{2,3}(?!\w)',title)
        if len(set(all_numbers))>1:return True
    # Explicitly conflicting MEP codes in a single listing indicate ambiguous identity.
    promos=re.findall(r'\bMEP[ -]?(\d{2,3})(?![\w/])',title,re.I)
    if card['set_id']=='mep' and any(int(n)!=int(card['local_id']) for n in promos):return True
    return False

def explicit_print_variant(title):
    """Only explicit print words qualify; generic Holo is not a Normal print."""
    reverse=bool(re.search(r'\breverse(?:[ -]?holo)?\b',title,re.I))
    normal=bool(re.search(r'\b(?:normal(?:druck)?|non[- ]?holo|nicht[- ]?holo)\b',title,re.I))
    if reverse and normal:return None
    return 'REVERSE' if reverse else 'NORMAL' if normal else None

def audit_listing_images(report,card):
    """Verify card ART identity with two adjacent-print negative controls.

    Only a positive high-confidence score can replace a missing printed number.
    Language, NM condition, single-card sale, and print variant remain independent
    requirements. This cannot certify physical foil or card condition.
    """
    if card['set_id'] not in ('sv01','sv02') or not str(card['local_id']).isdigit():
        return report
    number=int(card['local_id'])
    reference=f"https://assets.tcgdex.net/de/sv/{card['set_id']}/{number:03d}/high.webp"
    negatives=[f"https://assets.tcgdex.net/de/sv/{card['set_id']}/{n:03d}/high.webp"
               for n in (number-1,number+1) if 1<=n<=int(card.get('denominator',193))]
    candidates=[]
    for r in report.get('rows',[]):
        if len(candidates)>=8:break
        title=r.get('title','')
        if (not r.get('image_url') or exact_number(title,card) or
            not all(re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',title,re.I) for t in card['name'].split()) or
            contradictory_print_or_multi_card(title,card)):
            continue
        candidates.append({'id':r['item_id'],'url':r['image_url']})
    if not candidates:return report
    script=ROOT.parent/'cardshop'/'scripts'/'ebay-collector'/'image-compare.mjs'
    if not script.is_file():
        script=Path('/home/tv/cardshop/scripts/ebay-collector/image-compare.mjs')
    try:
        process=subprocess.run(['node',str(script)],input=json.dumps(dict(reference=reference,
            negativeReferences=negatives,items=candidates)),capture_output=True,text=True,timeout=110)
        if process.returncode!=0:raise ValueError('COMPARISON_FAILED')
        audit=json.loads(process.stdout)
        results={r['id']:r for r in audit.get('items',[])}
        for row in report.get('rows',[]):
            comparison=results.get(row.get('item_id'))
            if comparison:
                row['image_match_score']=comparison.get('edge')
                row['image_competing_score']=comparison.get('competingEdge')
                row['image_match_margin']=comparison.get('margin')
                row['image_identity_verified']=comparison.get('verified') is True
        report['imageAudit']={'status':'COMPLETE','tested':len(results),
            'verified':sum(r.get('verified') is True for r in results.values()),
            'scope':'art_only_no_variant_condition_verification'}
    except (OSError,ValueError,subprocess.TimeoutExpired):
        report['imageAudit']={'status':'UNAVAILABLE','tested':0,'verified':0}
    return report

def select_rows(report,card):
    rejected=collections.Counter();found={}
    for r in report.get('rows',[]):
        reason=None;title=r['title']
        if not r.get('eligible') or r.get('language')!='de':reason='COLLECTOR_REJECTED'
        elif not (exact_number(title,card) or (r.get('image_identity_verified') is True
                and not re.search(r'(?<![\w/])\d+\s*/\s*\d+(?!\w)',title))):
            reason='CARD_NUMBER_OR_SET_UNCLEAR'
        elif not all(re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',title,re.I) for t in card['name'].split()):reason='NAME_MISMATCH'
        elif (contradictory_print_or_multi_card(title,card)
              or re.search(r'jumbo|oversiz|sealed|versiegelt|\b(?:bundle|lot|konvolut|mehrere karten|[2-9]x)\b|\s\+\s',title,re.I)
              or (card['set_id'] not in ('sv01','sv02') and re.search(r'reverse|non.?holo|nicht.?holo',title,re.I))):
            reason='OTHER_PRINT_OR_SEALED'
        elif r.get('condition')=='conflict':reason='CONDITION_CONFLICT'
        elif not r.get('sold_date') or not date.fromisoformat(r['sold_date'])<=date.today():reason='SALE_DATE_INVALID'
        elif not 0<float(r.get('price_eur') or 0)<100000:reason='PRICE_INVALID'
        if reason:rejected[reason]+=1
        else:
            r['condition_assumed']=r.get('condition')=='unknown'
            r['history_condition']='NEAR_MINT' if r.get('condition') in ('unknown','nm','mint') else str(r.get('condition')).upper()
            found[r['item_id']]=r
    return sorted(found.values(),key=lambda r:(r['sold_date'],r['item_id']),reverse=True),dict(rejected)

def import_result(report,card,directory):
    rows,reasons=select_rows(report,card)
    outcome={'card_id':card['card_id'],'name':card['name'],'set_id':card['set_id'],
             'parsed':len(report.get('rows',[])),'nm_candidates':len(rows),'rejections':reasons}
    variants=card['variants']
    if card['set_id']!='mep' and (not str(card['local_id']).isdigit() or int(card['local_id']) > int(card.get('denominator',128))):
        return outcome|{'status':'SET_NUMBER_REVIEW'}
    if not report.get('pages') or report['pages'][-1]['status']!='OK':
        return outcome|{'status':'FETCH_INCOMPLETE'}
    if len(rows)<1:return outcome|{'status':'NO_MATCHING_SALES'}
    # Assign every sold individual listing to a catalog print. Unmarked
    # modern-set singles are assumed Normal; reverse/holo must be explicit.
    by_variant={}
    for row in rows:
        hint=explicit_print_variant(row['title'])
        if len(variants)==1 and variants[0].get('id')!='generated':
            selected=variants[0]
            # A title naming a conflicting print must not be silently accepted.
            if hint and selected.get('legacyVariant') in ('NORMAL','REVERSE') and hint!=selected['legacyVariant']:
                continue
        else:
            if hint is None:
                # A bare "Holo" is not safely identifiable as a Normal print.
                if re.search(r'\bholo\b',row['title'],re.I):continue
                hint='NORMAL'
            matches=[v for v in variants if v.get('legacyVariant')==hint and v.get('id')!='generated']
            if len(matches)!=1:continue
            selected=matches[0]
        match=by_variant.setdefault(selected['id'],[])
        row['variant_assumed']=row.get('variant_assumed') if row.get('source')=='EBAY_PURCHASE_HISTORY' else explicit_print_variant(row['title']) is None
        match.append(row)
    if not by_variant:return outcome|{'status':'CATALOG_VARIANT_REVIEW'}
    card_id=card['card_id']
    current=json.loads(db('SELECT variants FROM catalog_cards_mirror WHERE language_code=\'de\' AND card_id='+sql(card_id)+';'))
    if current!=variants:return outcome|{'status':'CATALOG_CHANGED'}
    imported=[]
    for variant,all_rows in by_variant.items():
        # Keep explicit lower-condition sales in the historic series, but never
        # blend them with the Near Mint market value.
        save_sales(card_id,variant,all_rows)
        existing=stored_sales(card_id,variant)
        calculation=choose_median(existing)
        if not calculation:continue
        recent=calculation['recent_sales']
        sales=[dict(itemId=r['item_id'],title=r['title'],soldPriceEur=float(r['sold_eur']),
            rawCondition='Near Mint (angenommen)' if r.get('condition_assumed') else 'Near Mint (Titel)',
            endedAt=str(r['sold_on'])[:10]+'T00:00:00Z',url=r['url']) for r in recent]
        key='card_id='+sql(card_id)+" AND language_code='de' AND variant_id="+sql(variant)
        backup=directory/('previous-cache-'+re.sub(r'[^a-zA-Z0-9_-]','_',variant)+'.json')
        if not backup.exists():backup.write_text(db("SELECT COALESCE(jsonb_agg(to_jsonb(t)),'[]') FROM ebay_price_cache t WHERE "+key+';'))
        # Cardyssey stores the unconditioned base and applies 0.92 for Near Mint.
        values=','.join(str(round(v/0.92,4)) for v in (calculation['median_eur'],calculation['min_eur'],calculation['max_eur']))
        db('BEGIN; INSERT INTO ebay_price_cache(card_id,language_code,variant_id,source,base_eur,range_low_eur,range_high_eur,sample_count,recent_sales,price_window_days,price_window_label,low_sample,updated_at) VALUES ('+sql(card_id)+",'de',"+sql(variant)+",'CARDYSSEY_EBAY',"+values+','+str(calculation['sample_count'])+','+sql(json.dumps(sales,ensure_ascii=False))+"::jsonb,"+str(calculation['window_days'])+','+sql(calculation['window_label'])+','+('TRUE' if calculation['low_sample'] else 'FALSE')+",NOW()) ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET source=EXCLUDED.source,base_eur=EXCLUDED.base_eur,range_low_eur=EXCLUDED.range_low_eur,range_high_eur=EXCLUDED.range_high_eur,sample_count=EXCLUDED.sample_count,recent_sales=EXCLUDED.recent_sales,price_window_days=EXCLUDED.price_window_days,price_window_label=EXCLUDED.price_window_label,low_sample=EXCLUDED.low_sample,updated_at=NOW(); DELETE FROM ebay_price_refresh_state WHERE "+key+'; COMMIT;')
        imported.append(dict(variant_id=variant,median_eur=calculation['median_eur'],
            sample_count=calculation['sample_count'],window_days=calculation['window_days'],
            window_label=calculation['window_label'],low_sample=calculation['low_sample']))
    audit=outcome|{'status':'IMPORTED' if imported else 'HISTORY_ONLY',
        'variants_imported':imported,'historical_sales_collected':sum(map(len,by_variant.values())),
        'imported_at':datetime.now(timezone.utc).isoformat()}
    atomic_json(directory/'import-audit.json',audit)
    return audit

def recent_verified_report(directory, query, max_hours=24, sold_since=None):
    """Reuse complete, recent sold-page reports instead of re-fetching eBay.

    A prior 30-day client cutoff never deletes historic page observations;
    remove only that obsolete cutoff while preserving all other rejections.
    """
    path=directory/'sales.json'
    if not path.is_file():return None
    try:
        report=json.loads(path.read_text())
        config=report.get('config',{})
        if config.get('query')!=query or config.get('language')!='de' or config.get('sold_since')!=sold_since:return None
        if sold_since and report.get('incremental_boundary_reached') is not True:return None
        if not report.get('pages') or report['pages'][-1].get('status')!='OK':return None
        collected=datetime.fromisoformat(report['collected_at'].replace('Z','+00:00'))
        if not 0 <= (datetime.now(timezone.utc)-collected).total_seconds() <= max_hours*3600:return None
        for row in report.get('rows',[]):
            exclusions=[x for x in str(row.get('exclusions') or '').split(';') if x and x!='SALE_TOO_OLD']
            row['exclusions']=';'.join(exclusions)
            row['eligible']=not exclusions
        report['config']['max_age_days']=36500
        report['reused_recent_sales_page']=True
        return report
    except (ValueError,TypeError,KeyError,OSError):return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'anniversary-20261021');ap.add_argument('--incremental',action='store_true');args=ap.parse_args()
    os.umask(0o077);args.out.mkdir(parents=True,exist_ok=True)
    lock=(ROOT/'.anniversary.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=args.out/'manifest.json'
    if not manifest.exists():atomic_json(manifest,json.loads(db(QUERY)))
    cards=json.loads(manifest.read_text());assert cards and len(cards)<=1000
    statefile=args.out/'progress.json'
    state=json.loads(statefile.read_text()) if statefile.exists() else {'total':len(cards),'results':[]}
    # Re-evaluate earlier runs with the newly requested 30-day / minimum-one rule.
    # Preserve previous results as audit before replacing their results.
    if state.get('pricing_rule') != 'rolling_history_v1':
        audit=args.out/('previous-progress-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
        atomic_json(audit,state)
        state={'total':len(cards),'results':[], 'pricing_rule':'rolling_history_v1', 'status':'RUNNING', 'started_at':time.time(), 'run_start_done':0}
        atomic_json(statefile,state)
    done={r['card_id'] for r in state['results']}
    for card in cards:
        if card['card_id'] in done:continue
        directory=args.out/card['card_id'];directory.mkdir(exist_ok=True)
        if card['set_id']!='mep' and (not str(card['local_id']).isdigit() or int(card['local_id'])>int(card.get('denominator',128))):
            outcome={'card_id':card['card_id'],'name':card['name'],'set_id':card['set_id'],'status':'SET_NUMBER_REVIEW','fetch_status':'SKIPPED','nm_candidates':0}
            state['results'].append(outcome);state.update(status='RUNNING',finished=len(state['results']));state['counts']=dict(collections.Counter(r['status'] for r in state['results']));atomic_json(statefile,state)
            print(json.dumps(outcome,ensure_ascii=False),flush=True)
            continue
        number=card['local_id'] if card['set_id']=='mep' else card['local_id']+'/'+str(30 if card['set_id']=='30th-c' else card.get('denominator',128))
        query=search_query(card)
        since, cursor_source, scan_at=scan_window(card['card_id'],query,args.out) if args.incremental else (None,'FULL_SCAN',None)
        try:
            from price_history import db as _db,sql as _sql
            review=_db('SELECT refresh_days FROM ebay_card_review WHERE card_id='+_sql(card['card_id'])+" AND language_code='de';")
            refresh_days=int(review) if review else 7
        except (OSError,ValueError,subprocess.CalledProcessError):refresh_days=7
        if scan_at and datetime.now(timezone.utc)-scan_at < timedelta(days=refresh_days):
            # A successful manual/weekly lookup less than seven days ago
            # needs no redundant eBay requests, even if another card failed.
            outcome={'card_id':card['card_id'],'name':card['name'],
                     'set_id':card['set_id'],'status':'SKIPPED_RECENT',
                     'fetch_status':'SKIPPED','scan_mode':'INCREMENTAL',
                     'since_date':since,'cursor_source':cursor_source}
            state['results'].append(outcome)
            state.update(status='RUNNING',finished=len(state['results']),checked_at=datetime.now(timezone.utc).isoformat())
            state['counts']=dict(collections.Counter(r['status'] for r in state['results']))
            atomic_json(statefile,state)
            print(json.dumps(outcome,ensure_ascii=False),flush=True)
            continue
        cmd=['bash',str(ROOT/'run-tiny.sh'),'--query',query,'--language','de',
             '--pages',str(5 if since else 1),'--max-age-days','36500','--min-sales','1']
        if since:cmd.extend(['--sold-since',since])
        # Broad discovery must not pre-reject alternate spacing, language or promo identifiers.
        # select_rows enforces language, name, print ID and condition before import.
        env=dict(os.environ,EBAY_OUTPUT_DIR=str(directory),EBAY_LOCK_WAIT='180')
        report=recent_verified_report(directory,query,sold_since=since)
        fetch='OK' if report is not None else 'RUNNER_ERROR'
        if report is None:
            report={}
            for attempt in range(2):
                if attempt:time.sleep(60)
                with (directory/'run.log').open('a') as log:
                    subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
                path=directory/'sales.json'
                report=json.loads(path.read_text()) if path.exists() else {}
                fetch=(report.get('pages') or [{}])[-1].get('status','RUNNER_ERROR')
                if fetch not in ('SERVICE_ERROR','ERROR','RUNNER_ERROR'):break
        if fetch in ('LOGIN_REQUIRED','BLOCKED','WRONG_BROWSER_PROFILE'):
            state.update(status='STOPPED_'+fetch,next_card=card['card_id'],checked_at=datetime.now(timezone.utc).isoformat())
            atomic_json(statefile,state);print(json.dumps({'status':state['status'],'card_id':card['card_id']}),flush=True);return
        if fetch=='OK':
            report=audit_listing_images(report,card)
            atomic_json(directory/'sales.json',report)
        offer_candidates=0
        if fetch=='OK':
            try:offer_candidates=store_offer_candidates(report,card)
            except (OSError,ValueError,subprocess.CalledProcessError):pass
            try:
                report=audit_purchase_history(report,card,cards)
            except (OSError,ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
                report['purchaseHistoryAudit']={'status':'UNAVAILABLE','errorType':type(error).__name__}
            atomic_json(directory/'sales.json',report)
        cross_imports=[]
        cross_sales={}
        for entry in report.get('purchaseHistoryCrossCardSales',[]):
            cross_sales.setdefault(entry['cardId'],{})[entry['sale']['item_id']]=entry['sale']
        for target_id,sales_by_id in cross_sales.items():
            target=next((c for c in cards if c['card_id']==target_id),None)
            if not target:continue
            evidence_directory=args.out/'cross-card-purchase-evidence'/target_id
            evidence_directory.mkdir(parents=True,exist_ok=True)
            try:
                imported=import_result({'pages':[{'status':'OK'}],'rows':list(sales_by_id.values())},target,evidence_directory)
                cross_imports.append({'cardId':target_id,'status':imported.get('status'),'count':len(sales_by_id)})
            except (OSError,ValueError,subprocess.CalledProcessError):
                cross_imports.append({'cardId':target_id,'status':'CROSS_CARD_IMPORT_REVIEW_REQUIRED','count':len(sales_by_id)})
        outcome=import_result(report,card,directory)|{'fetch_status':fetch,
            'cross_card_imports':cross_imports,
            'purchase_history':report.get('purchaseHistoryAudit',{}),
            'offer_candidates':offer_candidates,
            'image_audit':report.get('imageAudit',{}),
            'scan_mode':'INCREMENTAL' if since else 'FULL',
            'since_date':since,'cursor_source':cursor_source}
        # Cursor advances ONLY when every necessary sold page was checked.
        # Incomplete/captcha/unknown layouts must be retried next time.
        if fetch=='OK' and (not since or report.get('incremental_boundary_reached') is True):
            try:
                timestamp=datetime.fromisoformat(report['collected_at'].replace('Z','+00:00'))
                mark_success(card['card_id'],query,timestamp)
                outcome['scan_checkpoint_updated']=True
            except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
                outcome['scan_checkpoint_updated']=False
                outcome['scan_checkpoint_error']=type(error).__name__
        state['results'].append(outcome);state.update(status='RUNNING',finished=len(state['results']),checked_at=datetime.now(timezone.utc).isoformat())
        state['counts']=dict(collections.Counter(r['status'] for r in state['results']))
        atomic_json(statefile,state)
        (args.out/'review.tsv').write_text('card_id\tname\tstatus\tfetch_status\tnm_candidates\n'+'\n'.join('\t'.join(str(r.get(k,'')) for k in ['card_id','name','status','fetch_status','nm_candidates']) for r in state['results'] if r['status']!='IMPORTED')+'\n')
        print(json.dumps(outcome,ensure_ascii=False),flush=True)
        # A burst of service errors is an upstream failure, not 30d market absence.
        # Pause instead of wasting the entire 123-card job on inaccessible eBay pages.
        if len(state['results']) >= 3 and all(
            r.get('fetch_status') in ('SERVICE_ERROR','ERROR','RUNNER_ERROR')
            for r in state['results'][-3:]
        ):
            state.update(status='STOPPED_SERVICE_ERRORS',next_card=next(
                (c['card_id'] for c in cards if c['card_id'] not in {r['card_id'] for r in state['results']}),None))
            atomic_json(statefile,state)
            print('STOPPED_SERVICE_ERRORS: three consecutive unsuccessful fetches',flush=True)
            return
        # Serial, paced browser requests: reduce idle time modestly, but slow
        # down after upstream errors instead of parallelizing eBay requests.
        time.sleep(30 if fetch!='OK' else 15)
    state.update(status='COMPLETE',checked_at=datetime.now(timezone.utc).isoformat());atomic_json(statefile,state)
if __name__=='__main__':main()
