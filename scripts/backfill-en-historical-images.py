#!/usr/bin/env python3
"""Backfill verified English historical card images from exact allowlisted sources.

Safety:
- English only.
- Existing rows only.
- Exact card_id mapping only.
- Never overwrites an existing source.
"""
import argparse
import subprocess

SOURCES = {
    "hgssp-HGSS18": (
        "https://www.pokemonkarte.de/wp-content/uploads/"
        "Tropical-Tidal-Wave-18-HeartGold-SoulSilver-Promos.png"
    ),
    "30th-G": "https://www.pokemonkarte.de/wp-content/uploads/tcg_30th_celebration_g.jpg",
    "30th-R": "https://www.pokemonkarte.de/wp-content/uploads/tcg_30th_celebration_r.jpg",
    "30th-B": "https://www.pokemonkarte.de/wp-content/uploads/tcg_30th_celebration_b.jpg",
}

def db(sql: str) -> str:
    return subprocess.run(
        ["docker", "exec", "cardyssey-db", "psql", "-U", "cardyssey", "-d", "cardyssey",
         "-At", "-c", sql],
        check=True, capture_output=True, text=True
    ).stdout.strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    rows = db("""SELECT card_id FROM catalog_cards_mirror
                 WHERE language_code='en' AND image_source_url IS NULL
                 ORDER BY card_id""").splitlines()
    matches = [(cid, SOURCES[cid]) for cid in rows if cid in SOURCES]
    print(f"matches={len(matches)} applied={args.apply}")
    if not args.apply:
        return
    for cid, url in matches:
        q = lambda s: s.replace("'", "''")
        db(f"""UPDATE catalog_cards_mirror
               SET image_source_url='{q(url)}',
                   image_complete=FALSE,
                   image_dhash=NULL,
                   source_updated_at=NOW()
               WHERE language_code='en'
                 AND card_id='{q(cid)}'
                 AND image_source_url IS NULL;""")

if __name__ == "__main__":
    main()
