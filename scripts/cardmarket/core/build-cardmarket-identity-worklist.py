#!/usr/bin/env python3
"""Build safe DE/EN Cardmarket ID candidates and a compact print-review queue.

Read-only against all existing price tables. Candidate set identities are staged
separately and never treated as per-language NM prices or verified foil/stamps.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
from cardmarket_print_routes import load_evidence, official_products, read_queue
import argparse
import csv
import json
import re
import subprocess
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path("/home/tv/cardshop")
QUEUE=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
OUT=ROOT/"reports"
FIELDS=("language","card_id","variant_id","set_id","number","name","type","foil","subtype","stamps",
        "candidate_ids","matched_set_ids","expansion_id","classification","product_names","requires_confirmation",
        "guide_has_30day","guide_product_id","stamp_route","reference_candidate_urls",
        "reference_product_url","reference_product_id","exact_print_filter_supported")
def db_json(sql):
    p=subprocess.run(["docker","exec","cardyssey-db","psql","-X","-v","ON_ERROR_STOP=1",
                      "-U","cardyssey","-d","cardyssey","-At","-c",sql],capture_output=True,text=True,check=True)
    return [json.loads(line) for line in p.stdout.splitlines() if line.strip()]
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
    ap.add_argument('--output-dir',type=Path,default=OUT)
    args=ap.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
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
    queues={lang:read_queue(QUEUE/f'queue-{lang}.csv') for lang in ('de','en')}
    routing=load_evidence(QUEUE,queues,products)
    review=[]
    counts={}
    for lang in ("de","en"):
        counts[lang]=Counter()
        out=args.output_dir/f"cardmarket-identity-worklist-{lang}.csv"
        with out.open("w",encoding="utf-8",newline="") as w:
            writer=csv.DictWriter(w,fieldnames=FIELDS);writer.writeheader()
            for r in queues[lang]:
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
                special=bool(r["sonderdruck"].strip() or r["foil"].strip() or r["stempel"].strip() not in ("","[]","null"))
                # Inferred English set identities are only consensus suggestions.
                # They are not equivalent to the independently mapped DE set crosswalk.
                if lang=="en" and r["set_id"] in inferred:
                    state=state.replace("VERIFIED_SET","INFERRED_SET")
                route=routing[lang].get((r['cardyssey_karte'],r['variante_id']),{})
                if human_confirmed:state='HUMAN_CONFIRMED_EXACT_PRINT'
                elif route.get('reference_product_id'):
                    pid=route['reference_product_id']
                    matched=[pid];exp=str(products[pid]['idExpansion'])
                    state='VINTAGE_MAIN_SET_PAGE_PRINT_UNVERIFIED'
                elif route.get('reference_candidate_urls'):
                    state='STAMP_SUBSET_SET_NUMBER_CANDIDATES'
                elif route.get('stamp_route'):
                    state='STAMP_SUBSET_SEARCH_REQUIRED'
                elif special:state += "_SPECIAL_PRINT"
                counts[lang][state]+=1
                chosen=matched[0] if len(matched)==1 and not print_missing and not route else ""
                data=dict(language=lang,card_id=r["cardyssey_karte"],variant_id=r["variante_id"],
                          set_id=r["set_id"],number=r["kartennummer"],name=r["kartenname_suche"],
                          type=r["drucktyp"],foil=r["foil"],subtype=r["sonderdruck"],stamps=r["stempel"],
                          candidate_ids=",".join(sorted(set(ids+matched))),matched_set_ids=",".join(matched),
                          expansion_id=exp or "",classification=state,
                          product_names=" | ".join(products[i].get("name","") for i in matched[:5]),
                          requires_confirmation="SET_NUMBER_LANGUAGE_PRINT_FOIL_STAMP",
                          guide_has_30day="",guide_product_id=chosen)
                data.update({col:route.get(col,'') for col in FIELDS[-5:]})
                writer.writerow(data)
                if state not in ('ONE_PRODUCT_IN_VERIFIED_SET','HUMAN_CONFIRMED_EXACT_PRINT'):
                    review.append(data)
    # Prefer existing ownership and missing price when shown in admin; no automatic price publication.
    with (args.output_dir/"cardmarket-print-review-all.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(review)
    status={"feed_date":feed_date,"official_catalog_size":len(products),"de_set_candidate_crosswalks":len(sets),
            "inferred_unverified_en_set_mappings":len(inferred),"en_set_conflicts":len(flagged),
            "lang_counts":{k:dict(v) for k,v in counts.items()},
            "manual_review_rows":len(review),
            "catalog_set_ambiguities_held":sorted(quarantined),
            "safety":"CANDIDATES ONLY. No prices or routing rows have been written."}
    (args.output_dir/"cardmarket-identity-pipeline-status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(status,ensure_ascii=False))
if __name__=="__main__":main()
