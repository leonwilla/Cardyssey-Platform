#!/usr/bin/env python3
"""Backfill verified German card artwork from Pokémon's official asset CDN.

Safety rules:
- German rows only.
- Existing Cardyssey rows only; never creates cards.
- Only explicitly allowlisted sets whose official asset naming was verified.
- Never overwrites an existing image_source_url.
- Every derived URL must return a 2xx image response before it is stored.
- Dry-run by default; --apply writes verified matches.
"""
import argparse
import json
import subprocess
import urllib.request

BASE = "https://assets.pokemon.com/static-assets/content-assets/cms2-de-de/img/cards/web"
ALLOWED_SETS = {"mee": "MEE", "mep": "MEP", "svp": "SVP"}


def db(sql: str):
    p = subprocess.run(
        [
            "docker", "exec", "cardyssey-db", "psql",
            "-U", "cardyssey", "-d", "cardyssey",
            "-At", "-F", "\t", "-c", sql,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return p.stdout.splitlines()


def asset_number(local_id: str) -> str:
    value = local_id.strip()
    try:
        return str(int(value))
    except ValueError:
        return value


def image_exists(url: str) -> bool:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Cardyssey catalog backfill",
            "Accept": "image/png,image/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return (
                200 <= response.status < 300
                and (response.headers.get("Content-Type") or "").lower().startswith("image/")
            )
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    set_list = ",".join("'" + s + "'" for s in sorted(ALLOWED_SETS))
    rows = db(
        f"""SELECT card_id,set_id,local_id
            FROM catalog_cards_mirror
            WHERE language_code='de'
              AND image_complete=FALSE
              AND image_source_url IS NULL
              AND set_id IN ({set_list})
            ORDER BY set_id,card_id"""
    )

    matches = []
    for line in rows:
        card_id, set_id, local_id = line.split("\t")
        code = ALLOWED_SETS[set_id]
        number = asset_number(local_id)
        url = f"{BASE}/{code}/{code}_DE_{number}.png"
        if image_exists(url):
            matches.append((card_id, set_id, local_id, url))

    if args.apply:
        for card_id, _, _, url in matches:
            quote = lambda s: s.replace("'", "''")
            db(
                f"""UPDATE catalog_cards_mirror
                    SET image_source_url='{quote(url)}',
                        image_complete=FALSE,
                        image_dhash=NULL,
                        source_updated_at=NOW()
                    WHERE language_code='de'
                      AND card_id='{quote(card_id)}'
                      AND image_source_url IS NULL;"""
            )

    by_set = {}
    for _, set_id, _, _ in matches:
        by_set[set_id] = by_set.get(set_id, 0) + 1

    print(
        json.dumps(
            {
                "language": "de",
                "candidate_rows": len(rows),
                "verified_matches": len(matches),
                "sets": by_set,
                "applied": args.apply,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
