#!/usr/bin/env python3
"""Read-only Cardmarket candidate audit using verified expansion IDs.

Never interpret one product ID as confirmed print/foil/language identity.
Never writes price caches, routing, or candidate tables.
"""
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

URL="https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_6.json"
CACHE=Path("/home/tv/.local/state/cardyssey-queue/price-feeds")/(hashlib.sha256(URL.encode()).hexdigest()+".json")
BASE=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
REPORTS=Path("/home/tv/cardshop/reports")
REPORTS.mkdir(parents=True,exist_ok=True)

def get_set_crosswalk():
    q="""SELECT json_build_object('card_id',card_id,'language',language_code,
             'expansion',provider_expansion_id,'status',candidate_status)::text
         FROM cardmarket_catalog_link_candidates
         WHERE provider_expansion_id IS NOT NULL
           AND candidate_status IN ('SINGLE_SET_PRODUCT','MULTIPLE_SET_PRODUCTS')
           AND language_code IN ('de','en')"""
    r=subprocess.run(["docker","exec","cardyssey-db","psql","-X","-At",
       "-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey","-c",q],
       capture_output=True,text=True,check=True)
    return {(x["language"],x["card_id"]):str(x["expansion"])
            for line in r.stdout.splitlines() if line.strip()
            for x in [json.loads(line)]}

def review(products, crosswalk,lang):
    counts=Counter()
    path=REPORTS/f"cardmarket-candidates-checked-{lang}.csv"
    with (BASE/f"queue-{lang}.csv").open(encoding="utf-8-sig",newline="") as infile, path.open("w",encoding="utf-8",newline="") as outfile:
        reader=csv.DictReader(infile)
        fields=["language","card_id","variant_id","set_id","printed_number","card_name",
            "type","foil","stamps","candidate_count","matched_set_count",
            "all_product_ids","same_set_ids","rejected_other_set_ids",
            "classification","next_step"]
        writer=csv.DictWriter(outfile,fieldnames=fields)
        writer.writeheader()
        for row in reader:
            counts["total"]+=1
            card=row["cardyssey_karte"]
            ids=sorted({s for s in row["cardmarket_ids"].split(",") if s.isdigit()})
            expansion=crosswalk.get((lang,card))
            same=[pid for pid in ids if pid in products and str(products[pid].get("idExpansion"))==expansion] if expansion else []
            other=[pid for pid in ids if pid in products and str(products[pid].get("idExpansion"))!=expansion] if expansion else []
            if not ids:
                classification="NO_ID"
                step="LOOKUP_BY_SET_NAME_AND_PRINTED_NUMBER"
            elif expansion and len(same)==1:
                classification="ONE_MATCH_IN_VERIFIED_SET"
                step="VERIFY_PRINT_FOIL_STAMP_LANGUAGE"
                counts["one_matching_set"]+=1
                if len(ids)>1:counts["multi_resolved_by_set"]+=1
            elif expansion and len(same)>1:
                classification="MULTIPLE_MATCHES_WITHIN_SET"
                step="REVIEW_PRINT_OR_PRODUCT"
                counts["multi_same_set"]+=1
            elif expansion:
                classification="NO_MATCH_WITHIN_VERIFIED_SET"
                step="REVIEW_MISMATCH"
                counts["no_set_match"]+=1
            elif len(ids)==1 and ids[0] in products:
                classification="ONE_ID_SET_UNVERIFIED"
                step="VERIFY_SET_NUMBER_PRINT"
                counts["one_id_no_set_proof"]+=1
            else:
                classification="SET_UNVERIFIED_OR_MISSING_ID"
                step="FIND_SET_MATCH"
                counts["set_unverified"]+=1
            counts[classification]+=1
            writer.writerow({
                "language":lang,"card_id":card,"variant_id":row["variante_id"],
                "set_id":row["set_id"],"printed_number":row["kartennummer"],
                "card_name":row["kartenname_suche"],"type":row["drucktyp"],
                "foil":row["foil"],"stamps":row["stempel"],
                "candidate_count":len(ids),"matched_set_count":len(same),
                "all_product_ids":",".join(ids),"same_set_ids":",".join(same),
                "rejected_other_set_ids":",".join(other),
                "classification":classification,"next_step":step})
    return dict(counts),str(path)

def main():
    products={str(p["idProduct"]):p for p in json.loads(CACHE.read_text())["products"]}
    crosswalk=get_set_crosswalk()
    out={"official_products":len(products),"verified_set_crosswalk_cards":len(crosswalk),"langs":{}}
    for lang in ("de","en"):
        stats,path=review(products,crosswalk,lang)
        out["langs"][lang]={"counts":stats,"report":path}
    (REPORTS/"cardmarket-set-crosscheck-summary.json").write_text(
       json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False))
if __name__=="__main__":
    main()
