#!/usr/bin/env python3
import argparse,html,json,math,re,subprocess,time,urllib.parse,urllib.request
from datetime import date

NM_FACTOR=0.92
UA={"User-Agent":"Mozilla/5.0 Cardyssey/0.3","Accept":"text/html,application/xhtml+xml"}
parser=argparse.ArgumentParser()
parser.add_argument("--apply",action="store_true")
args=parser.parse_args()

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True,
    ).stdout.strip()
def q(v):return str(v).replace("'","''")
def clean(v):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",v or ""))).strip()
def get_text(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=20) as r:return r.read().decode("utf-8","ignore")

rate_req=urllib.request.Request(
    "https://api.frankfurter.dev/v2/rate/JPY/EUR",
    headers={"User-Agent":"Cardyssey-cardrush-price"},
)
with urllib.request.urlopen(rate_req,timeout=15) as r:
    rate=float(json.load(r)["rate"])
if not math.isfinite(rate) or rate<=0:raise SystemExit("JPY/EUR unavailable")

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,v.value::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND c.set_id IN ('M-P','SV-P')
  AND v.value->>'id'=p.variant_id
ORDER BY c.set_id,c.local_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t",6)
    if len(z)!=7:continue
    cid,setid,lid,name,vid,legacy,vjson=z
    try:v=json.loads(vjson)
    except Exception:continue
    if v.get("stamps") or v.get("subtype") or v.get("foil"):continue
    if str(v.get("size") or "").lower() not in ("","standard"):continue
    # 30th Celebration starter promos are unreleased until 2026-10-16.
    if date.today()<date(2026,10,16) and setid=="M-P" and str(lid).isdigit() and 101<=int(lid)<=127:continue
    rows.append((cid,setid,lid,name,vid,legacy))

updates=[]
misses=[]
for i,(cid,setid,lid,name,vid,legacy) in enumerate(rows,1):
    code=f"{int(lid):03d}/{setid}" if str(lid).isdigit() else f"{lid}/{setid}"
    url="https://www.cardrush-pokemon.jp/product-list/0/0/normal?"+urllib.parse.urlencode({"keyword":code})
    try:h=get_text(url)
    except Exception as e:
        misses.append((cid,"request",repr(e)));continue
    matches=[]
    for m in re.finditer(r'<div class="item_data clearfix" data-product-id="(\d+)">(.*?)</li>',h,re.S):
        pid=m.group(1);block=m.group(2)
        if code.lower() not in clean(block).lower():continue
        nm=re.search(r'<span class="goods_name">(.*?)</span>',block,re.S)
        title=clean(nm.group(1) if nm else "")
        if name not in title:continue
        if any(x in title for x in ("状態B","状態C","PSA","鑑定済","状態難")):continue
        if 'stock soldout' in block:continue
        pm=re.search(r'<span class="figure">([0-9,]+)円</span>',block)
        if not pm:continue
        yen=int(pm.group(1).replace(",",""))
        if yen<=0:continue
        matches.append((yen,pid,title,url))
    if matches:
        matches.sort()
        yen,pid,title,url=matches[0]
        eur=round((yen*rate)/NM_FACTOR,4)
        updates.append((cid,setid,lid,name,vid,yen,eur,pid,title,url))
        print(f"cardrush_match={cid} code={code} yen={yen} eur={eur:.4f} product={pid} title={title}",flush=True)
    else:
        misses.append((cid,"no_exact_in_stock",""))
    if i%10==0:print(f"cardrush_progress={i}/{len(rows)} matches={len(updates)}",flush=True)
    time.sleep(0.12)

print(f"cardrush_candidates={len(rows)} matches={len(updates)} misses={len(misses)} jpy_eur={rate}",flush=True)
if not args.apply or not updates:raise SystemExit(0)

sql=["BEGIN;"]
for cid,setid,lid,name,vid,yen,eur,pid,title,url in updates:
    detail=f"CardRush JP exact promo {lid}/{setid}; product {pid}; listed JPY {yen}; {url}"
    sql.append(
        f"UPDATE tcg_price_cache SET source='WEB_CARDRUSH_JP',base_eur={eur:.4f},updated_at=NOW(),"
        f"resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' "
        f"WHERE card_id='{q(cid)}' AND language_code='ja' AND variant_id='{q(vid)}' "
        f"AND resolution_status='NO_PRICE';"
    )
    sql.append(
        f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) "
        f"VALUES('{q(cid)}','ja','{q(vid)}','WEB_CARDRUSH_JP',{eur:.4f},NOW());"
    )
sql.append("COMMIT;")
subprocess.run(
    ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
    input="\n".join(sql),text=True,check=True,
)
print(f"cardrush_applied={len(updates)}",flush=True)
