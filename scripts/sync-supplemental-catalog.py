#!/usr/bin/env python3
"""Incremental supplemental catalog import. Standard library only; never executes upstream code."""
import argparse
import base64
import collections
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

REPOSITORY = "https://github.com/type-null/PTCG-database.git"
DIRECTORIES = {"ja": "data_jp", "ko": "data_ko", "zh-tw": "data_tc"}
HOSTS = {
    "ja": {"www.pokemon-card.com"},
    "ko": {"pokemoncard.co.kr", "cards.image.pokemonkorea.co.kr"},
    "zh-tw": {"asia.pokemon-card.com"},
    "th": {"asia.pokemon-card.com"},
    "id": {"asia.pokemon-card.com"},
}


def official_url(url, language):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("https", "http") or parsed.hostname not in HOSTS[language]:
        raise ValueError("Non-official source/image host for " + language)
    if parsed.username or parsed.password:
        raise ValueError("Credentials in source URL")
    if language in ("zh-tw", "th", "id"):
        locale = {"zh-tw": "tw"}.get(language, language)
        if not parsed.path.startswith("/" + locale + "/"):
            raise ValueError("Wrong image/source locale")
    return urllib.parse.urlunsplit(parsed._replace(scheme="https"))


def record(raw, language, revision, species):
    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
        raise ValueError("Invalid card object")
    name, code, number = (str(raw.get(key, "")).strip() for key in ("name", "set_name", "number"))
    if not name or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,49}", code):
        raise ValueError("Missing name or unverified set code")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/._-]{0,39}", number):
        raise ValueError("Missing or ambiguous printed number")
    source = official_url(str(raw.get("url", "")), language)
    image = official_url(str(raw.get("img", "")), language)
    if not urllib.parse.urlsplit(image).path.lower().endswith((".jpg", ".jpeg", ".png")):
        raise ValueError("Unsupported source image format")
    source_id = "official_" + language.replace("-", "_") + "_" + hashlib.sha256(source.encode()).hexdigest()[:24]
    total = str(raw.get("set_total", "0"))
    total = int(total) if total.isdigit() else 0
    dex = raw.get("pokedex_number")
    if isinstance(dex, list):
        dex = dex[0] if len(dex) == 1 else None
    german = species.get(str(dex))
    return {
        "sourceId": source_id, "sourceUrl": source, "revision": revision,
        "germanSpecies": german, "allowMatch": True,
        "details": {
            "id": source_id, "localId": number, "name": name, "languageCode": language,
            "imageBase": image, "imageLanguage": language, "setId": code,
            "setName": str(raw.get("set_full_name") or code), "officialCount": total,
            "rarity": raw.get("rarity") or None, "variants": [],
        },
    }


def avoid_ambiguous_matches(records):
    groups = collections.defaultdict(list)
    for item in records:
        card = item["details"]
        groups[(card["languageCode"], card["setId"].upper(), card["localId"].lstrip("0"), card["name"])].append(item)
    for items in groups.values():
        if len({item["details"]["imageBase"] for item in items}) > 1:
            for item in items:
                item["allowMatch"] = False
    return records


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self, own=False):
        return " ".join(c if isinstance(c, str) else ("" if own else c.text()) for c in self.children).strip()

    def find(self, tag=None, cls=None):
        result = []
        if (tag is None or self.tag == tag) and (cls is None or cls in self.attrs.get("class", "").split()):
            result.append(self)
        for c in self.children:
            if isinstance(c, Node):
                result.extend(c.find(tag, cls))
        return result


