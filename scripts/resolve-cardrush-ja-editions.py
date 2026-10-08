#!/usr/bin/env python3
import argparse,concurrent.futures,html,json,math,re,subprocess,urllib.parse,urllib.request,time
from collections import defaultdict

NM_FACTOR=0.92
SAFE_SETS={"PCG2","PCG5","PCG7","web1","VS1"}
UA={"User-Agent":"Mozilla/5.0 Cardyssey/0.3","Accept":"text/html,application/xhtml+xml"}
parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");args=parser.parse_args()

def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v):return str(v).replace("'","''")
def clean(v):return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",v or ""))).strip()
def fetch(code):
    url="https://www.cardrush-pokemon.jp/product-list/0/0/normal?"+urllib.parse.urlencode({"keyword":code})
    last=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=20) as r:
                return code,url,r.read().decode("utf-8","ignore"),None
        except Exception as e:
            last=e;time.sleep(.4*(attempt+1))
    return code,url,"",repr(last)

with urllib.request.urlopen(urllib.request.Request("https://api.frankfurter.dev/v2/rate/JPY/EUR",headers={"User-Agent":"Cardyssey-cardrush-editions"}),timeout=15) as r:
    jpy_eur=float(json.load(r)["rate"])
if not math.isfinite(jpy_eur) or jpy_eur<=0:raise SystemExit("JPY/EUR unavailable")

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,s.official_count,v.value::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND c.set_id IN ('PCG2','PCG5','PCG7','web1','VS1')
  AND v.value->>'id'=p.variant_id
ORDER BY c.set_id,c.local_id,p.variant_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t",7)
    if len(z)!=8:continue
    cid,setid,lid,name,vid,legacy,total,vjson=z
    try:v=json.loads(vjson)
    except:continue
    stamps=[str(x).lower() for x in (v.get("stamps") or [])]
    subtype=str(v.get("subtype") or "").lower()
    expected=None
    if any("1st" in x or "first" in x for x in stamps): expected="first"
    elif subtype=="unlimited": expected="unlimited"
    elif any("1st-edition" in x for x in stamps): expected="first"
    if expected is None:continue
    if v.get("foil"):continue
    if not lid.isdigit() or int(total)<=0:continue
    code=f"{int(lid):03d}/{int(total):03d}"
    rows.append({"card_id":cid,"set_id":setid,"lid":int(lid),"name":name,"vid":vid,"legacy":legacy,"total":int(total),"expected":expected,"code":code})

codes=sorted({r["code"] for r in rows})
pages={}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for idx,(code,url,h,err) in enumerate(pool.map(fetch,codes),1):
        pages[code]=(url,h,err)
        if idx%25==0 or idx==len(codes):print(f"cardrush_edition_fetch={idx}/{len(codes)}",flush=True)

updates=[];misses=0
for r in rows:
    url,h,err=pages.get(r["code"],("", "", "missing"))
    if not h:
        misses+=1;continue
    cand=[]
    for m in re.finditer(r'<div class="item_data clearfix" data-product-id="(\d+)">(.*?)</li>',h,re.S):
        pid=m.group(1);block=m.group(2)
        nm=re.search(r'<span class="goods_name">(.*?)</span>',block,re.S)
        title=clean(nm.group(1) if nm else "")
        if r["code"] not in title:continue
        if r["name"] not in title:continue
        lower=title.lower()
        is_first=("1ed" in lower or "1st" in lower or "初版" in title)
        is_unlimited=("アンリミ" in title or "unlimited" in lower)
        if r["expected"]=="first" and not is_first:continue
        if r["expected"]=="unlimited" and not is_unlimited:continue
        if r["expected"]=="first" and is_unlimited:continue
        if r["expected"]=="unlimited" and is_first:continue
        if any(x in title for x in ("PSA","鑑定済","状態B","状態C","状態D","状態難")):continue
        if "状態" in title and "状態A-" not in title:continue
        # Reject mirror/reverse/special foil labels unless the catalog variant
        # explicitly represents such a printing.
        if any(x in title for x in ("ミラー","リバース","マスターボール","モンスターボール")):continue
        pm=re.search(r'<span class="figure">([0-9,]+)円</span>',block)
        if not pm:continue
        yen=int(pm.group(1).replace(",",""))
        if yen<=0:continue
        sold=('stock soldout' in block)
        cand.append((sold,yen,pid,title,url))
    if not cand:
        misses+=1;continue
    cand.sort(key=lambda x:(x[0],x[1]))
    sold,yen,pid,title,url=cand[0]
    eur=round((yen*jpy_eur)/NM_FACTOR,4)
    source="WEB_CARDRUSH_JP_EDITION" if not sold else "WEB_CARDRUSH_JP_EDITION_REFERENCE"
    updates.append((r,source,yen,eur,pid,title,url,sold))
    print(f"cardrush_edition={r['card_id']}:{r['vid']} {r['expected']} {source} JPY={yen} EUR={eur:.4f} {title}",flush=True)

print(f"cardrush_edition_candidates={len(rows)} unique_searches={len(codes)} updates={len(updates)} misses={misses}",flush=True)
if args.apply and updates:
    sql=["BEGIN;"]
    for r,source,yen,eur,pid,title,url,sold in updates:
        detail=f"CardRush JP exact edition {r['expected']} {r['code']}; product {pid}; listed JPY {yen}; sold_out_reference={'true' if sold else 'false'}; {url}"
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={eur:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['vid'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','ja','{q(r['vid'])}','{source}',{eur:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"cardrush_edition_applied={len(updates)}",flush=True)
