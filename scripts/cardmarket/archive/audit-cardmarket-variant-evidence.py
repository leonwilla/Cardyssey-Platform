#!/usr/bin/env python3
"""Offline inspection of all German unresolved Cardmarket variant candidates.

Consumes previously generated evidence, never browser credentials or a live account;
never treats a product-name match as full print identity.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def classify(case):
    products = case.get("products") or []
    candidates = {str(p.get("id")) for p in products}
    external = str((case.get("exact_variant_provider_ids") or {}).get("cardmarket") or "")
    verified_set = bool(case.get("set_verified"))
    if external and external in candidates and verified_set:
        return "DIRECT_ID_SET_MATCH_REVIEW"
    if external:
        return "DIRECT_ID_CONFLICT_REVIEW"
    if verified_set and len(candidates) == 1:
        return "SINGLE_SET_CANDIDATE_REVIEW"
    if verified_set and candidates:
        return "MULTIPLE_SET_CANDIDATES_REVIEW"
    if case.get("name_only_search_hints"):
        return "NAME_ONLY_HINT_NOT_VERIFIED"
    return "NO_PRODUCT_CANDIDATE"


def audit(cases):
    rows = []
    keys = set()
    for case in cases:
        key = (case.get("language"), case.get("card_id"), case.get("variant_id"))
        if key in keys:
            raise ValueError(f"duplicate key: {key}")
        keys.add(key)
        variant = case.get("variant") or {}
        refs = case.get("exact_variant_provider_ids") or {}
        rows.append({
            "language": case.get("language", ""), "card_id": case.get("card_id", ""),
            "variant_id": case.get("variant_id", ""), "set_id": case.get("set_code", ""),
            "number": case.get("number", ""), "variant_type": variant.get("type", ""),
            "subtype": variant.get("subtype", ""), "foil": variant.get("foil", ""),
            "stamps": ",".join(variant.get("stamps") or []),
            "status": classify(case),
            "direct_cardmarket_id": str(refs.get("cardmarket") or ""),
            "in_set_candidate_ids": ",".join(str(p.get("id")) for p in (case.get("products") or [])),
            "name_only_hint_count": len(case.get("name_only_search_hints") or []),
            "remaining_proof": ",".join(case.get("unverified_identity_fields") or []),
            "verified_identity": False,
            "price_auto_published": False,
        })
    summary = {"rows_inspected": len(rows), "unique_variant_keys": len(keys),
               "by_status": dict(Counter(row["status"] for row in rows)),
               "fully_verified_prints": 0, "published_prices": 0,
               "source": "existing official catalogue and variant cross-references; offline review"}
    return rows, summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    rows, summary = audit(json.loads(a.input.read_text(encoding="utf-8"))["unresolved"])
    a.output_dir.mkdir(parents=True, exist_ok=True)
    with (a.output_dir / "de_full_identity_audit.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    (a.output_dir / "de_full_identity_audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
