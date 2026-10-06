#!/usr/bin/env python3
"""Backfill verified German McDonald's scans from Bisafans.

Only exact Cardyssey set/local-id rows are considered.
The source pages explicitly list German scans for these sets.
"""
import argparse
import subprocess
import urllib.request

BASES = {
    "2011bw": "https://media.bisafans.de/0394d67/sammelkarten/sets/promos-specials/sw-mcdonalds-2011",
    "2019sm": "https://media.bisafans.de/0394d67/sammelkarten/sets/promos-specials/sm-mcdonalds-2019",
    "2021swsh": "https://media.bisafans.de/0394d67/thumbs/h700/sammelkarten/sets/promos-specials/swsh-mcdonalds-2021",
    "2023sv": "https://media.bisafans.de/0394d67/thumbs/h700/sammelkarten/sets/promos-specials/sv-mcdonalds-2023",
}

def db(sql: str) -> str:
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def find_image(base: str, local_id: str):
    n=f"{int(local_id):03d}"
    for ext in ("jpg","png","jpeg","webp"):
        url=f"{base}/{n}.{ext}"
        req=urllib.request.Request(url,headers={"User-Agent":"Cardyssey catalog backfill","Accept":"image/*"})
        try:
            with urllib.request.urlopen(req,timeout=15) as r:
                ctype=(r.headers.get("Content-Type") or "").lower()
                if 200 <= r.status < 300 and ctype.startswith("image/"):
                    return url
        except Exception:
            pass
    return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    rows=db("""SELECT card_id,set_id,local_id
               FROM catalog_cards_mirror
               WHERE language_code='de'
                 AND image_complete=FALSE
                 AND image_source_url IS NULL
                 AND set_id IN ('2011bw','2019sm','2021swsh','2023sv')
               ORDER BY set_id,local_id""").splitlines()
    matches=[]
    for line in rows:
        cid,sid,lid=line.split("\t")
        url=find_image(BASES[sid],lid)
        if url:
            matches.append((cid,url,sid,lid))
    print(f"verified={len(matches)} of {len(rows)} applied={args.apply}")
    if not args.apply:
        return
    for cid,url,_,_ in matches:
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
