#!/usr/bin/env python3
"""Backfill verified German McDonald's Dragon Discovery 2024 scans.

Exact Cardyssey card IDs only. Sources are German product scans from Battle Bear.
"""
import argparse, subprocess, urllib.request

SOURCES = {
    "2024sv-1": "https://www.battle-bear-sb.de/cdn/shop/files/802823_34fd9f7a-2969-4822-96d0-5f7b2b5c0d8a.jpg?v=1769514737&width=2048",
    "2024sv-2": "https://www.battle-bear-sb.de/cdn/shop/files/802824.jpg?v=1751979866&width=2048",
    "2024sv-3": "https://www.battle-bear-sb.de/cdn/shop/files/802825.jpg?v=1751979853&width=2048",
    "2024sv-5": "https://www.battle-bear-sb.de/cdn/shop/files/802827.jpg?v=1769514986&width=2048",
    "2024sv-6": "https://www.battle-bear-sb.de/cdn/shop/files/802828.jpg?v=1751979767&width=2048",
    "2024sv-8": "https://www.battle-bear-sb.de/cdn/shop/files/802830.jpg?v=1747757303&width=2048",
    "2024sv-9": "https://www.battle-bear-sb.de/cdn/shop/files/802831.jpg?v=1751979918&width=2048",
    "2024sv-10": "https://www.battle-bear-sb.de/cdn/shop/files/802832.jpg?v=1747757260&width=2048",
    "2024sv-11": "https://www.battle-bear-sb.de/cdn/shop/files/802833.jpg?v=1747757554&width=2048",
    "2024sv-12": "https://www.battle-bear-sb.de/cdn/shop/files/802834.jpg?v=1741184323&width=2048",
    "2024sv-13": "https://www.battle-bear-sb.de/cdn/shop/files/802835.jpg?v=1769514845&width=2048",
    "2024sv-14": "https://www.battle-bear-sb.de/cdn/shop/files/802836.jpg?v=1751979871&width=2048",
    "2024sv-15": "https://www.battle-bear-sb.de/cdn/shop/files/802837.jpg?v=1741184324&width=2048",
}

def db(sql):
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-c",sql],
        check=True,capture_output=True,text=True).stdout.strip()

def ok(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Cardyssey catalog backfill","Accept":"image/*"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            return 200 <= r.status < 300 and (r.headers.get("Content-Type") or "").lower().startswith("image/")
    except Exception:
        return False

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); args=ap.parse_args()
    existing=set(db("""SELECT card_id FROM catalog_cards_mirror
                       WHERE language_code='de' AND set_id='2024sv'
                         AND image_complete=FALSE AND image_source_url IS NULL""").splitlines())
    matches=[(cid,url) for cid,url in SOURCES.items() if cid in existing and ok(url)]
    print(f"verified={len(matches)} applied={args.apply}")
    if not args.apply: return
    for cid,url in matches:
        q=lambda s:s.replace("'","''")
        db(f"""UPDATE catalog_cards_mirror
               SET image_source_url='{q(url)}', image_complete=FALSE,
                   image_dhash=NULL, source_updated_at=NOW()
               WHERE language_code='de' AND card_id='{q(cid)}'
                 AND image_source_url IS NULL;""")

if __name__=="__main__": main()
