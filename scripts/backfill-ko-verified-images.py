#!/usr/bin/env python3
"""Backfill exact verified Korean card images when old official CDN URLs are dead."""
import argparse, subprocess, urllib.request

SOURCES = {
    "official_ko_16df4fdbdd0295c50414886d":
        "https://cdn6966.templcdn.com/wp-content/uploads/2021/07/KR_043BW.jpg",
    "official_ko_7b4fab2b675e6f123d646e71":
        "https://img.carahi.kr/card-thumbs/v1/site-images/v1/pokemon-korea/8aa4c3bb93354b0ab90f65eb6f93abfbdc31d31a0e4bdbce2bf12d23b438f081.webp",
}

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def ok(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Cardyssey catalog backfill","Accept":"image/*"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            return 200 <= r.status < 300 and (r.headers.get("Content-Type") or "").lower().startswith("image/")
    except Exception:
        return False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    existing=set(db("""SELECT card_id FROM catalog_cards_mirror
                       WHERE language_code='ko'
                         AND image_complete=FALSE""").splitlines())
    matches=[(cid,url) for cid,url in SOURCES.items() if cid in existing and ok(url)]
    print(f"verified={len(matches)} applied={args.apply}")
    if not args.apply:
        return
    for cid,url in matches:
        q=lambda s:s.replace("'","''")
        db(f"""UPDATE catalog_cards_mirror
               SET image_source_url='{q(url)}',
                   image_complete=FALSE,
                   image_dhash=NULL,
                   source_updated_at=NOW()
               WHERE language_code='ko'
                 AND card_id='{q(cid)}';""")

if __name__=="__main__":
    main()
