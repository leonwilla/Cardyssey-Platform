#!/usr/bin/env python3
"""Build safe DE/EN Cardmarket ID candidates and a compact print-review queue.

Read-only against all existing price tables. Candidate set identities are staged
separately and never treated as per-language NM prices or verified foil/stamps.
"""
from cardmarket_game_profile import load_game_profile
import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path("/home/tv/cardshop")
QUEUE=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
FEEDS=Path("/home/tv/.local/state/cardyssey-queue/price-feeds")
CAT_URL=load_game_profile()['product_url']
OUT=ROOT/"reports"
FIELDS=("language","card_id","variant_id","set_id","number","name","type","foil","subtype","stamps",
        "candidate_ids","matched_set_ids","expansion_id","classification","product_names","requires_confirmation",
        "guide_has_30day","guide_product_id")
def db_json(sql):
    p=subprocess.run(["docker","exec","cardyssey-db","psql","-X","-v","ON_ERROR_STOP=1",
                      "-U","cardyssey","-d","cardyssey","-At","-c",sql],capture_output=True,text=True,check=True)
    return [json.loads(line) for line in p.stdout.splitlines() if line.strip()]
def official_products():
    p=FEEDS/(hashlib.sha256(CAT_URL.encode()).hexdigest()+".json")
    raw=json.loads(p.read_text())
    return {str(x["idProduct"]):x for x in raw["products"]},raw.get("createdAt")
def set_mapping():
    rows=db_json("""SELECT json_build_object('set',set_id,'exp',provider_expansion_id)::text
       FROM cardmarket_catalog_link_candidates
       WHERE language_code='de' AND provider_expansion_id IS NOT NULL
         AND candidate_status IN ('SINGLE_SET_PRODUCT','MULTIPLE_SET_PRODUCTS')""")
    counts=defaultdict(Counter)
    for x in rows:counts[x["set"]][str(x["exp"])]+=1
    return {sid:next(iter(c)) for sid,c in counts.items() if len(c)==1 and sum(c.values())>=3}
