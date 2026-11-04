#!/usr/bin/env python3
"""Cardyssey: conservative eBay sold-search collector. Python 3.10+."""
import argparse
import os
import hashlib
import tempfile
import urllib.request
from urllib.error import URLError
from contextlib import contextmanager
import csv
import json
import re
import statistics
import sys
import time
from datetime import datetime, timezone, date
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def text(self):
        if self.cls('clipped') or self.attrs.get('aria-hidden') == 'true': return ''
        return ' '.join(' '.join(c.text() if isinstance(c, Node) else c for c in self.children).split())
    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.walk()
    def cls(self, name):
        return name in self.attrs.get('class', '').split()


class DOM(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs)
        self.stack[-1].children.append(n)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(n)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break
    def handle_data(self, data):
        if self.stack[-1].tag not in {'script', 'style'}:
            self.stack[-1].children.append(data)


def pick(node, *classes):
    return next((n.text() for n in node.walk() if any(n.cls(c) for c in classes)), '')


def money(raw):
    # Only unambiguous EUR prices; reject ranges and foreign currencies.
    if not re.search(r'€|\bEUR\b', raw, re.I) or re.search(r'\b(?:bis|to)\b|\d\s*[-–]\s*\d', raw, re.I):
        return None
    nums = re.findall(r'\d[\d.,\s\u00a0]*', raw)
    if len(nums) != 1:
        return None
    s = re.sub(r'\s', '', nums[0]).strip('.,')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif ',' in s or '.' in s:
        sep = ',' if ',' in s else '.'
        s = s.replace(sep, '.') if len(s.rsplit(sep, 1)[1]) == 2 else s.replace(sep, '')
    try:
        value = Decimal(s)
        return float(value) if value >= 0 else None
    except InvalidOperation:
        return None


def page_state(html, url='', status=200):
    root = DOM(html).root
    txt = root.text().lower()
    title = next((n.text().lower() for n in root.walk() if n.tag == 'title'), '')
    if status in (403, 429) or any(s in title for s in ('pardon our interruption', 'security measure', 'access denied', 'robot check', 'sicherheitsmaßnahme')):
        return 'BLOCKED'
    if '/splashui/captcha' in url or any(n.attrs.get('id') == 'captcha_form' for n in root.walk()):
        return 'BLOCKED'
    if any(s in txt for s in ('verify you are human', 'verify yourself', 'checking your browser', 'bestätigen sie, dass sie ein mensch')):
        return 'BLOCKED'
    if 'signin.ebay.' in url or any(n.tag == 'input' and n.attrs.get('type') == 'password' for n in root.walk()):
        return 'LOGIN_REQUIRED'
    if 'error page' in title or 'something went wrong on our end' in txt or status >= 500:
        return 'SERVICE_ERROR'
    if status >= 400:
        return 'HTTP_ERROR'
    return 'OK'


def listing_thumbnail(card):
    """Return a vetted eBay/CDN thumbnail URL, never arbitrary external URLs."""
    for node in card.walk():
        if node.tag != 'img':
            continue
        for key in ('data-src','data-lazy-src','src'):
            candidate = node.attrs.get(key,'').strip()
            if candidate.startswith('//'):
                candidate = 'https:' + candidate
            parsed = urlsplit(candidate)
            host = (parsed.hostname or '').lower()
            if (parsed.scheme == 'https' and
                (host == 'i.ebayimg.com' or host.endswith('.ebayimg.com')) and
                not parsed.username and not parsed.password and
                len(candidate) < 2048):
                return candidate
    return None


