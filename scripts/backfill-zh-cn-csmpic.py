#!/usr/bin/env python3
"""Backfill all 48 genuine Simplified-Chinese CSMPiC card images.

PixelBinder's CSMPiC checklist exposes exact CardTrader blueprint images for
all 48 numbered printings. This importer accepts only CardTrader image URLs,
requires one unique 001..048 mapping, verifies every URL is an image, and only
updates existing zh-cn CSMPiC rows.
"""
import argparse
import concurrent.futures
import html
import re
import subprocess
import urllib.request

INDEX = "https://pixel-binder.com/cards/csmpic/"
EXPECTED = {f"{n:03d}" for n in range(1, 49)}
IMAGE_RE = re.compile(
    r'https://cardtrader\.com/uploads/blueprints/image/[^"\'<> ]+'
    r'-(\d{3})-024-csmpic-battle-party-set-reward-pack\.(?:webp|png|jpg|jpeg)',
    re.I,
)

def db(sql: str) -> str:
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def fetch_text(url: str) -> str:
    req=urllib.request.Request(url,headers={"User-Agent":"Cardyssey catalog backfill"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","replace")

def image_ok(item):
    number,url=item
    req=urllib.request.Request(url,headers={"User-Agent":"Cardyssey catalog backfill","Accept":"image/*"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            return item if 200 <= r.status < 300 and (r.headers.get("Content-Type") or "").lower().startswith("image/") else None
    except Exception:
        return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()

    page=html.unescape(fetch_text(INDEX))
    mapping={}
    for match in IMAGE_RE.finditer(page):
        url=match.group(0)
        number=match.group(1)
        previous=mapping.setdefault(number,url)
        if previous != url:
            raise SystemExit(f"ambiguous image mapping for {number}")

    if set(mapping) != EXPECTED:
        missing=sorted(EXPECTED-set(mapping))
        extra=sorted(set(mapping)-EXPECTED)
        raise SystemExit(f"expected 48 exact images; got {len(mapping)} missing={missing} extra={extra}")

    rows=db("""SELECT local_id,card_id FROM catalog_cards_mirror
               WHERE language_code='zh-cn' AND set_id='CSMPiC'
               ORDER BY local_id""").splitlines()
    dbmap={local:cid for local,cid in (row.split("\t") for row in rows)}
    if set(dbmap) != EXPECTED:
        raise SystemExit(f"database CSMPiC rows are not exact 001..048: {len(dbmap)} rows")

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        verified=[x for x in ex.map(image_ok,sorted(mapping.items())) if x]
    if len(verified) != 48:
        raise SystemExit(f"only {len(verified)}/48 image URLs verified")

    print(f"verified=48 applied={args.apply}")
    if not args.apply:
        return

    for number,url in verified:
        cid=dbmap[number]
        q=lambda s:s.replace("'","''")
        db(f"""UPDATE catalog_cards_mirror
               SET image_source_url='{q(url)}',
                   image_complete=FALSE,
                   image_dhash=NULL,
                   source_updated_at=NOW()
               WHERE language_code='zh-cn'
                 AND set_id='CSMPiC'
                 AND card_id='{q(cid)}';""")

if __name__=="__main__":
    main()