def infer_english_sets(products,known):
    votes=defaultdict(lambda:defaultdict(set))
    with (QUEUE/"queue-en.csv").open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            ids={i for i in r["cardmarket_ids"].split(",") if i.isdigit()}
            if len(ids)!=1 or r["set_id"] in known:continue
            p=products.get(next(iter(ids)))
            if p:votes[r["set_id"]][str(p.get("idExpansion"))].add(r["cardyssey_karte"])
    inferred={}
    flagged={}
    for sid,exp in votes.items():
        scores=sorted(((len(cards),eid) for eid,cards in exp.items()),reverse=True)
        total=sum(n for n,_ in scores)
        if scores[0][0]>=6 and scores[0][0]/max(1,total)>=0.98 and (len(scores)==1 or scores[0][0]-scores[1][0]>=6):
            inferred[sid]=scores[0][1]
        else:flagged[sid]=dict((k,len(v)) for k,v in exp.items())
    return inferred,flagged

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--review-limit",type=int,default=2000)
    args=ap.parse_args()
    products,feed_date=official_products()
    sets=set_mapping()
    inferred,flagged=infer_english_sets(products,sets)
    all_sets={**sets,**inferred}
    # A strong duplicate expansion-name list is NOT independent set evidence.
    # Do not promote catalog-only singleton IDs from those sets until their
    # specific Cardmarket expansion is verified separately. Preserve human
    # exact-print routes in the loop below.
    audit_file=ROOT/'reports/cardmarket-set-mapping-risk-audit.json'
    quarantined=set()
    if audit_file.exists():
        audit=json.loads(audit_file.read_text(encoding='utf-8'))
        if audit.get('setsChecked',0)>=100:
            quarantined={r['setId'] for r in audit['cases']
                if r['status']=='AMBIGUOUS_OVERLAPPING_EXPANSIONS'
                and not (r.get('independentlyConfirmedOverride') or r.get('variantIdConsensusMatch'))}
            for sid in quarantined:all_sets.pop(sid,None)
    review=[]
    counts={}
    for lang in ("de","en"):
        counts[lang]=Counter()
        out=OUT/f"cardmarket-identity-worklist-{lang}.csv"
        with (QUEUE/f"queue-{lang}.csv").open(encoding="utf-8-sig",newline="") as f,out.open("w",encoding="utf-8",newline="") as w:
            reader=csv.DictReader(f)
            writer=csv.DictWriter(w,fieldnames=FIELDS);writer.writeheader()
            for r in reader:
                counts[lang]["total"]+=1
                ids=sorted({i for i in r["cardmarket_ids"].split(",") if i.isdigit()})
                exp=all_sets.get(r["set_id"])
                matched=[i for i in ids if i in products and exp is not None and str(products[i]["idExpansion"])==exp]
                # When a special print has NO exact Cardmarket product ID,
                # preserve card-level candidates from the independently
                # mapped expansion as UNVERIFIED PRINT candidates. This is
                # NEVER a confirmed physical print or a publishable price.
                print_missing=not matched and not ids
                card_candidates=sorted({i for i in r.get('set_card_candidate_ids','').split(',')
                    if i in products and exp is not None and str(products[i]['idExpansion'])==exp})
                if print_missing and card_candidates:
                    matched=card_candidates
                human_confirmed=(r.get('routing_state')=='VERIFIED_PRODUCT_ID' and
                    bool(r.get('known_url')) and len(ids)==1 and ids[0] in products)
                if human_confirmed:
                    # One user-confirmed exact print is evidence for THIS print,
                    # not for the whole expansion. Preserve it despite a faulty
                    # old set crosswalk and do not repeatedly ask for the same ID.
                    matched=[ids[0]]
                    exp=str(products[ids[0]].get('idExpansion') or exp or '')
                if exp is None:state="SET_NOT_VERIFIED"
                elif print_missing and matched:state="CARD_IN_VERIFIED_SET_PRINT_NOT_IDENTIFIED"
                elif not ids:state="NO_PRODUCT_ID"
                elif not matched:state="NO_MATCH_IN_VERIFIED_SET"
                elif len(matched)>1:state="MULTIPLE_PRODUCTS_IN_VERIFIED_SET"
                else:state="ONE_PRODUCT_IN_VERIFIED_SET"
                typ=(r["drucktyp"] or "").casefold()
                finish="REVERSE" if "reverse" in typ else ("HOLO" if "holo" in typ else "NORMAL")
                special=bool(r["sonderdruck"].strip() or r["foil"].strip() or r["stempel"].strip() not in ("","[]","null"))
                # Inferred English set identities are only consensus suggestions.
                # They are not equivalent to the independently mapped DE set crosswalk.
                if lang=="en" and r["set_id"] in inferred:
                    state=state.replace("VERIFIED_SET","INFERRED_SET")
                if human_confirmed:state='HUMAN_CONFIRMED_EXACT_PRINT'
                elif special:state += "_SPECIAL_PRINT"
                counts[lang][state]+=1
                chosen=matched[0] if len(matched)==1 and not print_missing else ""
                data=dict(language=lang,card_id=r["cardyssey_karte"],variant_id=r["variante_id"],
                          set_id=r["set_id"],number=r["kartennummer"],name=r["kartenname_suche"],
                          type=r["drucktyp"],foil=r["foil"],subtype=r["sonderdruck"],stamps=r["stempel"],
                          candidate_ids=",".join(sorted(set(ids+matched))),matched_set_ids=",".join(matched),
                          expansion_id=exp or "",classification=state,
                          product_names=" | ".join(products[i].get("name","") for i in matched[:5]),
                          requires_confirmation="SET_NUMBER_LANGUAGE_PRINT_FOIL_STAMP",
                          guide_has_30day="",guide_product_id=chosen)
                writer.writerow(data)
                if state not in ('ONE_PRODUCT_IN_VERIFIED_SET','HUMAN_CONFIRMED_EXACT_PRINT'):
                    review.append(data)
    # Prefer existing ownership and missing price when shown in admin; no automatic price publication.
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"cardmarket-print-review-all.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(review)
    status={"feed_date":feed_date,"official_catalog_size":len(products),"de_set_candidate_crosswalks":len(sets),
            "inferred_unverified_en_set_mappings":len(inferred),"en_set_conflicts":len(flagged),
            "lang_counts":{k:dict(v) for k,v in counts.items()},
            "manual_review_rows":len(review),
            "catalog_set_ambiguities_held":sorted(quarantined),
            "safety":"CANDIDATES ONLY. No prices or routing rows have been written."}
    (OUT/"cardmarket-identity-pipeline-status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(status,ensure_ascii=False))
if __name__=="__main__":main()
