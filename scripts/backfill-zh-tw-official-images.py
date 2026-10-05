#!/usr/bin/env python3
"""Backfill missing Traditional-Chinese card artwork from the official Pokemon Asia catalog.

Safety:
- zh-tw only.
- Existing Cardyssey rows only.
- Match by official expansion code + collector number + normalized exact card name.
- Official duplicate prints with the same identity use the first official catalog image.
- Dry-run by default; --apply only writes image_source_url for currently incomplete rows.
"""
import argparse
import concurrent.futures
import html
import re
import subprocess
import urllib.request

BASE = "https://asia.pokemon-card.com"
UA = {"User-Agent": "Cardyssey-CatalogMirror/1.0 (+official Pokemon Asia catalog backfill)"}

SPECIAL = {
    ("SV-P", "no0"): f"{BASE}/tw/card-img/tw00018358.png",
    ("SV-P", "no1"): f"{BASE}/tw/wp-content/uploads/sites/2/2024/01/tw_news_RL23-24_vol3_Promo_Champion.png",
    ("SV-P", "no2"): f"{BASE}/tw/wp-content/uploads/sites/2/2024/01/tw_news_RL23-24_vol3_Promo_Finalist.png",
    ("SV-P", "no3"): f"{BASE}/tw/wp-content/uploads/sites/2/2024/01/tw_news_RL23-24_vol3_Promo_TOP4.png",
}


def db(sql: str):
    return subprocess.check_output(
        ["docker", "exec", "cardyssey-db", "psql", "-U", "cardyssey", "-d", "cardyssey", "-At", "-F", "\t", "-c", sql],
        text=True,
    ).splitlines()


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", "ignore")


def clean_name(value: str) -> str:
    value = re.sub(r"\[[^]]+\]$", "", value).strip()
    return value


def list_detail_ids(expansion: str):
    ids = []
    page = 1
    while True:
        body = get(f"{BASE}/tw/card-search/list/?expansionCodes={expansion}&pageNo={page}")
        found = list(dict.fromkeys(re.findall(r"/tw/card-search/detail/(\d+)/", body)))
        if not found:
            break
        ids.extend(found)
        total_match = re.search(r"/ 共\s*(\d+)\s*頁", body)
        total = int(total_match.group(1)) if total_match else page
        if page >= total:
            break
        page += 1
    return list(dict.fromkeys(ids))


def parse_detail(item):
    expected_set, detail_id = item
    body = get(f"{BASE}/tw/card-search/detail/{detail_id}/")
    number = re.search(r'class="collectorNumber"[^>]*>\s*([^<]+)', body)
    image = re.search(r'<div class="cardImage">\s*<img src="([^"]+)"', body)
    title = re.search(r'<h1 class="pageHeader cardDetail">(.*?)</h1>', body, re.S)
    expansion = re.search(r"/tw/card-search/list/\?expansionCodes=([^\"&]+)", body)
    if not (number and image and title and expansion):
        return None
    raw_title = re.sub(r"<span[^>]*>.*?</span>", " ", title.group(1), flags=re.S)
    name = html.unescape(re.sub(r"<[^>]+>", " ", raw_title))
    name = re.sub(r"\s+", " ", name).strip()
    local_id = html.unescape(number.group(1)).strip().split("/", 1)[0].strip()
    if expansion.group(1).lower() != expected_set.lower():
        return None
    return expansion.group(1), local_id, name, image.group(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rows = []
    for line in db(
        """SELECT set_id,local_id,card_id,name
           FROM catalog_cards_mirror
           WHERE language_code='zh-tw' AND NOT image_complete
           ORDER BY set_id,local_id"""
    ):
        rows.append(line.split("\t", 3))

    targets = {(set_id, local_id): (card_id, name) for set_id, local_id, card_id, name in rows}
    matches = {}

    # Explicit official event cards whose collector number is intentionally absent.
    for key, url in SPECIAL.items():
        if key in targets:
            matches[key] = url

    ordinary_sets = sorted({set_id for set_id, local_id, _, _ in rows if (set_id, local_id) not in SPECIAL})
    detail_jobs = []
    for set_id in ordinary_sets:
        try:
            detail_jobs.extend((set_id, detail_id) for detail_id in list_detail_ids(set_id))
        except Exception as exc:
            print(f"WARN list {set_id}: {exc}")

    parsed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for item in pool.map(parse_detail, detail_jobs):
            if item:
                parsed.append(item)

    # Keep the first official image for duplicate prints with the same exact identity.
    official = {}
    for set_id, local_id, name, url in parsed:
        key = (set_id.lower(), local_id.lstrip("0") or "0", clean_name(name))
        official.setdefault(key, url)

    for set_id, local_id, _, name in rows:
        if (set_id, local_id) in matches:
            continue
        key = (set_id.lower(), local_id.lstrip("0") or "0", clean_name(name))
        url = official.get(key)
        if url:
            matches[(set_id, local_id)] = url

    unresolved = [(s, l, c, n) for s, l, c, n in rows if (s, l) not in matches]
    print(f"missing={len(rows)} matched={len(matches)} unresolved={len(unresolved)} apply={args.apply}")
    for item in unresolved[:30]:
        print("UNRESOLVED", *item, sep=" | ")

    if not args.apply:
        return

    for set_id, local_id, card_id, _ in rows:
        url = matches.get((set_id, local_id))
        if not url:
            continue
        esc_url = url.replace("'", "''")
        esc_id = card_id.replace("'", "''")
        db(
            f"""UPDATE catalog_cards_mirror
                SET image_source_url='{esc_url}', image_complete=FALSE,
                    image_dhash=NULL, image_local_path=NULL, source_updated_at=NOW()
                WHERE language_code='zh-tw' AND card_id='{esc_id}'
                  AND NOT image_complete;"""
        )


if __name__ == "__main__":
    main()