def parse(html, required=(), excluded=()):
    root, rows, seen = DOM(html).root, [], set()
    for card in root.walk():
        if not (card.cls('s-item') or card.cls('s-card')):
            continue
        link = next((n.attrs.get('href','') for n in card.walk() if n.tag == 'a' and re.search(r'/itm/(?:[^/?]+/)?\d{9,15}', n.attrs.get('href',''))), '')
        match = re.search(r'/itm/(?:[^/?]+/)?(\d{9,15})', link)
        if not match or match[1] in seen:
            continue
        host = (urlsplit(link).hostname or '').lower()
        if host not in {'www.ebay.de','www.ebay.com','www.ebay.co.uk','www.ebay.at','www.ebay.ch'}:
            continue
        seen.add(match[1])
        title = re.sub(r'^(?:NEUES ANGEBOT|NEW LISTING)\s*', '', pick(card, 's-item__title', 's-card__title'), flags=re.I)
        txt = card.text()
        raw = pick(card, 's-item__price', 's-card__price')
        price = money(raw)
        sold = re.search(r'\b(?:Verkauft(?:\s+am)?|Sold)\s*:?\s+(\d[^|]*?)(?=EUR|€|\$|$)', txt, re.I)
        # A dated sale marker is required: "Beendet" or "3 verkauft" is insufficient.
        sold_marker = re.search(r'\b(?:Verkauft(?:\s+am)?|Sold)\s*:?\s+(?:\d{1,2}[. /-]|(?:Jan|Feb|Mär|Mar|Apr|Mai|May|Jun|Jul|Aug|Sep|Okt|Oct|Nov|Dez|Dec)[a-zä]*\.?\s+\d{1,2})', txt, re.I)
        reasons = []
        if not sold_marker: reasons.append('NO_DATED_SOLD_MARKER')
        if not title: reasons.append('MISSING_TITLE')
        if price is None or price <= 0: reasons.append('INVALID_OR_NON_EUR_PRICE')
        if re.search(r'preisvorschlag|best offer', txt, re.I) or any(n.tag in {'s','del'} or n.cls('strikethrough') or 'line-through' in n.attrs.get('style','') for n in card.walk()):
            reasons.append('OFFER_OR_STRIKETHROUGH_PRICE')
        if re.search(r'\b(lot|bundle|konvolut|sammlung|proxy|reprint|replica|fake|PSA|BGS|CGC|SGC|AOG|PGS|GSG|AP|graded|bewertet|sealed|versiegelt|OVP)\b|\b\d+\s*[x×]\b', title, re.I):
            reasons.append('BUNDLE_GRADED_OR_REPLICA')
        if any(t.casefold() not in title.casefold() for t in required): reasons.append('REQUIRED_TOKEN_MISSING')
        if any(t.casefold() in title.casefold() for t in excluded): reasons.append('EXCLUDED_TOKEN')
        # Capture only public listing thumbnails. Do not download images or treat
        # image presence as verified card identity.
        image_url = listing_thumbnail(card)
        shipping_raw = pick(card, 's-item__shipping', 's-item__logisticsCost', 's-card__shipping')
        if not shipping_raw:
            shipping_raw = next((n.text() for n in card.walk() if n.cls('s-card__attribute-row') and re.search(r'Lieferung|Versand|shipping|postage', n.text(), re.I)), '')
        shipping = 0.0 if re.search(r'kostenlos|gratis|free shipping|free postage', shipping_raw, re.I) else money(shipping_raw.split('·')[0])
        sale_date, sale_label = sold_date(txt)
        if not sale_date: reasons.append('INVALID_SALE_DATE')
        elif date.fromisoformat(sale_date) > date.today(): reasons.append('FUTURE_SALE_DATE')
        traits = classify(title)

        rows.append(dict(item_id=match[1], title=title, url=f'https://{host}/itm/{match[1]}', price_eur=price,
                         shipping_eur=shipping, price_raw=raw, shipping_raw=shipping_raw,
                         sold_label=sale_label, sold_date=sale_date,
                         image_url=image_url, image_verified=False, **traits,
                         eligible=not reasons, exclusions=';'.join(reasons), evidence=txt))
    return rows


def summary(rows, minimum):
    prices = [r['price_eur'] for r in rows if r['eligible']]
    enough = len(prices) >= minimum
    return dict(status='ESTIMATE_ONLY' if enough else 'INSUFFICIENT_DATA', eligible_count=len(prices),
                sample_median_eur=round(statistics.median(prices), 2) if prices else None,
                estimated_market_value_eur=round(statistics.median(prices), 2) if enough else None,
                min_eur=min(prices) if prices else None, max_eur=max(prices) if prices else None,
                price_basis='displayed_item_price_excluding_shipping',
                warning='Unverified displayed prices; payment, hidden offers, condition and exact print identity are not independently verified.')


