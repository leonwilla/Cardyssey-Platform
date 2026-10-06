#!/usr/bin/env python3
"""Backfill German Pokémon TCG Pocket B2a artwork.

Source pattern was verified against the German card pages at
pokemontcgpocket.app. Exact existing Cardyssey rows only; each URL must return
an image before it is stored.
"""
import argparse, subprocess, urllib.request, concurrent.futures

BASE = "https://game.pokemontcgpocket.app/de/tcgp/B2a"

def db(sql: str) -> str:
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
         "-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def norm(v: str) -> str:
    s=v.strip()
    try:
        return f"{int(s):03d}"
    except ValueError:
        return s

def probe(row):
    cid,lid=row.split("\t")
    n=norm(lid)
    url=f"{BASE}/{n}/high.webp"
    req=urllib.request.Request(url,headers={"User-Agent":"Cardyssey catalog backfill","Accept":"image/webp,image/*"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            ok=200 <= r.status < 300 and (r.headers.get("Content-Type") or "").lower().startswith("image/")
            if ok:
                return cid,url
    except Exception:
        pass
    return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    rows=db("""SELECT card_id,local_id
               FROM catalog_cards_mirror
               WHERE language_code='de'
                 AND set_id='B2a'
                 AND image_complete=FALSE
                 AND image_source_url IS NULL
               ORDER BY local_id""").splitlines()
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
        matches=[x for x in ex.map(probe,rows) if x]
    print(f"verified={len(matches)} of {len(rows)} applied={args.apply}")
    if not args.apply:
        return
    for cid,url in matches:
        q=lambda s:s.replace("'","''")
        db(f"""UPDATE catalog_cards_mirror
               SET image_source_url='{q(url)}',
                   image_complete=FALSE,
                   image_dhash=NULL,
                   source_updated_at=NOW()
               WHERE language_code='de'
                 AND card_id='{q(cid)}'
                 AND image_source_url IS NULL;""")

if __name__=="__main__":
    main()
