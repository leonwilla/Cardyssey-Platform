#!/usr/bin/env python3
"""Build a safe, auditable Cardmarket German print-identity review queue.

Candidate IDs are suggestions, never automatic assignments. The product page
number, set, language, edition, finish and special stamps need independent proof.
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


def triage(item):
    products = item.get("products") or []
    same_set = bool(item.get("set_verified"))
    external = item.get("exact_variant_provider_ids") or {}
    direct = str(external.get("cardmarket") or "").strip()
    candidate_ids = {str(p.get("id")) for p in products}
    hinted = item.get("name_only_search_hints") or []
    variant = item.get("variant") or {}
    special = any((variant.get(k) for k in ("subtype", "foil", "stamps")))
    if direct and direct in candidate_ids and same_set:
        return "P1", "EXTERNAL_CARDMARKET_ID_IN_VERIFIED_SET", "Produktnummer und exakte Druckidentitaet auf Produktseite pruefen"
    if direct and direct not in candidate_ids:
        return "P1", "EXTERNAL_CARDMARKET_ID_CONFLICT", "Externe Varianten-ID gegen Set und Karte pruefen; keinen Kandidaten automatisch zuordnen"
    if same_set and len(products) == 1:
        return "P2" if not special else "P3", "SINGLE_SET_CANDIDATE", "Kartennummer, Sprache, Edition und Sonderdruck pruefen"
    if same_set and len(products) > 1:
        return "P3", "MULTIPLE_SET_CANDIDATES", "Kartennummer und Artwork/Attacken zur Unterscheidung pruefen"
    if external:
        return "P3", "EXTERNAL_VARIANT_REFERENCE_ONLY", "Externe Varianten-ID nach Set und Druck pruefen"
    if hinted:
        return "P4", "NAME_ONLY_SEARCH_HINTS", "Set zuerst belegen; Namensgleichheit ist kein Produktmatch"
    return "P5", "NO_PRODUCT_CANDIDATE", "Produktkatalog nach Set, Nummer und Namen manuell recherchieren"


def make_rows(items):
    rows = []
    for x in items:
        candidates = x.get("products") or []
        variant = x.get("variant") or {}
        external = x.get("exact_variant_provider_ids") or {}
        priority, action, instruction = triage(x)
        rows.append({
            "prioritaet": priority, "status": "ZU_PRUEFEN", "prueffall": action,
            "naechster_schritt": instruction, "set_id": x.get("set_code") or "",
            "kartennummer": x.get("number") or "",
            "kartenname_suche": x.get("english_name") or "",
            "cardyssey_karte": x.get("card_id") or "", "variante_id": x.get("variant_id") or "",
            "drucktyp": variant.get("type") or "", "sonderdruck": variant.get("subtype") or "",
            "foil": variant.get("foil") or "", "stempel": ",".join(variant.get("stamps") or []),
            "produktkandidaten": len(candidates),
            "cardmarket_ids": ",".join(str(c.get("id") or "") for c in candidates),
            "cardmarket_namen": " | ".join(str(c.get("name") or "") for c in candidates),
            "externe_cardmarket_id": str(external.get("cardmarket") or ""),
            "externe_tcgplayer_id": str(external.get("tcgplayer") or ""),
            "externe_cardtrader_id": str(external.get("cardtrader") or ""),
            "namenstreffer_nur_hinweis": int(x.get("name_only_match_count") or 0),
            "namenstreffer_ids": ",".join(str(c.get("id") or "") for c in (x.get("name_only_search_hints") or [])),
            "offen_zu_pruefen": ",".join(x.get("unverified_identity_fields") or []),
            "suche": x.get("search_query") or "",
            "filter_sprache": "Deutsch (language[3])",
            "filter_zustand": "mind. Near Mint (minCondition=2)",
            "filter_signiert": "Nein", "filter_veraendert": "Nein",
            "produktnummer_bestaetigt": "", "set_bestaetigt": "",
            "sprache_bestaetigt": "", "edition_bestaetigt": "",
            "foil_bestaetigt": "", "stempel_bestaetigt": "",
            "manuell_bestaetigte_id": "", "manuell_bestaetigte_edition": "",
            "manuell_bestaetigte_sprache": "", "notizen": "",
        })
    rows.sort(key=lambda r: (r["prioritaet"], r["set_id"], r["cardyssey_karte"], r["variante_id"]))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    items = json.loads(args.input.read_text(encoding="utf-8"))["unresolved"]
    rows = make_rows(items)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if rows:
        path = args.output_dir / "de_offene_cardmarket_varianten.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "total": len(rows),
        "with_product_candidates": sum(bool(r["produktkandidaten"]) for r in rows),
        "with_exact_variant_provider_ids": sum(bool(x.get("exact_variant_provider_ids")) for x in items),
        "with_direct_cardmarket_variant_id": sum(bool((x.get("exact_variant_provider_ids") or {}).get("cardmarket")) for x in items),
        "name_only_hint_without_set_candidate": sum(bool(x.get("name_only_search_hints")) and not x.get("products") for x in items),
        "priorities": dict(Counter(r["prioritaet"] for r in rows)),
        "review_actions": dict(Counter(r["prueffall"] for r in rows)),
        "safety": "No product ID or price is confirmed/published by this review queue.",
        "first_examples": [{k: r[k] for k in ("set_id", "cardyssey_karte", "prueffall", "cardmarket_ids")} for r in rows[:5]],
    }
    (args.output_dir / "status.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