MONTHS = {'jan':1,'feb':2,'mär':3,'mar':3,'apr':4,'mai':5,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'okt':10,'oct':10,'nov':11,'dez':12,'dec':12}
def sold_date(text):
    m = re.search(r'\b(?:Verkauft(?:\s+am)?|Sold)\s*:?\s+(\d{1,2})\.?\s+([A-Za-zäÄ]+)\.?\s+(\d{4})\b', text, re.I)
    if m:
        try: return date(int(m[3]), MONTHS[m[2].lower()[:3]], int(m[1])).isoformat(), m[0]
        except (ValueError, KeyError): return None, m[0]
    m = re.search(r'\bSold\s+([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\b', text, re.I)
    if m:
        try: return date(int(m[3]), MONTHS[m[1].lower()[:3]], int(m[2])).isoformat(), m[0]
        except (ValueError, KeyError): return None, m[0]
    return None, ''


def classify(title):
    def matches(pattern): return bool(re.search(pattern, title, re.I))
    langs = [lang for lang, pat in {
        'de':r'\b(deutsch|german|de)\b', 'en':r'\b(englisch|english|en)\b',
        'ja':r'\b(japanisch|japanese|japan|jpn|jp|ja)\b', 'ko':r'\b(koreanisch|korean|ko)\b',
        'zh-cn':r'\b(simplified chinese|vereinfachtes chinesisch|zh-cn)\b',
        'zh-tw':r'\b(traditional chinese|traditionelles chinesisch|zh-tw)\b'}.items() if matches(pat)]
    first = matches(r'\b(?:1\.?\s*(?:st\s*)?(?:edition|auflage)|first edition|1st ed)\b')
    unlimited = matches(r'\b(unlimited|unlimitiert|unl)\b')
    edition = 'conflict' if first and unlimited else 'first' if first else 'unlimited' if unlimited else 'unknown'
    nonholo = matches(r'\b(non[- ]?holo|nicht[- ]?holo)\b')
    reverse = matches(r'\breverse\b')
    holo = matches(r'\bholo(?:graphic)?\b')
    variant = 'conflict' if nonholo and reverse else 'nonholo' if nonholo else 'reverse' if reverse else 'holo' if holo else 'unknown'
    conditions = [name for name, pat in {
        'mint':r'\b(mint|mt)\b', 'nm':r'\b(nm|near mint|nearmint)\b',
        'ex':r'\b(excellent|exc)\b', 'lp':r'\b(lp|light(?:ly)? played)\b',
        'gd':r'\b(good|gd)\b', 'vg':r'\b(very good|vg)\b',
        'mp':r'\b(mp|moderately played)\b', 'hp':r'\b(hp|heavily played|stark bespielt)\b',
        'played':r'\b(played|bespielt)\b', 'damaged':r'\b(damaged|dmg|beschädigt)\b'
    }.items() if matches(pat)]
    if 'nm' in conditions and 'mint' in conditions: conditions.remove('mint')
    if 'vg' in conditions and 'gd' in conditions: conditions.remove('gd')
    if any(c in conditions for c in ['lp','mp','hp','gd']) and 'played' in conditions: conditions.remove('played')
    # EX is also a Pokémon card mechanic. Never derive condition from bare EX.
    if conditions == ['ex'] and not matches(r'\b(excellent|exc)\b'): conditions = []
    number = re.search(r'(?<!\w)([A-Za-z]*\d+)\s*/\s*([A-Za-z]*\d+)(?!\w)', title)
    def normalize(n):
        m = re.fullmatch(r'([A-Za-z]*)(\d+)', n)
        return m[1].upper()+str(int(m[2])) if m else n.upper()
    return dict(language=langs[0] if len(langs)==1 else 'conflict' if langs else 'unknown',
                edition=edition, variant=variant,
                condition=conditions[0] if len(conditions)==1 else 'conflict' if conditions else 'unknown',
                card_number='/'.join(normalize(n) for n in number.groups()) if number else 'unknown')


def apply_policy(rows, args):
    for row in rows:
        reasons = list(filter(None, row['exclusions'].split(';')))
        for field in ('language','edition','variant','condition','card_number'):
            expected = getattr(args, field)
            if expected and row[field] != expected: reasons.append(field.upper()+'_MISMATCH_OR_UNKNOWN')
        if row['sold_date'] and (date.today()-date.fromisoformat(row['sold_date'])).days > args.max_age_days:
            reasons.append('SALE_TOO_OLD')
        row['exclusions'] = ';'.join(dict.fromkeys(reasons))
        row['eligible'] = not reasons


