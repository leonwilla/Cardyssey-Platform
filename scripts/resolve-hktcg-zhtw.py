#!/usr/bin/env python3
import argparse,html,json,math,re,subprocess,time,urllib.parse,urllib.request
from collections import defaultdict

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
def fetch(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=25) as r:return r.read().decode("utf-8","ignore")

with urllib.request.urlopen(
    urllib.request.Request("https://api.frankfurter.dev/v2/rate/HKD/EUR",headers={"User-Agent":"Cardyssey-hktcg-price"}),
    timeout=15,
) as r:
    hkd_eur=float(json.load(r)["rate"])
if not math.isfinite(hkd_eur) or hkd_eur<=0:raise SystemExit("HKD/EUR unavailable")

raw=db("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,p.legacy_variant,s.official_count,
       COUNT(*) OVER(PARTITION BY c.card_id,p.language_code) AS open_variants
FROM tcg_price_cache p
JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
WHERE p.language_code='zh-tw' AND p.resolution_status='NO_PRICE'
  AND s.official_count>0
ORDER BY c.set_id,c.local_id,p.variant_id""")
rows=[]
for line in raw.splitlines():
    z=line.split("\t")
    if len(z)!=8:continue
    cid,setid,lid,name,vid,legacy,total,open_variants=z
    if not str(lid).isdigit() or int(open_variants)!=1:continue
    rows.append({
        "card_id":cid,"set_id":setid,"local_id":int(lid),"name":name,
        "variant_id":vid,"legacy":legacy,"official_count":int(total),
    })

wanted_sets=sorted({r["set_id"] for r in rows})
catalog=defaultdict(list)
for si,setid in enumerate(wanted_sets,1):
    seen_ids=set()
    base="https://www.hktcg.com/search?"+urllib.parse.urlencode({"q":setid})
    try:first=fetch(base)
    except Exception as e:
        print(f"hktcg_set_error={setid} error={e!r}",flush=True);continue
    pages=[int(x) for x in re.findall(r'[?&]page=(\d+)',first)]
    max_page=max(pages+[1])
    for page in range(1,min(max_page,20)+1):
        h=first if page==1 else fetch(base+"&page="+str(page))
        found=0
        for m in re.finditer(r'<article\b[^>]*class="[^"]*hktcg-product-card[^"]*"[^>]*>.*?</article>',h,re.S):
            block=m.group(0)
            # HKTCG also returns Japanese products for the same set number.
            # An explicit Traditional-Chinese product label is mandatory.
            category=re.search(r'<div class="hktcg-product-card__copy">\s*<p>(.*?)</p>',block,re.S)
            if not category or not re.search(r'繁中|繁體|繁体|中文版|Chinese',clean(category.group(1)),re.I):
                continue
            titlem=re.search(r'<h3[^>]*>(.*?)</h3>',block,re.S)
            if not titlem:continue
            title=clean(titlem.group(1))
            mm=re.match(rf'^{re.escape(setid)}\s+0*(\d+)/0*(\d+)\b',title,re.I)
            if not mm:continue
            local=int(mm.group(1));den=int(mm.group(2))
            if den<=0:continue
            hrefm=re.search(r'data-product-url="([^"]+)"',block)
            if not hrefm:continue
            href=html.unescape(hrefm.group(1)).split("?",1)[0]
            if not href.startswith("/products/") or href in seen_ids:continue
            seen_ids.add(href)
            pm=re.search(r'<span class=money>HK\$([0-9,.]+)</span>',block)
            if not pm:continue
            hkd=float(pm.group(1).replace(",",""))
            if not math.isfinite(hkd) or hkd<=0:continue
            sold=("is-soldout" in m.group(0).split(">",1)[0]) or ("售罄" in block)
            catalog[(setid,local,den)].append({
                "hkd":hkd,"sold":sold,"title":title,
                "url":"https://www.hktcg.com"+href,
            })
            found+=1
        if page>1 and found==0:break
        if page<max_page:time.sleep(0.08)
    print(f"hktcg_set={setid} pages={max_page} products={sum(len(v) for k,v in catalog.items() if k[0]==setid)}",flush=True)

updates=[];misses=0;den_mismatch=0
for r in rows:
    exact=catalog.get((r["set_id"],r["local_id"],r["official_count"]),[])
    if not exact:
        # Accept a single denominator from this exact set+number if catalog
        # official_count differs from retailer metadata.
        alt=[v for (sid,lid,den),vals in catalog.items() if sid==r["set_id"] and lid==r["local_id"] for v in vals]
        dens={den for (sid,lid,den) in catalog if sid==r["set_id"] and lid==r["local_id"]}
        if len(dens)==1 and alt:
            exact=alt;den_mismatch+=1
    if not exact:
        misses+=1;continue
    # Same set and number are not sufficient to identify a printing.
    # Require the Chinese card name to match the complete product suffix.
    identity=[]
    for candidate in exact:
        match=re.match(rf'^{re.escape(r["set_id"])}\s+\d+/\d+\s+(.+)$',candidate["title"],re.I)
        if match and re.sub(r'\s+','',clean(match.group(1))) == re.sub(r'\s+','',r["name"]):
            identity.append(candidate)
    if len(identity)!=1:
        misses+=1;continue
    exact=identity
    live=[x for x in exact if not x["sold"]]
    chosen=min(live or exact,key=lambda x:x["hkd"])
    source="WEB_HKTCG" if live else "WEB_HKTCG_REFERENCE"
    eur=round((chosen["hkd"]*hkd_eur)/NM_FACTOR,4)
    updates.append((r,chosen,source,eur))

print(f"hktcg_candidates={len(rows)} updates={len(updates)} live={sum(1 for x in updates if x[2]=='WEB_HKTCG')} soldout_reference={sum(1 for x in updates if x[2]=='WEB_HKTCG_REFERENCE')} misses={misses} denominator_fallback={den_mismatch} hkd_eur={hkd_eur}",flush=True)
for r,item,source,eur in updates[:40]:
    print(f"hktcg_match={r['card_id']} {source} HKD={item['hkd']:.2f} EUR={eur:.4f} {item['title']}",flush=True)

if not args.apply or not updates:raise SystemExit(0)
sql=["BEGIN;"]
for r,item,source,eur in updates:
    detail=(
        f"HKTCG exact Traditional Chinese single {r['set_id']} {r['local_id']:03d}/{r['official_count']}; "
        f"listed HKD {item['hkd']:.2f}; sold_out_reference={'true' if item['sold'] else 'false'}; {item['url']}"
    )
    sql.append(
        f"UPDATE tcg_price_cache SET source='{source}',base_eur={eur:.4f},updated_at=NOW(),"
        f"resolution_status='PRICE_FOUND',failure_detail='{q(detail)}',next_attempt_at=NOW()+INTERVAL '7 days' "
        f"WHERE card_id='{q(r['card_id'])}' AND language_code='zh-tw' AND variant_id='{q(r['variant_id'])}' "
        f"AND resolution_status='NO_PRICE';"
    )
    sql.append(
        f"INSERT INTO tcg_price_history(card_id,language_code,variant_id,source,base_eur,captured_at) "
        f"VALUES('{q(r['card_id'])}','zh-tw','{q(r['variant_id'])}','{source}',{eur:.4f},NOW());"
    )
sql.append("COMMIT;")
subprocess.run(
    ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
    input="\n".join(sql),text=True,check=True,
)
print(f"hktcg_applied={len(updates)}",flush=True)
