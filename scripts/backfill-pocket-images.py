#!/usr/bin/env python3
"""Backfill missing English Pokémon TCG Pocket artwork from a public static dataset.

Safety rules:
- English only: the dataset's card images are English prints.
- Existing Cardyssey rows only; never creates cards.
- Exact set code + normalized collector number only.
- Never overwrites an existing image_source_url.
- Dry-run by default; --apply writes only verified manifest matches.
"""
import argparse, json, subprocess, urllib.request

MANIFEST = "https://raw.githubusercontent.com/flibustier/pokemon-tcg-pocket-database/main/dist/cards.no-image.min.json"
IMAGE_BASE = "https://raw.githubusercontent.com/flibustier/pokemon-tcg-pocket-database/main/cards-by-set"

def db(sql):
    p = subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True, capture_output=True, text=True)
    return p.stdout.splitlines()

def norm_number(v):
    s=str(v or "").strip()
    if "/" in s: s=s.split("/",1)[0]
    try: return str(int(s))
    except ValueError: return s.upper()

def load_manifest():
    req=urllib.request.Request(MANIFEST, headers={"User-Agent":"Cardyssey catalog backfill"})
    with urllib.request.urlopen(req, timeout=30) as r:
        rows=json.load(r)
    out={}
    duplicates=set()
    for c in rows:
        key=(str(c.get("set","")).upper(), norm_number(c.get("number")))
        if not key[0] or not key[1]: continue
        if key in out: duplicates.add(key)
        else: out[key]=c
    for key in duplicates: out.pop(key,None)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args=ap.parse_args()
    manifest=load_manifest()
    rows=db("""SELECT card_id,set_id,local_id FROM catalog_cards_mirror
               WHERE language_code='en' AND image_source_url IS NULL
               ORDER BY set_id,card_id""")
    matches=[]
    for line in rows:
        card_id,set_id,local_id=line.split("\t")
        key=(set_id.upper(), norm_number(local_id))
        if key not in manifest: continue
        # URL path is documented by the dataset and derived only after an exact
        # manifest match, so unrelated TCG sets cannot be pulled accidentally.
        url=f"{IMAGE_BASE}/{manifest[key]['set']}/{norm_number(manifest[key]['number'])}.webp"
        matches.append((card_id,url,set_id,local_id))
    if args.apply:
        for card_id,url,_,_ in matches:
            q=lambda s: s.replace("'","''")
            db(f"""UPDATE catalog_cards_mirror
                   SET image_source_url='{q(url)}', image_complete=FALSE,
                       image_dhash=NULL, source_updated_at=NOW()
                   WHERE language_code='en' AND card_id='{q(card_id)}'
                     AND image_source_url IS NULL;""")
    by_set={}
    for _,_,s,_ in matches: by_set[s]=by_set.get(s,0)+1
    print(json.dumps({"language":"en","missing_without_source":len(rows),
                      "matched":len(matches),"sets":by_set,"applied":args.apply},
                     ensure_ascii=False, sort_keys=True))
if __name__=="__main__": main()