def atomic_json(path, value):
    temp = path.with_suffix(path.suffix+'.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


class ProfileMismatch(RuntimeError):
    pass


class WebDriver:
    """Attach to existing local Selenium session; never quit/delete that session."""
    def __init__(self, endpoint, session_id=None, profile='/home/seluser/.config/chromium', headless=False):
        u = urlsplit(endpoint)
        if u.scheme != 'http' or u.hostname not in {'localhost','127.0.0.1','::1'} or u.username or u.password or u.query or u.fragment:
            raise ValueError('Selenium endpoint must be local HTTP; use an SSH tunnel for remote hosts')
        if not profile.startswith('/') or '\x00' in profile:
            raise ValueError('Absolute persistent browser profile required')
        self.base = endpoint.rstrip('/')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        status = self.call('GET','/status')
        sessions = [s['session'] for n in status.get('nodes',[]) for s in n.get('slots',[]) if s.get('session')]
        if session_id:
            selected = next((s for s in sessions if s['sessionId']==session_id),None)
            if selected is None: raise RuntimeError('SESSION_NOT_FOUND')
        elif not sessions:
            selected = self.call('POST','/session',{'capabilities':{'alwaysMatch':{
                'browserName':'chrome','pageLoadStrategy':'eager',
                'goog:chromeOptions':{'args':['--user-data-dir='+profile,'--profile-directory=Default','--window-size=1440,1000']+(['--headless=new'] if headless else [])},
                'timeouts':{'pageLoad':45000,'script':15000,'implicit':0}}}})
            print('SESSION_CREATED_WITH_PERSISTENT_PROFILE',file=sys.stderr)
        elif len(sessions)==1:
            selected=sessions[0]
        else: raise RuntimeError('MULTIPLE_SESSIONS_REQUIRE_EXPLICIT_ID')
        actual=selected.get('capabilities',{}).get('chrome',{}).get('userDataDir')
        if actual != profile: raise ProfileMismatch('WRONG_BROWSER_PROFILE')
        session_id=selected['sessionId']
        if not re.fullmatch(r'[a-zA-Z0-9-]+',session_id): raise ValueError('Invalid session ID')
        self.session='/session/'+session_id
    def call(self, method, path, payload=None):
        req=urllib.request.Request(self.base+path, data=json.dumps(payload).encode() if payload is not None else None,
                                   headers={'Content-Type':'application/json'},method=method)
        with self.opener.open(req, timeout=70) as response: value=json.load(response)['value']
        if isinstance(value,dict) and value.get('error'): raise RuntimeError('WebDriver '+value['error'])
        return value
    def script(self, script): return self.call('POST',self.session+'/execute/sync',{'script':script,'args':[]})
    def load(self,url):
        self.call('POST',self.session+'/url',{'url':url})
        # Wait for real cards, an explicit empty result, or a challenge/login.
        for _ in range(15):
            if self.script('return !!document.querySelector(".s-card,.s-item,input[type=password],#captcha_form,.srp-save-null-search") || /captcha|signin/.test(location.href)'): break
            time.sleep(1)
        data=self.script('return {html:document.documentElement.outerHTML,url:location.href}')
        return data['html'], data['url'], 200


@contextmanager
def browser(args):
    if args.webdriver:
        driver=WebDriver(args.webdriver,args.session_id,args.webdriver_profile,args.webdriver_headless)
        previous=driver.call('GET',driver.session+'/timeouts')
        driver.call('POST',driver.session+'/timeouts',{'pageLoad':45000,'script':15000})
        try: yield driver
        finally:
            try: driver.call('POST',driver.session+'/timeouts',previous)
            except Exception: pass
        return
    from playwright.sync_api import sync_playwright
    args.profile.mkdir(mode=0o700, parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx=pw.chromium.launch_persistent_context(str(args.profile.resolve()),headless=not(args.headed or args.login),locale='de-DE')
        try:
            page=ctx.new_page()
            if args.login:
                page.goto('https://www.ebay.de/',wait_until='domcontentloaded')
                input('Bei eBay selbst anmelden, dann Enter. ')
            class Adapter:
                def load(self,url):
                    response=page.goto(url,wait_until='domcontentloaded',timeout=60000)
                    try: page.wait_for_selector('.s-card,.s-item,input[type=password],#captcha_form',timeout=15000)
                    except Exception: pass
                    return page.content(),page.url,response.status if response else 0
            yield Adapter()
        finally: ctx.close()


def main():
    os.umask(0o077)
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--query',required=True)
    ap.add_argument('--require',action='append',default=[])
    ap.add_argument('--exclude',action='append',default=[])
    ap.add_argument('--language',choices=['de','en','ja','ko','zh-cn','zh-tw'])
    ap.add_argument('--edition',choices=['first','unlimited'])
    ap.add_argument('--variant',choices=['holo','reverse','nonholo'])
    ap.add_argument('--condition',choices=['mint','nm','ex','lp','gd','vg','mp','hp','played','damaged'])
    ap.add_argument('--card-number')
    ap.add_argument('--max-age-days',type=int,default=30)
    ap.add_argument('--sold-since',help='ISO sale date lower bound for incremental sold-search pages')
    ap.add_argument('--pages',type=int,default=3)
    ap.add_argument('--delay',type=float,default=8)
    ap.add_argument('--min-sales',type=int,default=1)
    ap.add_argument('--out',type=Path,default=Path('results'))
    ap.add_argument('--html',type=Path,nargs='+')
    ap.add_argument('--headed',action='store_true')
    ap.add_argument('--login',action='store_true')
    ap.add_argument('--profile',type=Path,default=Path('.ebay-profile'))
    ap.add_argument('--webdriver',help='Local Selenium endpoint, e.g. http://127.0.0.1:4444')
    ap.add_argument('--webdriver-headless',action='store_true',help='Create new Selenium sessions without browser UI')
    ap.add_argument('--webdriver-profile',default='/home/seluser/.config/chromium',help='Persistent profile inside Selenium host/container')
    ap.add_argument('--session-id',help='Optional existing session ID; otherwise discover sole active session')
    ap.add_argument('--resume',action='store_true')
    a=ap.parse_args()
    if not 1<=a.pages<=100 or not 3<=a.delay<=300 or a.min_sales<1 or a.max_age_days<1: ap.error('pages 1..100, delay 3..300, min-sales >=1, max-age-days >=1')
    if a.sold_since:
        try:
            since=date.fromisoformat(a.sold_since)
            if since>date.today():ap.error('--sold-since cannot be in the future')
        except ValueError:ap.error('--sold-since requires YYYY-MM-DD')
    if a.login and (a.webdriver or a.html): ap.error('--login is for a local Playwright profile only')
    if a.card_number:
        a.card_number=classify(a.card_number)['card_number']
        if a.card_number=='unknown': ap.error('--card-number requires numerator/denominator')
    a.out.mkdir(parents=True,exist_ok=True,mode=0o700)
    # OS lock is automatically released on crash. One collector per profile/session.
    import fcntl
    lock_path=(a.profile.resolve()/'.ebay-collector.lock') if not a.webdriver else Path(tempfile.gettempdir())/('cardyssey-ebay-'+str(os.getuid())+'.lock')
    lock_path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=lock_path.open('a')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: print('Another collector is active',file=sys.stderr); return 2
    config={k:getattr(a,k) for k in ['query','require','exclude','language','edition','variant','condition','card_number','max_age_days','min_sales','sold_since']}
    signature=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    checkpoint=a.out/'checkpoint.json'
    rows,states,next_page=[],[],1
    if a.resume and checkpoint.exists():
        old=json.loads(checkpoint.read_text())
        if old['signature']!=signature: ap.error('Checkpoint filters differ; use a different output directory')
        rows,states,next_page=old['rows'],old['pages'],old['next_page']
    seen={r['item_id'] for r in rows}
    incremental_boundary=False
    def consume(html,url,status,num):
        nonlocal incremental_boundary
        nonlocal next_page
        state=page_state(html,url,status)
        found=parse(html,a.require,a.exclude) if state=='OK' else []
        if state=='OK' and not found: state='EMPTY_OR_LAYOUT_CHANGED'
        apply_policy(found,a)
        if a.sold_since and state=='OK':
            cutoff=date.fromisoformat(a.sold_since)
            dated=[date.fromisoformat(r['sold_date']) for r in found if r.get('sold_date')]
            # Only trust a sorted, dated page. An out-of-order or partially
            # undated result page cannot prove the end of the new-sale window.
            ordered=bool(dated) and len(dated)==len(found) and all(
                dated[i]>=dated[i+1] for i in range(len(dated)-1))
            incremental_boundary=incremental_boundary or (ordered and dated[-1]<cutoff)
            found=[r for r in found if r.get('sold_date') and date.fromisoformat(r['sold_date'])>=cutoff]
        new=[r for r in found if r['item_id'] not in seen]
        if state=='OK' and not new and not (a.sold_since and incremental_boundary): state='REPEATED_PAGE'
        if state=='OK':
            rows.extend(new); seen.update(r['item_id'] for r in new); next_page=num+1
        states.append({'page':num,'status':state,'parsed_count':len(found),'new_count':len(new)})
        atomic_json(checkpoint,dict(signature=signature,rows=rows,pages=states,next_page=next_page))
        print(f'page {num}: {state}, {len(new)} new',file=sys.stderr)
        return state
    try:
        if a.html:
            for num,path in enumerate(a.html,1):
                if num<next_page: continue
                if consume(path.read_text(encoding='utf-8'),'',200,num)!='OK': break
                if a.sold_since and incremental_boundary:break
        else:
            with browser(a) as b:
                if a.login: return 0
                for num in range(next_page,a.pages+1):
                    url='https://www.ebay.de/sch/i.html?'+urlencode(dict(_nkw=a.query,LH_Sold=1,LH_Complete=1,**({'_sop':13} if a.sold_since else {}),**({'_pgn':num} if num>1 else {})))
                    html,final_url,status=b.load(url)
                    if page_state(html,final_url,status)=='SERVICE_ERROR':
                        time.sleep(max(a.delay,15))
                        html,final_url,status=b.load(url)
                    if consume(html,final_url,status,num)!='OK': break
                    if a.sold_since and incremental_boundary:break
            if num<a.pages: time.sleep(a.delay)
    except ProfileMismatch: states.append({'status':'WRONG_BROWSER_PROFILE'})
    except KeyboardInterrupt: states.append({'status':'INTERRUPTED'})
    except Exception as exc:
        # Never log exception strings: browser libraries may include sensitive URLs.
        states.append({'status':'ERROR','error_type':type(exc).__name__})
    complete=bool(states) and states[-1]['status']=='OK' and (
        not a.sold_since or incremental_boundary)
    if a.sold_since and states and states[-1]['status']=='OK' and not incremental_boundary:
        states.append({'status':'INCREMENTAL_BOUNDARY_NOT_REACHED',
                       'reason':'Page limit reached without safely finding older sold dates'})
    apply_policy(rows,a)
    result=summary(rows,a.min_sales)
    result['collection_incomplete']=not complete
    identity_complete=all(getattr(a,k) for k in ['language','edition','variant','condition','card_number']) and bool(a.require)
    if not identity_complete or not complete:
        result['estimated_market_value_eur']=None
        result['status']='COLLECTION_INCOMPLETE' if not complete else 'IDENTITY_FILTERS_REQUIRED'
    prices=[r['price_eur'] for r in rows if r['eligible']]
    result['median_absolute_deviation_eur']=round(statistics.median(abs(p-statistics.median(prices)) for p in prices),2) if prices else None
    groups={}
    for row in rows:
        if row['eligible']:
            key='|'.join(row[k] for k in ['language','card_number','edition','variant','condition'])
            groups.setdefault(key,[]).append(row)
    report=dict(schema_version=2,config=config,collected_at=datetime.now(timezone.utc).isoformat(),incremental_boundary_reached=incremental_boundary,pages=states,summary=result,
                groups={k:summary(v,a.min_sales) | {'estimated_market_value_eur':None,'status':'GROUP_SAMPLE_ONLY'} for k,v in groups.items()},rows=rows)
    atomic_json(a.out/'sales.json',report)
    atomic_json(checkpoint,dict(signature=signature,rows=rows,pages=states,next_page=next_page))
    fields=list(rows[0]) if rows else ['item_id','title','url','price_eur','eligible','exclusions']
    temp=a.out/'sales.csv.tmp'
    with temp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=';'); w.writeheader()
        for row in rows:
            w.writerow({k:"'"+v if isinstance(v,str) and (v.lstrip().startswith(('=','+','-','@')) or v.startswith(('\t','\r','\n'))) else v for k,v in row.items()})
    temp.replace(a.out/'sales.csv')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if complete else 2

if __name__=='__main__': raise SystemExit(main())
