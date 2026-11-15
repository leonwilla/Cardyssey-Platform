#!/usr/bin/env python3
"""Conservative offline product-page lead resolver for Cardmarket ambiguous hits.

Only references a V1 page in the verified set; it never verifies print identity
or publishes prices. Shadowless, stamps, and uncommon foils are never promoted
to ordinary filter support. CSV rewrites are atomic and require an idle scanner.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))


def page_candidate(url: str, guard: str | None, language: str, number: str) -> bool:
    if not guard or not url:
        return False
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "www.cardmarket.com":
        return False
    path = parsed.path.split("/")
    if len(path) != 7 or path[1:6] != [language, "Pokemon", "Products", "Singles", guard]:
        return False
    if not re.search(r"(?i)(?:^|-)V1(?:-|$)", path[6]):
        return False
    if re.search(r"(?i)(?:^|-)V(?:[2-9]|[1-9][0-9])(?:-|$)|additionals", path[6]):
        return False
    m = re.search(r"(?i)-[A-Z]{1,8}([0-9]{1,4})$", path[6])
    return bool(m and str(int(m[1])) == str(int(number)))


def resolve(observations: list[dict], guards: dict, language: str = "de") -> list[dict]:
    latest = {}
    for row in observations:
        key = row.get("key") or (
            f"{row.get('card_id','')}|{row.get('variant_id','')}"
        )
        if key and "|" in key:
            latest[key] = row
    result = []
    for key, row in latest.items():
        if row.get("status") != "MULTIPLE_SEARCH_HITS":
            continue
        guard = guards.get(str(row.get("set_id") or ""))
        urls = row.get("score_top_candidate_urls") or []
        if not isinstance(urls, list):
            continue
        valid = sorted({
            u.split("?")[0]
            for u in urls
            if isinstance(u, str)
            and guard
            and urlsplit(u).scheme == "https"
            and urlsplit(u).netloc == "www.cardmarket.com"
            and urlsplit(u).path.startswith(f"/{language}/Pokemon/Products/Singles/{guard}/")
            and re.search(r"(?i)(?:^|-)V1(?:-|$)", urlsplit(u).path.split("/")[-1])
        })
        result.append({
            "key": key,
            "status": "OFFLINE_UNIQUE_V1_PAGE_CANDIDATE" if len(valid) == 1
                      else "MULTIPLE_SEARCH_HITS_REVIEW",
            "reference_product_url_candidate": valid[0] if len(valid) == 1 else None,
            "reference_standard_filter_supported": "UNVERIFIED",
            "comparison_urls": urls[:8],
            "price_verified": False,
        })
    return result


def safe_standard_filter(row: dict) -> bool:
    # Holo & reverse in this specific set have a standard Reverse Holo
    # provider control; unsupported special finishes must not pass this gate.
    return (
        row.get("drucktyp", "").casefold() in ("holo", "reverse", "normal", "nonholo", "common")
        and not str(row.get("sonderdruck") or "").strip()
        and not str(row.get("foil") or "").strip()
        and str(row.get("stempel") or "[]") in ("", "[]", "null")
    )


def build_updates(rows: list[dict], candidates: list[dict],
                  guards: dict, language: str, now: str) -> tuple[list[dict], dict]:
    by_key = {r["key"]: r for r in candidates
              if r.get("status") in ("OFFLINE_UNIQUE_V1_PAGE_CANDIDATE",
                                      "OFFLINE_UNIQUE_PLAIN_CANDIDATE_REVIEW")
              and r.get("reference_product_url_candidate")}
    counters = Counter()
    output = []
    for original in rows:
        row = original.copy()
        key = row["cardyssey_karte"] + "|" + row["variante_id"]
        candidate = by_key.get(key)
        if candidate is None:
            output.append(row)
            continue
        url = candidate["reference_product_url_candidate"]
        guard = guards.get(str(row.get("set_id")))
        if not page_candidate(url, guard, language, str(row.get("kartennummer") or "0")):
            counters["rejected_identity_or_set"] += 1
            output.append(row)
            continue
        if row.get('stamp_route') or row.get('reference_evidence') == 'VINTAGE_MAIN_SET_PAGE_PRINT_UNVERIFIED':
            continue
        current = str(row.get("reference_product_url") or "").split("?")[0]
        if (current and current != url) or str(row.get("reference_print_verified") or "") == "YES":
            counters["rejected_existing_reference"] += 1
            output.append(row)
            continue
        if str(row.get("routing_state")) == "VERIFIED_PRODUCT_ID" and row.get("known_url"):
            counters["rejected_verified_mapping"] += 1
            output.append(row)
            continue
        supported = safe_standard_filter(row)
        row["reference_product_url"] = url
        row["reference_print_verified"] = "NO"
        row["reference_evidence"] = "OFFLINE_VERIFIED_SET_UNIQUE_V1_PAGE_PRINT_UNVERIFIED"
        row["reference_standard_filter_supported"] = "YES" if supported else "NO"
        # A new manual request is required even when the previous ambiguous
        # observation is recent. All old evidence remains in the JSONL log.
        if current != url:
            row["manual_scan_requested_at"] = now
            counters["new_hints"] += 1
        else:
            counters["existing_hints"] += 1
        counters["filter_supported" if supported else "special_print_unfilterable"] += 1
        output.append(row)
    return output, dict(counters)


def write_atomic_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    fd, temporary = tempfile.mkstemp(prefix="cm-resolver-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(buffer.getvalue().encode("utf-8-sig"))
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    base = args.base
    guards = json.loads((base / "verified-set-url-guards.json").read_text(encoding="utf-8-sig"))
    pending = {}
    now = datetime.now(timezone.utc).isoformat()
    for lang in ("de", "en"):
        source = base / f"browser-observations-{lang}.jsonl"
        observations = []
        for line in source.open(encoding="utf-8-sig"):
            try:
                observations.append(json.loads(line))
            except ValueError:
                continue
        candidates = resolve(observations, guards, lang)
        output_path = base / f"multiple-search-hits-offline-review-{lang}.json"
        queue_path = base / f"queue-{lang}.csv"
        with queue_path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            fields = reader.fieldnames
            rows = list(reader)
        updated, counts = build_updates(rows, candidates, guards, lang, now)
        pending[lang] = (updated, fields, queue_path, output_path, candidates, counts)
    if args.apply:
        # Detect an executing Windows scanner before touching either queue.
        import importlib.util
        loader = importlib.util.spec_from_file_location('cm_windows_deployer',
            Path(__file__).parent / 'deploy-windows-modules.py')
        checker = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(checker)
        checker.scanner_idle()
        from cardmarket_delta_scan import lock_queue_active
        lock_queue_active(base, datetime.now(timezone.utc))
    report = {}
    for lang, (updated, fields, queue, output_path, candidates, counts) in pending.items():
        if args.apply:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backups = base / "queue-backups"
            backups.mkdir(exist_ok=True)
            shutil.copy2(queue, backups / f"{queue.stem}-before-resolver-{timestamp}.csv")
            write_atomic_csv(queue, updated, fields)
            output_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
        report[lang] = {
            "candidates": sum(bool(x["reference_product_url_candidate"]) for x in candidates),
            **counts,
        }
    print(json.dumps({"mode": "APPLIED" if args.apply else "DRY_RUN", "languages": report},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