class Document(HTMLParser):
    VOID = {"img", "br", "hr", "meta", "input", "link", "source", "wbr", "area", "base", "embed", "param", "col"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_asia(html, language, url):
    root = Document(html).root
    name = root.find("h1", "cardDetail")[0].text(own=True)
    image = root.find(cls="cardImage")[0].find("img")[0].attrs["src"]
    collector = root.find("span", "collectorNumber")[0].text()
    # Only an explicitly linked product code is accepted. Never derive codes from a similar language.
    links = root.find("section", "expansionLinkColumn")[0].find("a")
    products = [(urllib.parse.parse_qs(urllib.parse.urlsplit(a.attrs.get("href", "")).query).get("expansionCodes", []), a.text()) for a in links]
    products = [(codes[0], name) for codes, name in products if len(codes) == 1]
    if len(set(code for code, _ in products)) != 1:
        raise ValueError("Ambiguous/missing product code")
    match = re.fullmatch(r"([A-Za-z0-9._-]+)\s*/\s*(\d+)", collector)
    if not match:
        raise ValueError("Ambiguous collector number")
    return {"name": name, "set_name": products[0][0], "set_full_name": products[0][1],
            "number": match[1], "set_total": match[2], "url": url,
            "img": urllib.parse.urljoin(url, image)}


def psql(sql):
    # Credentials remain inside the database container; never echoed into Actions logs.
    subprocess.run(["docker", "exec", "-i", "cardyssey-db", "sh", "-lc",
                    'exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
                   input=sql, text=True, check=True)


def sql_json(value):
    data = base64.b64encode(json.dumps(value, ensure_ascii=False).encode()).decode()
    return "convert_from(decode('" + data + "', 'base64'), 'UTF8')::jsonb"


def import_rows(rows, apply):
    if not apply or not rows:
        return
    sql = Path(__file__).with_name("catalog-supplemental-import.sql").read_text()
    for start in range(0, len(rows), 100):
        values = ",\n".join("(" + sql_json(row) + ")" for row in rows[start:start + 100])
        psql("BEGIN; CREATE TEMP TABLE source_rows(payload JSONB) ON COMMIT DROP;\n"
             "INSERT INTO source_rows VALUES " + values + ";\n" + sql + "\nCOMMIT;")


def status(source, state, count, error, apply):
    print(json.dumps({"source": source, "status": state, "cards": count, "error": error}, ensure_ascii=False), flush=True)
    if apply:
        p = sql_json({"source": source, "status": state, "count": count, "error": error})
        psql("INSERT INTO catalog_supplemental_sync(source,status,card_count,last_error) "
             "SELECT p->>'source',p->>'status',(p->>'count')::integer,p->>'error' FROM (SELECT " + p + " AS p) x "
             "ON CONFLICT(source) DO UPDATE SET status=EXCLUDED.status,card_count=EXCLUDED.card_count,"
             "last_error=EXCLUDED.last_error,updated_at=NOW();")


def checkout(cache):
    repo = cache / "source"
    if not (repo / ".git").is_dir():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", "--depth=1", REPOSITORY, str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "data_jp", "data_ko", "data_tc", "code"], check=True)
    subprocess.run(["git", "-C", str(repo), "fetch", "--depth=1", "origin", "main"], check=True)
    # This is a dedicated data cache; no upstream Python/JS is ever run.
    subprocess.run(["git", "-C", str(repo), "checkout", "--detach", "FETCH_HEAD"], check=True)
    revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    return repo, revision


class Fetcher:
    def __init__(self, deadline, delay):
        self.deadline, self.delay, self.last = deadline, delay, 0.0

    def get(self, url):
        if time.monotonic() >= self.deadline:
            raise TimeoutError("Time budget reached; cached progress will resume next run")
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        request = urllib.request.Request(url, headers={"User-Agent": "Cardyssey-Catalog/1.0 (+https://cardyssey.de)"})
        # No challenge bypass. A refusal leaves a visible source error.
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise ValueError("Source returned HTTP " + str(response.status))
            data = response.read(5_000_001)
            if len(data) > 5_000_000:
                raise ValueError("Source page exceeds size limit")
            return data.decode("utf-8")


def asia_records(language, cache, fetcher, apply):
    folder = cache / language
    folder.mkdir(parents=True, exist_ok=True)
    seen, page, count, rejected = set(), 1, 0, 0
    batch = []
    try:
        while True:
            url = f"https://asia.pokemon-card.com/{language}/card-search/list/?pageNo={page}"
            root = Document(fetcher.get(url)).root
            links = {urllib.parse.urljoin(url, a.attrs.get("href", "")) for a in root.find("a")
                     if re.fullmatch(f"/{language}/card-search/detail/[0-9]+/", urllib.parse.urlsplit(a.attrs.get("href", "")).path)}
            if not links:
                raise ValueError(f"No card links on listing page {page}; source not complete")
            if links <= seen:
                raise ValueError(f"Repeated listing page {page}; source not complete")
            for link in sorted(links - seen):
                number = urllib.parse.urlsplit(link).path.rstrip("/").split("/")[-1]
                local = folder / (number + ".json")
                try:
                    if local.exists() and time.time() - local.stat().st_mtime < 30 * 86400:
                        raw = json.loads(local.read_text())
                    else:
                        raw = parse_asia(fetcher.get(link), language, link)
                        tmp = local.with_suffix(".tmp")
                        tmp.write_text(json.dumps(raw, ensure_ascii=False))
                        tmp.replace(local)
                    row = record(raw, language, time.strftime("%Y-%m-%d"), {})
                    # Streaming pages cannot establish global print uniqueness. Keep their own IDs.
                    row["allowMatch"] = False
                    batch.append(row)
                    count += 1
                except (ValueError, IndexError, KeyError) as error:
                    rejected += 1
                    print(f"Skipped {link}: {error}", file=sys.stderr)
                if len(batch) >= 100:
                    import_rows(batch, apply)
                    batch.clear()
            seen.update(links)
            pages = [int(value) for a in root.find("a")
                     for value in urllib.parse.parse_qs(urllib.parse.urlsplit(a.attrs.get("href", "")).query).get("pageNo", [])
                     if value.isdigit()]
            if not any(value > page for value in pages):
                break
            page += 1
            if page > 5000:
                raise ValueError("Listing page safety limit exceeded")
    finally:
        import_rows(batch, apply)
    return count, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache/cardyssey-catalog")
    parser.add_argument("--apply", action="store_true", help="Import into the local cardyssey-db container")
    parser.add_argument("--languages", default="ko,ja,zh-tw,th,id")
    parser.add_argument("--max-seconds", type=int, default=18000)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    languages = args.languages.split(",")
    if any(lang not in HOSTS for lang in languages):
        parser.error("Supported sources: ko,ja,zh-tw,th,id. No verified zh-cn source is configured.")
    args.cache.mkdir(parents=True, exist_ok=True)
    with (args.cache / "sync.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.apply:
            psql("SELECT 1 FROM catalog_supplemental_cards LIMIT 0;")
        deadline = time.monotonic() + max(60, args.max_seconds)
        repo, revision = checkout(args.cache) if any(lang in DIRECTORIES for lang in languages) else (None, None)
        species = {}
        if repo:
            names = json.loads((repo / "code/species_dex_intl.json").read_text()).get("de", {})
            for name, dex in names.items():
                species.setdefault(str(dex), name[:1].upper() + name[1:])
        failed = False
        for language in languages:
            source = ("type-null/" if language in DIRECTORIES else "pokemon-asia/") + language
            status(source, "running", 0, None, args.apply)
            try:
                if language in DIRECTORIES:
                    rows, rejected = [], 0
                    for path in sorted((repo / DIRECTORIES[language]).rglob("*.json")):
                        try:
                            rows.append(record(json.loads(path.read_text()), language, revision, species))
                        except (ValueError, KeyError, TypeError):
                            rejected += 1
                    if not rows:
                        raise ValueError("No valid source cards; previous data retained")
                    import_rows(avoid_ambiguous_matches(rows), args.apply)
                    count = len(rows)
                else:
                    count, rejected = asia_records(language, args.cache, Fetcher(deadline, max(0.2, args.delay)), args.apply)
                state = "partial" if rejected else "imported"
                status(source, state, count, f"{rejected} unverified records skipped" if rejected else None, args.apply)
                failed = failed or bool(rejected)
            except (ValueError, OSError, subprocess.CalledProcessError) as error:
                status(source, "error", 0, str(error)[:500], args.apply)
                failed = True
        return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
