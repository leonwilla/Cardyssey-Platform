#!/usr/bin/env python3
"""Verify external variant IDs against the official Cardmarket product catalogue.

Never promote equal idMetacard to equal physical printing: two expansions can
contain the same underlying meta-card. Writes a full read-only review report.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def crosscheck(cases, products):
    catalog = {str(p.get("idProduct")): p for p in products}
    results = []
    for row in cases:
        candidates = [catalog.get(str(p.get("id"))) for p in row.get("products") or []]
        candidates = [p for p in candidates if p]
        direct_id = str((row.get("exact_variant_provider_ids") or {}).get("cardmarket") or "")
        direct = catalog.get(direct_id) if direct_id else None
        same_ids = [p for p in candidates if str(p.get("idProduct")) == direct_id]
        related_metacards = [p for p in candidates if direct and p.get("idMetacard") is not None and p.get("idMetacard") == direct.get("idMetacard")]
        if not direct_id:
            status = "NO_DIRECT_VARIANT_ID"
        elif direct is None:
            status = "DIRECT_ID_NOT_IN_CURRENT_CATALOG"
        elif same_ids:
            status = "DIRECT_ID_IN_SET_REVIEW_PRINT"
        elif related_metacards:
            status = "SAME_METACARD_DIFFERENT_PRODUCT_OR_EXPANSION"
        else:
            status = "DIRECT_ID_UNRELATED_TO_SET_CANDIDATES"
        results.append({
            "language": row.get("language", ""), "card_id": row.get("card_id", ""),
            "variant_id": row.get("variant_id", ""), "set": row.get("set_code", ""),
            "direct_product_id": direct_id, "direct_expansion": direct.get("idExpansion") if direct else "",
            "direct_metacard": direct.get("idMetacard") if direct else "",
            "candidate_products": ",".join(str(p.get("idProduct")) for p in candidates),
            "candidate_expansions": ",".join(str(p.get("idExpansion")) for p in candidates),
            "same_metacard_products": ",".join(str(p.get("idProduct")) for p in related_metacards),
            "crossref_status": status, "safe_to_assign_product_id": False,
        })
    summary = {"inspected": len(results), "by_status": dict(Counter(r["crossref_status"] for r in results)),
               "automatically_assigned": 0, "note": "idMetacard proves a catalogue family, not expansion, printed number, language or foil"}
    return results, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        from price_feed_client import fetch_json
    except ImportError:
        from scripts.price_feed_client import fetch_json
    url = "https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json"
    products = fetch_json(url, headers={"User-Agent": "Cardyssey/0.4 catalog-crossref"}).get("products") or []
    cases = json.loads(args.input.read_text(encoding="utf-8"))["unresolved"]
    results, summary = crosscheck(cases, products)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "de_cardmarket_catalog_crossrefs.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0])); w.writeheader(); w.writerows(results)
    (args.output_dir / "de_cardmarket_catalog_crossrefs.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()
