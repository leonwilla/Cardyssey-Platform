#!/usr/bin/env python3
"""Read-only DE/EN unresolved-price triage from matched Cardmarket and TCGCSV evidence."""
import argparse,collections,json
from pathlib import Path

def classify(r,exact):
    evidence=exact.get((r["language"],r["card_id"],r["variant_id"]))
    if evidence:
        status=evidence["status"]
        if status=="EXACT_PRODUCT_HAS_NO_PUBLIC_MARKET_PRICE":
            return "EXACT_PRODUCT_NO_PUBLIC_PRICE"
        if status=="PRODUCT_NOT_IN_GROUP":
            return "EXTERNAL_ID_GROUP_CONFLICT"
        if status=="EXACT_PRODUCT_MARKET_PRICE_AVAILABLE":
            return "VERIFY_PRINT_AND_SUBTYPE"
    if r.get("set_verified") and r.get("products"):
        return "VERIFY_CARDMARKET_PRINT_IDENTITY"
    if r.get("exact_variant_provider_ids"):
        return "EXTERNAL_ID_NEEDS_VALIDATION"
    return "NO_EXACT_PROVIDER_ID"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cardmarket-report",type=Path,required=True)
    p.add_argument("--tcgcsv-report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    cm=json.loads(a.cardmarket_report.read_text())["unresolved"]
    tcg=json.loads(a.tcgcsv_report.read_text())["results"]
    exact={(r["language"],r["card_id"],r["variant_id"]):r for r in tcg}
    rows=[]
    for r in cm:
        if r["language"] not in ("de","en"):continue
        label=classify(r,exact)
        rows.append(dict(language=r["language"],card_id=r["card_id"],variant_id=r["variant_id"],
                         cardmarket_status=r.get("status"),next_action=label,
                         cardmarket_verified_set=bool(r.get("set_verified")),
                         tcgcsv_status=exact.get((r["language"],r["card_id"],r["variant_id"]),{}).get("status")))
    report={"total_cases":len(rows),
            "by_language":dict(collections.Counter(r["language"] for r in rows)),
            "by_action":dict(collections.Counter(r["next_action"] for r in rows)),
            "automatically_published":0,
            "note":"Review evidence only. No cross-language prices and no assumed print match.",
            "cases":rows}
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},ensure_ascii=False))
if __name__=="__main__":main()
