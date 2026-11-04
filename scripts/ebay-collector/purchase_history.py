"""Audit real eBay multi-choice purchase-history rows, with strict print/price proof.

Never treats the listing-level sold counter or asking price as a card sale.
Buyer usernames are intentionally never scraped or stored.
"""
import hashlib,json,re,subprocess
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from ebay_sold import money,classify
from offer_references import MULTI
from price_history import db,sql

MONTH={'jan':1,'feb':2,'mär':3,'mar':3,'apr':4,'mai':5,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'sept':9,'okt':10,'oct':10,'nov':11,'dez':12,'dec':12}

def purchase_date(value):
    m=re.fullmatch(r'\s*(\d{1,2})\.?\s+([A-Za-zäÄ]+)\s+(\d{4}),?\s+(\d{1,2}):(\d{2}):(\d{2})(?:\s+(?:MESZ|MEZ|CEST|CET))?\s*',value)
    if not m:return None
    try:
        return datetime(int(m[3]),MONTH[m[2].casefold()[:3]],int(m[1]),int(m[4]),int(m[5]),int(m[6]),tzinfo=timezone.utc)
    except (KeyError,ValueError):return None

def verified_transaction(row,item_id,card,parent_title):
    """Return one importer-compatible sold observation only if row proves sale price.

    Date+unit price+exact selected print+language+single-card identity are mandatory.
    The listing's price itself is never a substitute for the purchase-row price.
    """
    variant=str(row.get('variant',''))
    if not re.fullmatch(r'\d{9,15}',str(item_id)):return None,'INVALID_ITEM'
    if not str(card.get('local_id','')).isdigit() or not re.search(r'\b'+re.escape(card['name'])+r'\b',variant,re.I):return None,'OTHER_CARD'
    num=int(card['local_id']);den=int(card.get('denominator',128))
    number=re.search(r'(?<![\w/])0*(\d{1,3})\s*/\s*0*(\d{2,3})(?!\w)',variant)
    if not number or int(number[1])!=num or int(number[2])!=den:return None,'OTHER_CARD'
    dt=purchase_date(str(row.get('purchasedAt','')))
    if not dt or dt.date()>date.today():return None,'INVALID_SALE_DATE'
    quantity=str(row.get('quantity','')).strip()
    if not quantity.isdigit() or not 1<=int(quantity)<=20:return None,'INVALID_QUANTITY'
    raw_price=str(row.get('displayedPrice','')).strip()
    if not re.fullmatch(r'(?:EUR\s*)?\d{1,6}(?:[.,]\d{2})?\s*(?:€|EUR)?',raw_price,re.I) or not ('EUR' in raw_price.upper() or '€' in raw_price):
        return None,'NO_PAID_PRICE'
    amount=money(raw_price)
    if amount is None or not 0<amount<100000:return None,'INVALID_PRICE'
    parent=parent_title.casefold()
    if not re.search(r'\b(?:deutsch|german|\bde\b)\b',parent,re.I):return None,'LANGUAGE_UNCLEAR'
    if not re.search(r'karmesin|purpur|paldea|sv01|sv02|svi|30 jahre|30th',parent,re.I):return None,'SET_UNCLEAR'
    set_id=card.get('set_id')
    if set_id=='sv01' and not re.search(r'karmesin\s*(?:&|und)\s*purpur|\bsv0?1\b|\bsvi\b',parent,re.I):return None,'SET_UNCLEAR'
    if set_id=='sv02' and not re.search(r'entwicklungen\s+in\s+paldea|\bsv0?2\b|\bpal\b',parent,re.I):return None,'SET_UNCLEAR'
    if set_id in ('30th','30th-c') and not re.search(r'30\s*jahre|30th',parent,re.I):return None,'SET_UNCLEAR'
    condition=classify(parent_title+' '+variant)['condition']
    if condition not in ('unknown','nm','mint'):return None,'CONDITION_NOT_NM'
    explicit_reverse=re.search(r'\breverse\b',variant,re.I)
    explicit_normal=re.search(r'\b(?:non[- ]?holo|nicht[- ]?holo|normal)\b',variant,re.I)
    if explicit_reverse and explicit_normal:return None,'VARIANT_CONFLICT'
    if explicit_normal and re.search(r'\breverse\b',parent_title,re.I) and not re.search(r'\breverse\s*(?:\+|/|und|&|oder)\s*holo\b',parent_title,re.I):return None,'VARIANT_CONFLICT'
    if not explicit_reverse and not explicit_normal and re.search(r'\breverse\s*(?:\+|/|und|&|oder)\s*holo\b',parent_title,re.I):
        return None,'VARIANT_UNCLEAR_MIXED_LISTING'
    # If no variant-specific wording, listing-wide reverse/non-holo is reliable only
    # when the listing itself offers that one print type for all choices.
    print_hint='REVERSE' if explicit_reverse or (not explicit_normal and re.search(r'\breverse\b',parent_title,re.I)) else 'NORMAL'
    raw_identity=f'{item_id}|{variant.casefold()}|{row["purchasedAt"]}|{amount:.4f}|{quantity}'
    sale_id='ph-'+hashlib.sha256(raw_identity.encode()).hexdigest()[:26]
    title=f'{card["name"]} {num:03d}/{den} {card.get("set_name","")} Deutsch '+('Reverse Holo' if print_hint=='REVERSE' else 'Normal')
    observation={'item_id':sale_id,'title':title,'url':f'https://www.ebay.de/bin/purchaseHistory?item={item_id}',
       'price_eur':amount,'sold_date':dt.date().isoformat(),'language':'de','condition':condition,
       'eligible':True,'exclusions':'','image_identity_verified':False,'image_url':None,
       'source':'EBAY_PURCHASE_HISTORY','quantity':int(quantity),'purchaseHistoryItemId':item_id,
       'originalVariantText':variant[:150], 'variant_assumed':not bool(explicit_reverse or explicit_normal)}
    return observation,'CONFIRMED'

