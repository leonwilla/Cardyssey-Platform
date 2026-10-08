#!/usr/bin/env python3
import argparse,html,json,math,re,subprocess,time,urllib.parse,urllib.request

NM_FACTOR=0.92
SAFE_SETS={"E2","E3","SM4S","SV8a"}
UA={"User-Agent":"Mozilla/5.0 Cardyssey/0.3","Accept":"text/html,application/xhtml+xml"}
parser=argparse.ArgumentParser(); parser.add_argument("--apply",action="store_true"); args=parser.parse_args()

def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],check=True,capture_output=True,text=True).stdout.strip()
def q(v): return str(v).replace("'","''")
def clean(v): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",v or ""))).strip()
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=20) as r:return r.read().decode("utf-8","ignore")

with urllib.request.urlopen(urllib.request.Request("https://api.frankfurter.dev/v2/rate/JPY/EUR",headers={"User-Agent":"Cardyssey-cardrush-numbered"}),timeout=15) as r:
    jpy_eur=float(json.load(r)["rate"])
if not math.isfinite(jpy_eur) or jpy_eur<=0: raise SystemExit("JPY/EUR unavailable")

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,s.official_count,v.value::text
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='ja' AND p.resolution_status='NO_PRICE'
  AND c.set_id IN ('E2','E3','SM4S','SV8a')
  AND v.value->>'id'=p.variant_id
ORDER BY c.set_id,c.local_id,p.variant_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t",7)
    if len(z)!=8:continue
    cid,setid,lid,name,vid,legacy,total,vjson=z
    try:v=json.loads(vjson)
    except:continue
    if v.get("stamps") or v.get("subtype"):continue
    foil=str(v.get("foil") or "").lower()
    if foil not in ("","masterball"):continue
    if not lid.isdigit() or int(total)<=0:continue
    rows.append({"card_id":cid,"set_id":setid,"lid":int(lid),"name":name,"vid":vid,"legacy":legacy,"total":int(total),"foil":foil})

updates=[];misses=[]
for i,r in enumerate(rows,1):
    code=f"{r['lid']:03d}/{r['total']:03d}"
    url="https://www.cardrush-pokemon.jp/product-list/0/0/normal?"+urllib.parse.urlencode({"keyword":code})
    try:h=fetch(url)
    except Exception as e: misses.append((r["card_id"],"request"));continue
    exact=[]
    for m in re.finditer(r'<div class="item_data clearfix" data-product-id="(\d+)">(.*?)</li>',h,re.S):
        pid=m.group(1);block=m.group(2)
        nm=re.search(r'<span class="goods_name">(.*?)</span>',block,re.S)
        title=clean(nm.group(1) if nm else "")
        if code not in title:continue
        # Japanese catalog names are authoritative for these sets; requiring the
        # exact name prevents same-number collisions across unrelated sets.
        if r["name"] not in title:continue
        is_mb=("マスターボール" in title or "masterball" in title.lower() or "master ball" in title.lower())
        if r["foil"]=="masterball" and not is_mb:continue
        if r["foil"]!="masterball" and is_mb:continue
        # Avoid graded/heavily played stock and edition-labelled products.
        # This resolver only handles variants without an explicit edition.
        if any(x in title for x in ("PSA","鑑定済","状態B","状態C","状態D","状態難","アンリミ","1ED","1st")):continue
        if "状態" in title and "状態A-" not in title:continue
        pm=re.search(r'<span class="figure">([0-9,]+)円</span>',block)
        if not pm:continue
        yen=int(pm.group(1).replace(",",""))
        if yen<=0:continue
        sold=('stock soldout' in block)
        exact.append((sold,yen,pid,title,url))
    if exact:
        # Prefer in-stock, then cheapest acceptable listing.
        exact.sort(key=lambda x:(x[0],x[1]))
        sold,yen,pid,title,url=exact[0]
        eur=round((yen*jpy_eur)/NM_FACTOR,4)
        source="WEB_CARDRUSH_JP" if not sold else "WEB_CARDRUSH_JP_REFERENCE"
        updates.append((r,source,yen,eur,pid,title,url,sold))
        print(f"cardrush_numbered={r['card_id']}:{r['vid']} {source} JPY={yen} EUR={eur:.4f} {title}",flush=True)
    else:misses.append((r["card_id"],"no_exact"))
    if i%10==0:print(f"cardrush_numbered_progress={i}/{len(rows)} updates={len(updates)}",flush=True)
    time.sleep(.08)
print(f"cardrush_numbered_candidates={len(rows)} updates={len(updates)} misses={len(misses)}",flush=True)

if args.apply and updates:
    sql=["BEGIN;"]
    for r,source,yen,eur,pid,title,url,sold in updates:
        detail=f"CardRush JP exact numbered card {r['lid']:03d}/{r['total']:03d}; product {pid}; listed JPY {yen}; sold_out_reference={'true' if sold else 'false'}; {url}"
        sql.append(f"UPDATE tcg_price_cache SET source='{source}',base_eur={eur:.4f},updated_at=NOW(),resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' WHERE card_id='{q(r['card_id'])}' AND language_code='ja' AND variant_id='{q(r['vid'])}' AND resolution_status='NO_PRICE';")
        sql.append(f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) VALUES('{q(r['card_id'])}','ja','{q(r['vid'])}','{source}',{eur:.4f},NOW());")
    sql.append("COMMIT;")
    subprocess.run(["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],input="\n".join(sql),text=True,check=True)
    print(f"cardrush_numbered_applied={len(updates)}",flush=True)
