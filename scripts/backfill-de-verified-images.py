#!/usr/bin/env python3
"""Backfill exact, verified German card image sources missing upstream.

Only explicit card IDs are allowed. Existing local images are never replaced.
"""
import argparse
import subprocess
import urllib.request

SOURCES = {
    "ecard2-50a": "https://www.pokemonkarte.de/wp-content/uploads/Golduck-Aquapolis.jpg",
    "ecard2-50b": "https://www.pokemonkarte.de/wp-content/uploads/Golduck-Aquapolis.jpg",
    "ecard2-74a": "https://www.pokemonkarte.de/wp-content/uploads/Drowzee-Aquapolis.jpg",
    "ecard2-74b": "https://www.pokemonkarte.de/wp-content/uploads/Drowzee-Aquapolis.jpg",
    "ecard2-95a": "https://www.pokemonkarte.de/wp-content/uploads/Mr.-Mime-Aquapolis.jpg",
    "ecard2-95b": "https://www.pokemonkarte.de/wp-content/uploads/Mr.-Mime-Aquapolis.jpg",
    "ecard2-103a": "https://www.pokemonkarte.de/wp-content/uploads/Porygon-Aquapolis.jpg",
    "ecard2-103b": "https://www.pokemonkarte.de/wp-content/uploads/Porygon-Aquapolis.jpg",
    "mep-078": "https://cdn.pokedexia.com/cards/me/MEP/cards/de/mep-078-high.webp?v=1781538081484",
    "2023sv-1": "https://www.tradingtoys.de/cdn/shop/files/felori-m23de-001-015-mcdonalds-promo-2023-holo-kaufen-1-917.webp?v=1787074371",
    "2023sv-3": "https://www.tradingtoys.de/cdn/shop/files/kwaks-m23de-003-015-mcdonalds-promo-2023-holo-kaufen-1-708.webp?v=1787074705",
    "2023sv-6": "https://www.tradingtoys.de/cdn/shop/files/pikachu-m23de-006-015-mcdonalds-promo-2023-holo-kaufen-1-879.webp?v=1787073994",
    "2023sv-11": "https://www.tradingtoys.de/cdn/shop/files/klibbe-m23de-011-015-mcdonalds-promo-2023-holo-kaufen-1-217.webp?v=1787250824",
}

def db(sql: str) -> str:
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-c",sql],
        check=True, capture_output=True, text=True
    ).stdout.strip()

def image_ok(url: str) -> bool:
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
                       WHERE language_code='de'
                         AND image_complete=FALSE
                         AND image_source_url IS NULL""").splitlines())
    matches=[(cid,url) for cid,url in SOURCES.items() if cid in existing and image_ok(url)]
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
               WHERE language_code='de'
                 AND card_id='{q(cid)}'
                 AND image_source_url IS NULL;""")

if __name__=="__main__":
    main()
