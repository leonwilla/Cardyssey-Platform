#!/usr/bin/env python3
"""Backfill missing Traditional-Chinese card images from the official Pokemon Asia card search.

Only explicitly allow-listed Taiwan expansion codes are accepted. The script maps
official collector numbers to official image URLs and only fills currently missing
image_source_url values; it never substitutes artwork from another language.
"""
import argparse
import concurrent.futures
import re
import subprocess
import urllib.request

BASE = "https://asia.pokemon-card.com"
ALLOWED_SETS = {"SV2a", "SV3"}
UA = "Cardyssey-Catalog/1.0 (+https://cardyssey.de)"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read().decode("utf-8", "ignore")


def detail_ids(set_id: str) -> list[str]:
    first = fetch(f"{BASE}/tw/card-search/list/?expansionCodes={set_id}")
    match = re.search(r'class="resultTotalPages">\s*/\s*共\s*(\d+)\s*頁', first)
    if not match:
        raise RuntimeError(f"Could not determine result pages for {set_id}")
    pages = int(match.group(1))
    ids: list[str] = []
    for page in range(1, pages + 1):
        html = first if page == 1 else fetch(
            f"{BASE}/tw/card-search/list/?expansionCodes={set_id}&pageNo={page}"
        )
        ids.extend(re.findall(r"/tw/card-search/detail/(\d+)/", html))
    return list(dict.fromkeys(ids))


def parse_detail(args: tuple[str, str]) -> tuple[str, str, str] | None:
    set_id, detail_id = args
    html = fetch(f"{BASE}/tw/card-search/detail/{detail_id}/")
    if set_id not in html:
        return None
    number = re.search(r"(\d{3})\s*/\s*(\d{3})", html)
    image = re.search(
        r'data-original="(https://asia\.pokemon-card\.com/tw/card-img/[^"]+)"', html
    )
    if not number or not image:
        return None
    return detail_id, number.group(1), image.group(1)


def psql(sql: str, output: bool = False) -> str:
    cmd = [
        "docker", "exec", "cardyssey-db", "psql", "-U", "cardyssey", "-d", "cardyssey",
        "-At", "-F", "|", "-v", "ON_ERROR_STOP=1", "-c", sql,
    ]
    result = subprocess.run(cmd, text=True, check=True, capture_output=output)
    return result.stdout if output else ""


def quote(value: str) -> str:
    return value.replace("'", "''")


def backfill(set_id: str, apply: bool) -> tuple[int, int]:
    ids = detail_ids(set_id)
    rows: list[tuple[str, str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for row in pool.map(parse_detail, [(set_id, detail_id) for detail_id in ids]):
            if row:
                rows.append(row)

    by_number: dict[str, list[tuple[int, str]]] = {}
    for detail_id, number, image in rows:
        by_number.setdefault(number, []).append((int(detail_id), image))

    missing = psql(
        "SELECT card_id,local_id FROM catalog_cards_mirror "
        f"WHERE language_code='zh-tw' AND set_id='{quote(set_id)}' "
        "AND NOT image_complete AND image_source_url IS NULL ORDER BY local_id;",
        output=True,
    )
    targets = [line.split("|", 1) for line in missing.splitlines() if "|" in line]
    updates: list[tuple[str, str]] = []
    for card_id, number in targets:
        choices = by_number.get(number)
        if choices:
            updates.append((card_id, min(choices)[1]))

    if apply and updates:
        values = ",".join(
            f"('{quote(card_id)}','{quote(image)}')" for card_id, image in updates
        )
        psql(
            "UPDATE catalog_cards_mirror c "
            "SET image_source_url=v.url,source_updated_at=NOW() "
            f"FROM (VALUES {values}) AS v(card_id,url) "
            "WHERE c.language_code='zh-tw' AND c.card_id=v.card_id "
            "AND c.image_source_url IS NULL;"
        )
    return len(targets), len(updates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sets", default="SV2a,SV3")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sets = [item.strip() for item in args.sets.split(",") if item.strip()]
    invalid = [item for item in sets if item not in ALLOWED_SETS]
    if invalid:
        parser.error("Unsupported Taiwan set(s): " + ", ".join(invalid))
    for set_id in sets:
        missing, mapped = backfill(set_id, args.apply)
        print(f"{set_id}: missing_without_source={missing} official_matches={mapped} apply={args.apply}")


if __name__ == "__main__":
    main()