def existing(item_id):
    raw=db('SELECT COALESCE(row_to_json(c)::text,\'null\') FROM (SELECT status,transactions,checked_at FROM ebay_purchase_history_check WHERE ebay_item_id='+sql(item_id)+') c;')
    return json.loads(raw or 'null')

def persist_check(obj):
    item=obj['itemId']
    status=obj['status'];rows=obj.get('rows',[])
    # Strip every property except selected print, price, date and quantity.
    rows=[{k:str(r.get(k,''))[:250] for k in ('variant','displayedPrice','quantity','purchasedAt')} for r in rows[:150]]
    if status=='VERIFIED_ROWS' and rows and all('EUR' not in x.get('displayedPrice','').upper() and '€' not in x.get('displayedPrice','') for x in rows):status='NO_VISIBLE_PRICE'
    raw=json.dumps(rows,ensure_ascii=False)
    db('INSERT INTO ebay_purchase_history_check(ebay_item_id,status,transactions,reason) VALUES ('+sql(item)+','+sql(status)+','+sql(raw)+"::jsonb,'') ON CONFLICT(ebay_item_id) DO UPDATE SET status=EXCLUDED.status,transactions=EXCLUDED.transactions,reason=EXCLUDED.reason,checked_at=now();")
    return {'status':status,'transactions':rows}

