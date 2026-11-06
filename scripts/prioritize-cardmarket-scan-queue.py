#!/usr/bin/env python3
"""Put actually unpriced German variants first, then valuable/special print cases.

The queue is rebuilt without changing the stable variant IDs or old observations.
"""
import argparse
import csv
import json
import subprocess
from pathlib import Path

def db_rows():
    sql = """SELECT json_agg(json_build_object(
        'card_id',p.card_id,'variant_id',p.variant_id,
        'status',p.resolution_status,'price',p.base_eur,'source',p.source,
        'rarity',c.rarity))
    FROM tcg_price_cache p LEFT JOIN catalog_cards_mirror c
    ON c.card_id=p.card_id AND c.language_code=p.language_code
    WHERE p.language_code='de'"""
    result = subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey",
         "-At","-c",sql], capture_output=True,text=True,check=True)
    return json.loads(result.stdout.strip() or "[]") or []

def prioritize(rows, cache):
    lookup = {(r["card_id"],r["variant_id"]): r for r in cache}
    expensive = 0
    for row in rows:
        state = lookup.get((row["cardyssey_karte"],row["variante_id"]),{})
        value = float(state.get("price") or 0)
        missing = state.get("status") != "PRICE_FOUND" or value <= 0
        stamp = str(row.get("stempel") or "").strip()
        # JSON [] is an empty stamp list, not a special printing.
        special = bool(row.get("sonderdruck") or row.get("foil") or (stamp not in ("", "[]", "null")))
        rare = str(state.get("rarity") or "").casefold() in {
            "selten","rare","ultra rare","secret rare","illustration rare",
            "special illustration rare","hyper rare","promo"}
        expensive_row = value >= 20
        bulk = str(state.get("rarity") or "").casefold() in {
            "häufig","ungewöhnlich","common","uncommon"}
        if missing: tier=0
        elif expensive_row: tier=1
        elif special or rare: tier=2
        elif bulk: tier=4  # price feeds, not browser
        else: tier=3
        row["scan_tier"] = tier
        row["existing_price_eur"] = f"{value:.4f}" if not missing else ""
        row["existing_source"] = str(state.get("source") or "")
        row["needs_price"] = "YES" if missing else "NO"
        expensive += int(expensive_row)
    rows.sort(key=lambda r:(r["scan_tier"],r.get("prioritaet",""),
                            r.get("set_id",""),r["cardyssey_karte"],r["variante_id"]))
    return rows

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--queue",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    with args.queue.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    prioritized=prioritize(rows,db_rows())
    if len(prioritized)!=len(rows):raise ValueError("lost queue rows")
    unique={(r["cardyssey_karte"],r["variante_id"]) for r in prioritized}
    if len(unique)!=len(rows):raise ValueError("duplicate variant key")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=prioritized[0].keys())
        writer.writeheader();writer.writerows(prioritized)
    print(json.dumps({"rows":len(prioritized),
                      "missing_first":sum(x["needs_price"]=="YES" for x in prioritized),
                      "first_cards":[x["cardyssey_karte"] for x in prioritized[:27]]},
                     ensure_ascii=False))
if __name__=="__main__":main()
