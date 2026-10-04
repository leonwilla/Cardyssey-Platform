#!/usr/bin/env python3
"""Fill missing JA/ZH-CN catalog image sources from pokemontcgapi.com.

This is intentionally conservative: it only updates an existing Cardyssey card when
both the set and collector number resolve uniquely. It never creates cards and never
uses translated WEST images as localized DE/EN artwork.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.pokemontcgapi.com/v1"
REGIONS = {"ja": "JP", "zh-cn": "CN"}
IMAGE_HOST = "img.pokemontcgapi.com"


def psql_json(sql):
    result = subprocess.run(
        ["docker", "exec", "-i", "cardyssey-db", "sh", "-lc",
         'exec psql -X -q -t -A -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        input="SELECT COALESCE(json_agg(x), '[]'::json)::text FROM (" + sql + ") x;",
        text=True, check=True, capture_output=True,
    )
    return json.loads(result.stdout.strip() or "[]")


def psql(sql):
    subprocess.run(
        ["docker", "exec", "-i", "cardyssey-db", "sh", "-lc",
         'exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        input=sql, text=True, check=True,
    )


def api_get(url, key):
    request = urllib.request.Request(url, headers={
        "X-Api-Key": key,
        "User-Agent": "Cardyssey-Catalog/1.0 (+https://cardyssey.de)",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError("API returned HTTP " + str(response.status))
            return json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read(1000).decode("utf-8", "replace")
        raise RuntimeError(f"API returned HTTP {error.code}: {body}") from error


def norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def number(value):
    value = str(value or "").strip().upper()
    if "/" in value:
        value = value.split("/", 1)[0]
    value = value.lstrip("0") or "0"
    return value


def image_url(card):
    direct = card.get("image_url")
    if direct:
        return direct
    images = card.get("images") or []
    normal = [row.get("url") for row in images
              if row.get("face") == "FRONT" and row.get("size") == "NORMAL" and row.get("url")]
    return normal[0] if len(normal) == 1 else None


def verified_image(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != IMAGE_HOST:
        raise ValueError("Unexpected image host")
    return url


def local_missing(language):
    lang = language.replace("'", "''")
    return psql_json(f"""
        SELECT c.card_id, c.set_id, c.local_id, c.name, s.name AS set_name
        FROM catalog_cards_mirror c
        LEFT JOIN catalog_sets_mirror s
          ON s.language_code=c.language_code AND s.set_id=c.set_id
        WHERE c.language_code='{lang}'
          AND c.image_local_path IS NULL
          AND c.image_source_url IS NULL
          AND LEFT(c.card_id, 9) <> 'official_'
        ORDER BY c.set_id, c.local_id, c.card_id
    """)


def api_sets(region, key):
    url = API + "/sets?" + urllib.parse.urlencode({
        "region": region, "limit": 250, "orderBy": "release_date"
    })
    rows = []
    while url:
        page = api_get(url, key)
        rows.extend(page.get("data") or [])
        url = (page.get("links") or {}).get("next")
    return rows


def set_candidates(local, remote_sets):
    code = norm(local["set_id"])
    name_key = norm(local.get("set_name"))
    by_code = [
        item for item in remote_sets
        if code and code in {norm(item.get("id")), norm(item.get("code")), norm(item.get("legacy_id"))}
    ]
    if len(by_code) == 1:
        return by_code
    if name_key:
        by_name = [item for item in remote_sets if norm(item.get("name")) == name_key]
        if len(by_name) == 1:
            return by_name
    return []


def cards_for_set(code, key):
    url = API + "/sets/" + urllib.parse.quote(str(code), safe="") + "/cards?" + urllib.parse.urlencode({
        "limit": 250, "orderBy": "id", "include": "images,set"
    })
    rows = []
    while url:
        page = api_get(url, key)
        rows.extend(page.get("data") or [])
        url = (page.get("links") or {}).get("next")
    return rows


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def apply_matches(language, matches):
    if not matches:
        return
    values = ",\n".join(
        "(" + ",".join(map(sql_literal, (language, card_id, url))) + ")"
        for card_id, url in matches
    )
    psql(f"""
        BEGIN;
        CREATE TEMP TABLE image_fallback(language_code TEXT, card_id TEXT, image_url TEXT) ON COMMIT DROP;
        INSERT INTO image_fallback VALUES {values};
        UPDATE catalog_cards_mirror c
        SET image_source_url=f.image_url,
            image_complete=FALSE,
            image_dhash=NULL,
            source_updated_at=NOW()
        FROM image_fallback f
        WHERE c.language_code=f.language_code
          AND c.card_id=f.card_id
          AND c.image_local_path IS NULL
          AND c.image_source_url IS NULL;
        COMMIT;
    """)


def sync_language(language, key, apply):
    region = REGIONS[language]
    missing = local_missing(language)
    remote_sets = api_sets(region, key)
    grouped = {}
    for card in missing:
        grouped.setdefault((card["set_id"], card.get("set_name")), []).append(card)

    matches, unresolved_sets, unresolved_cards = [], 0, 0
    for (_, _), local_cards in grouped.items():
        candidates = set_candidates(local_cards[0], remote_sets)
        if len(candidates) != 1:
            unresolved_sets += 1
            unresolved_cards += len(local_cards)
            continue
        remote_set = candidates[0]
        remote_cards = cards_for_set(remote_set.get("code") or remote_set.get("id"), key)
        by_number = {}
        for remote in remote_cards:
            by_number.setdefault(number(remote.get("number")), []).append(remote)
        for local in local_cards:
            candidates = by_number.get(number(local["local_id"]), [])
            usable = []
            for candidate in candidates:
                url = image_url(candidate)
                if url:
                    usable.append((candidate, verified_image(url)))
            # Number must identify exactly one image in the already-verified set.
            if len(usable) == 1:
                matches.append((local["card_id"], usable[0][1]))
            else:
                unresolved_cards += 1

    if apply:
        apply_matches(language, matches)
    print(json.dumps({
        "language": language,
        "region": region,
        "missing_before": len(missing),
        "matched": len(matches),
        "unresolved_sets": unresolved_sets,
        "unresolved_cards": unresolved_cards,
        "applied": bool(apply),
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--languages", default="ja,zh-cn")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    languages = [item.strip() for item in args.languages.split(",") if item.strip()]
    if any(item not in REGIONS for item in languages):
        parser.error("Supported fallback languages: ja,zh-cn")
    key = os.environ.get("PTCG_API_KEY", "").strip()
    if not key:
        parser.error("PTCG_API_KEY is required")
    for language in languages:
        sync_language(language, key, args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