def cached_or_fetch(item_ids,max_new=4):
    """Batch shared eBay-item checks; recent checks are never repeated per card."""
    data={};missing=[]
    for item in list(dict.fromkeys(item_ids))[:8]:
        record=existing(item)
        if record:
            checked=datetime.fromisoformat(record['checked_at'].replace('Z','+00:00'))
            ttl=timedelta(days=7) if record['status'] in ('VERIFIED_ROWS','NO_PURCHASE_ROWS','NO_VISIBLE_PRICE','UNSAFE_LAYOUT') else timedelta(days=1)
            if datetime.now(timezone.utc)-checked<ttl:
                data[item]=record;continue
        missing.append(item)
    if not missing:return data
    script=Path('/home/tv/cardshop/scripts/ebay-collector/purchase_history_browser.py')
    container='cardyssey-ebay-collector-browser'
    subprocess.run(['docker','cp',str(script),container+':/tmp/cardyssey_purchase_history_browser.py'],capture_output=True,check=True,timeout=15)
    for item in missing[:max_new]:
        try:
            result=subprocess.run(['docker','exec',container,'python3','/tmp/cardyssey_purchase_history_browser.py',item],capture_output=True,text=True,timeout=80)
            if result.returncode!=0:raise ValueError('BROWSER_UNAVAILABLE')
            obj=json.loads(result.stdout)['results'][0]
            data[item]=persist_check(obj)
        except (OSError,subprocess.TimeoutExpired,subprocess.CalledProcessError,ValueError,KeyError):
            data[item]=persist_check({'itemId':item,'status':'UNAVAILABLE','rows':[]})
    return data

def audit_purchase_history(report,card,all_cards=None):
    """Append only independently proven sold-choice transactions to this card's audit."""
    candidates={}
    for r in report.get('rows',[]):
        if MULTI.search(r.get('title','')) and str(r.get('item_id','')).isdigit():
            candidates[r['item_id']]=r['title']
    # Do not spend extra browser requests on unrelated options; only report
    # entries explicitly recorded for the card being scanned.
    audit={'checked':0,'confirmed':0,'cross_card_confirmed':0,'unpriced':0,'unpriced_other_card':0,'not_this_card':0,'unavailable':0,'sources':[]}
    if not candidates:
        report['purchaseHistoryAudit']=audit
        return report
    fetched=cached_or_fetch(list(candidates)[:8])
    cross_card=[]
    by_number={}
    for candidate in all_cards or []:
        if candidate.get('set_id')!=card.get('set_id'):continue
        if str(candidate.get('local_id','')).isdigit():
            by_number[int(candidate['local_id'])]=candidate

    for item,title in candidates.items():
        result=fetched.get(item)
        if not result:continue
        audit['checked']+=1
        source={'itemId':item,'url':'https://www.ebay.de/bin/purchaseHistory?item='+item,
                'status':result['status'],'rows':len(result.get('transactions',[])),'confirmed':0,
                'reason':'READABLE'}
        if result['status'] not in ('VERIFIED_ROWS','NO_VISIBLE_PRICE'):
            audit['unavailable']+=1
            source['reason']=result['status']
        for row in result.get('transactions',[]):
            observed,reason=verified_transaction(row,item,card,title)
            if observed:
                report.setdefault('rows',[]).append(observed)
                audit['confirmed']+=1;source['confirmed']+=1
            elif reason=='NO_PAID_PRICE':audit['unpriced']+=1;source['reason']='NO_PAID_PRICE'
            elif reason=='OTHER_CARD':
                audit['not_this_card']+=1
                match=re.search(r'(?<![\w/])0*(\d{1,3})\s*/\s*0*(\d{2,3})(?!\w)',row.get('variant',''))
                target=by_number.get(int(match[1])) if match else None
                if target and target['card_id']!=card['card_id']:
                    target_sale,target_reason=verified_transaction(row,item,target,title)
                    if target_sale:
                        cross_card.append({'cardId':target['card_id'],'sale':target_sale})
                        audit['cross_card_confirmed']+=1
                    elif target_reason=='NO_PAID_PRICE':
                        audit['unpriced_other_card']+=1
                        source['reason']='OTHER_CARD_NO_PAID_PRICE'
            else:source['reason']=reason
        audit['sources'].append(source)
    report['purchaseHistoryAudit']=audit
    report['purchaseHistoryCrossCardSales']=cross_card
    return report
