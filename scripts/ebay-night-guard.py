#!/usr/bin/env python3
"""Night safety gate: only resume eBay when its existing monitor confirms healthy sold pages."""
import json
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path("/home/tv/cardyssey-ebay-collector")
status_file=ROOT/"monitor/status.json"
progress=ROOT/"anniversary-20261021/progress.json"
try:
    health=json.loads(status_file.read_text())
    stamp=datetime.fromisoformat(health["checked_at"].replace("Z","+00:00"))
except (OSError,ValueError,KeyError) as exc:
    print("SKIPPED_HEALTH_UNKNOWN",type(exc).__name__,flush=True)
    raise SystemExit(0)
age=(datetime.now(timezone.utc)-stamp).total_seconds()
if health.get("status")!="OK" or not 0<=age<2*3600:
    print("SKIPPED_PROVIDER_UNHEALTHY",health.get("status"),"age_seconds",int(age),flush=True)
    raise SystemExit(0)
try:
    previous=json.loads(progress.read_text())
    if previous.get("status")=="COMPLETE":
        print("SKIPPED_BATCH_COMPLETE_RETAIN_7_DAY_CURSOR",flush=True)
        raise SystemExit(0)
except (OSError,ValueError):
    pass
print("START_EBAY_INCREMENTAL_RESUME",flush=True)
result=subprocess.run(["python3","-u",str(ROOT/"anniversary_batch.py"),
                       "--out",str(ROOT/"anniversary-20261021"),"--incremental"],
                      cwd=ROOT,timeout=14400)
print("EBAY_BATCH_EXIT",result.returncode,flush=True)
raise SystemExit(result.returncode)
