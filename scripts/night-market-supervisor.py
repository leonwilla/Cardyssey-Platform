#!/usr/bin/env python3
"""Conservative overnight supervisor; no bypass of access denials."""
import json
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path("/home/tv/cardshop")
EBAY=Path("/home/tv/cardyssey-ebay-collector")
MONITOR=EBAY/"monitor/status.json"
def main():
    now=datetime.now(timezone.utc)
    try:
        status=json.loads(MONITOR.read_text())
        checked=datetime.fromisoformat(status["checked_at"].replace("Z","+00:00"))
    except (OSError,ValueError,KeyError):
        print("EBAY_HEALTH_UNAVAILABLE",flush=True)
        return 0
    if status.get("status")!="OK" or not 0<=(now-checked).total_seconds()<7200:
        print("EBAY_PROVIDER_UNHEALTHY",status.get("status"),flush=True)
        return 0
    result=subprocess.run([sys.executable,str(ROOT/"scripts/ebay-collector/weekly_scan.py")],
                          cwd=ROOT,timeout=120,capture_output=True,text=True)
    print("EBAY_WEEKLY",result.returncode,result.stdout.strip(),result.stderr.strip()[:300],flush=True)
    return result.returncode
if __name__=="__main__":
    raise SystemExit(main())
