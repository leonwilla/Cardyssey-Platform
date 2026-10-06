#!/usr/bin/env python3
"""Backfill exact, verified German card image sources missing upstream.

Only explicit card IDs are allowed. Existing local images are never replaced.
"""
import argparse
import subprocess
import urllib.request

SOURCES = {
    # 30th RGB Mew are global English-only printings even inside the localized DE set.
    "30th-B": "https://cdn.pokedexia.com/cards/me/30C/cards/30c-b/rgb-mu47iptp-high.webp?v=1789569586314",
    "30th-G": "https://cdn.pokedexia.com/cards/me/30C/cards/30c-g/rgb-mu47l29o-high.webp?v=1789569685866",
    "30th-R": "https://cdn.pokedexia.com/cards/me/30C/cards/30c-r/rgb-mu47n3k1-high.webp?v=1789569780779",
    "tk-ex-latia-5": "https://i.ebayimg.com/images/g/nrkAAeSwR3Jo92Rr/s-l1600.webp",
    "tk-ex-latio-10": "https://i.ebayimg.com/images/g/3-AAAeSwrA1psWtw/s-l1600.webp",
    "tk-ex-latio-8": "https://i.ebayimg.com/images/g/RrkAAOSwMhFfcgLo/s-l1600.jpg",
    "tk-ex-latia-3": "https://img.ricardostatic.ch/images/565417a0-81a0-4baf-908c-e3a2f79800a7/t_1800x1350/enekoro-pokemon-310-ex-trainer-kit-latiaslatios-2004",
    "tk-ex-latia-4": "https://img.ricardostatic.ch/images/945a1beb-10d8-4b6a-92e6-5bf75f8cc515/t_1800x1350/pokemon-latias-410-holo-ex-trainer-kit-de",
    "tk-ex-latio-4": "https://img.ricardostatic.ch/images/cdba4645-a1d1-41f6-a4e0-a41a4385c543/t_1800x1350/magnetilo-pokemon-410-ex-trainer-kit-latiaslatios-2004",
    "tk-ex-latio-2": "https://img.kleinanzeigen.de/api/v1/prod-ads/images/0a/0ad003ce-2d6d-41d0-9c36-45a3578fe480?rule=$_59.AUTO",
    "tk-ex-latio-5": "https://img.kleinanzeigen.de/api/v1/prod-ads/images/ef/efccd6e5-646c-4a6b-ab17-02051b4ba48a?rule=$_59.AUTO",
    "tk-ex-latia-1": "https://img.ricardostatic.ch/images/9292728a-bffd-4dd0-a00e-ad1f88e9ec5d/t_1800x1350/pokemon-kindwurm-ex-trainer-kit-latias-110-deutsch",
    "tk-ex-latia-6": "https://img.ricardostatic.ch/images/2fef34d5-1953-452c-ae8c-32699105506d/t_1800x1350/pokemon-eneco-ex-trainer-kit-latias-610-deutsch",
    "tk-ex-latio-1": "https://img.ricardostatic.ch/images/594ffb8c-7d90-494d-b1a6-482d97f6c953/t_1800x1350/pokemon-frizelbliz-ex-trainer-kit-latios-110-deutsch",
    "tk-ex-latio-6": "https://img.ricardostatic.ch/images/e89b97eb-084f-4c78-8efe-22f3aba738c9/t_1800x1350/pokemon-pikachu-610-ex-trainer-kit-latios-ab-fr-1",
    "tk-ex-latio-7": "https://img.ricardostatic.ch/images/68e13ccd-2de8-45a0-8c2d-4f283885be7d/t_1800x1350/pokemon-zigzachs-ex-trainer-kit-latios-710-deutsch",
    "sve-017": "https://sleevee.de/media/a3/62/f1/1755569765/836249.jpg?ts=1755569765",
    "sve-018": "https://sleevee.de/media/cf/84/60/1755569765/836250.jpg?ts=1755569765",
    "sve-019": "https://sleevee.de/media/e5/55/1a/1755569766/836251.jpg?ts=1755569766",
    "sve-020": "https://sleevee.de/media/60/1c/6c/1755569766/836252.jpg?ts=1755569766",
    "sve-021": "https://sleevee.de/media/68/ce/e8/1755569767/836253.jpg?ts=1755569767",
    "sve-022": "https://sleevee.de/media/fc/2b/6a/1755569767/836254.jpg?ts=1755569767",
    "sve-023": "https://sleevee.de/media/45/09/2d/1755569768/836255.jpg?ts=1755569768",
    "sve-024": "https://sleevee.de/media/5b/26/63/1755569768/836256.jpg?ts=1755569768",
    "exu-!": "https://media.bisafans.de/0394d67/sammelkarten/sets/ex-verborgene-maechte/ausrufezeichen-28.jpg",
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
                         AND (image_source_url IS NULL
                              OR image_source_url LIKE 'https://assets.tcgdex.net/%')""").splitlines())
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
                 AND (image_source_url IS NULL
                      OR image_source_url LIKE 'https://assets.tcgdex.net/%');""")

if __name__=="__main__":
    main()
