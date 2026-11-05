#!/usr/bin/env python3
"""Local evidence snapshot for the overnight Cardmarket/eBay runs."""
import json
import subprocess
from pathlib import Path
from datetime import datetime,timezone
state=Path.home()/".local/state/cardyssey-queue"
cardmarket=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector")
ebay=Path.home()/"cardyssey-ebay-collector"
def read(path):
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,ValueError):return {}
cm=read(cardmarket/"progress.json")
health=read(ebay/"monitor/status.json")
sets={}
for name in ("30th","30th-c","mep","sv01","sv02"):
    d=read(ebay/"admin-set-runs"/name/"progress.json")
    sets[name]={"status":d.get("status"),"done":len(d.get("results",[])),"total":d.get("total"),"counts":d.get("counts",{})}
sql="SELECT language_code,count(*) FILTER (WHERE resolution_status=\x27PRICE_FOUND\x27),count(*) FROM tcg_price_cache WHERE language_code IN (\x27de\x27,\x27en\x27) GROUP BY language_code ORDER BY language_code"
try:
    proc=subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-c",sql],capture_output=True,text=True,timeout=25)
    prices=proc.stdout.strip() if proc.returncode==0 else "DB_ERROR"
except Exception:prices="DB_UNAVAILABLE"
report={"at":datetime.now(timezone.utc).isoformat(),"cardmarket":{k:cm.get(k) for k in ("status","done","total","last_card","updated_at")},"ebay_health":health,"ebay_set_runs":sets,"price_cache_de_en":prices,"note":"Candidate IDs are not necessarily verified language/condition/print prices."}
# Distinguish raw sold-date markers from verified, card-matched prices.
from collections import Counter
pages=Counter(); dated_rows=0; sale_files=0
for sale_file in (ebay/"anniversary-20261021").glob("*/sales.json"):
    d=read(sale_file)
    if not d:continue
    sale_files+=1
    pages.update(str(x.get("status")) for x in d.get("pages",[]))
    dated_rows+=sum(bool(x.get("sold_date")) for x in d.get("rows",[]))
report["ebay_raw_evidence"]={"files":sale_files,"page_statuses":dict(pages),"dated_rows_not_all_validated":dated_rows}
report["language_coverage"]={"ebay_set_jobs":"DE only; dedicated EN eBay collector not yet implemented","cardmarket_edge":"DE offer filter; no EN offer scan","cardmarket_price_guide":"DE and EN scheduled independently"}
report["cardmarket_cdp_last_error"]=None
try:
    err=(cardmarket/"connection-errors.jsonl").read_text(encoding="utf-8-sig").splitlines()[-1]
    report["cardmarket_cdp_last_error"]=json.loads(err)
except (OSError,ValueError,IndexError):pass
state.mkdir(parents=True,exist_ok=True)
outfile=state/"market-night-20261106-report.json"
outfile.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"report":str(outfile),"cardmarket_status":report["cardmarket"]["status"],"ebay":{k:v["status"] for k,v in sets.items()}},ensure_ascii=False))
