#!/usr/bin/env python3
"""Sync unresolved official Cardmarket product candidates to admin review safely.

Selected decisions and notes are preserved. Never writes tcg_price_cache.
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
import subprocess
from pathlib import Path
ROOT=Path("/home/tv/cardshop")
REPORT=ROOT/"reports/cardmarket-print-review-all.csv"
def sql_quote(text):
    return str(text).replace("'","''")
def ingest(path,apply=False):
    stats={"rows":0,"with_set_ids":0,"no_set_ids":0}
    chunks=[]
    batch=[]
    with path.open(encoding="utf-8",newline="") as f:
        for x in csv.DictReader(f):
            ids=[y for y in x["candidate_ids"].split(",") if y.isdigit()]
            matched=[y for y in x["matched_set_ids"].split(",") if y in ids]
            item=dict(language=x["language"],card_id=x["card_id"],variant_id=x["variant_id"],
              set_id=x["set_id"],name=x["name"],number=x["number"],type=x["type"],
              foil=x["foil"],subtype=x["subtype"],stamps=x["stamps"],
              candidate_ids=ids,matched_set_ids=matched,expansion=x["expansion_id"],
              classification=x["classification"],product_names=x["product_names"])
            batch.append(item)
            stats["rows"]+=1
            stats["with_set_ids" if matched else "no_set_ids"]+=1
            if len(batch)>=500:
                chunks.append(batch);batch=[]
    if batch:chunks.append(batch)
    if not apply:return stats
    sql=["BEGIN;"]
    for group in chunks:
        payload=sql_quote(json.dumps(group,ensure_ascii=False,separators=(",",":")))
        sql.append("""WITH incoming AS (
 SELECT x->>'language' AS language_code,x->>'card_id' AS card_id,
   x->>'variant_id' AS variant_id,x->>'set_id' AS set_id,
   x->>'name' AS card_name,x->>'number' AS printed_number,
   x->>'type' AS print_type,x->>'foil' AS foil,x->>'subtype' AS subtype,
   x->>'stamps' AS stamps,x->'candidate_ids' AS candidate_ids,
   x->'matched_set_ids' AS matched_set_ids,x->>'expansion' AS provider_expansion_id,
   x->>'classification' AS classification,x->>'product_names' AS product_names
 FROM jsonb_array_elements('"""+payload+"""'::jsonb) x)
INSERT INTO cardmarket_print_identity_review
(language_code,card_id,variant_id,set_id,card_name,printed_number,print_type,
 foil,subtype,stamps,candidate_ids,matched_set_ids,provider_expansion_id,
 classification,product_names)
SELECT language_code,card_id,variant_id,set_id,card_name,printed_number,print_type,
 foil,subtype,stamps,candidate_ids,matched_set_ids,provider_expansion_id,
 classification,product_names FROM incoming
ON CONFLICT(language_code,card_id,variant_id) DO UPDATE SET
 set_id=EXCLUDED.set_id,card_name=EXCLUDED.card_name,
 printed_number=EXCLUDED.printed_number,print_type=EXCLUDED.print_type,
 foil=EXCLUDED.foil,subtype=EXCLUDED.subtype,stamps=EXCLUDED.stamps,
 candidate_ids=EXCLUDED.candidate_ids,matched_set_ids=EXCLUDED.matched_set_ids,
 provider_expansion_id=EXCLUDED.provider_expansion_id,
 classification=EXCLUDED.classification,product_names=EXCLUDED.product_names,
 checked_at=NOW()
WHERE cardmarket_print_identity_review.status='PENDING_REVIEW';
""")
    sql.append("COMMIT;")
    p=subprocess.run(["docker","exec","-i","cardyssey-db","psql","-X","-q",
       "-v","ON_ERROR_STOP=1","-U","cardyssey","-d","cardyssey"],input="\n".join(sql),
       capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError("DB import failed: "+p.stderr[-1200:])
    return stats
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    p.add_argument("--input",type=Path,default=REPORT)
    a=p.parse_args()
    print(json.dumps({**ingest(a.input,a.apply),"applied":a.apply},ensure_ascii=False))
