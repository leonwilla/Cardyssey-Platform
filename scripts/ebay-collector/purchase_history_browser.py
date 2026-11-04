#!/usr/bin/env python3
"""Inspect eBay purchase-history tables via existing authorized Selenium session.

Runs inside existing browser container. Emits transaction facts only; neither
buyer names nor cookies nor full page HTML are returned or persisted.
"""
import json,re,sys,time
from cardyssey_ebay_sold import WebDriver

ITEM=re.compile(r'^\d{9,15}$')

def read_one(driver,item):
    url='https://www.ebay.de/bin/purchaseHistory?item='+item
    try:
        driver.call('POST',driver.session+'/url',{'url':url})
        details={}
        for _ in range(10):
            details=driver.script('''return {
                url:location.href, title:document.title,
                headers:[...document.querySelectorAll('table.app-table__table thead th')].map(x=>x.innerText.trim()),
                rows:[...document.querySelectorAll('table.app-table__table tbody tr')].slice(0,150).map(r=>[...r.querySelectorAll('td')].slice(1).map(x=>x.innerText.trim()))
            }''')
            if details.get('headers') or re.search('captcha|signin|login',details.get('url',''),re.I):break
            time.sleep(1)
        page=details.get('url','')
        if not page.startswith('https://www.ebay.de/bin/purchaseHistory?item='+item):
            return dict(itemId=item,status='BLOCKED' if 'captcha' in page else 'LOGIN_REQUIRED' if re.search('signin|login',page,re.I) else 'UNAVAILABLE',rows=[])
        headers=[h.casefold() for h in details.get('headers',[])]
        if len(headers)!=5 or not all(w in ' '.join(headers) for w in ('variante','preis','stückzahl','kaufdatum')):
            return dict(itemId=item,status='UNSAFE_LAYOUT',rows=[])
        entries=[dict(variant=r[0][:250],displayedPrice=r[1][:100],quantity=r[2][:30],purchasedAt=r[3][:100])
                 for r in details.get('rows',[]) if len(r)==4]
        return dict(itemId=item,status='VERIFIED_ROWS' if entries else 'NO_PURCHASE_ROWS',rows=entries)
    except Exception:
        return dict(itemId=item,status='UNAVAILABLE',rows=[])

def main():
    items=sys.argv[1:4]
    if not items or any(not ITEM.fullmatch(item) for item in items):raise SystemExit('INVALID_ITEM_ID')
    browser=WebDriver('http://127.0.0.1:4444')
    data=[]
    for item in items:
        data.append(read_one(browser,item))
        if len(items)>1:time.sleep(3)
    print(json.dumps({'results':data},ensure_ascii=False))

if __name__=='__main__':main()
