#!/usr/bin/env python3
"""Install the maintenance worker in the current user's existing cron, preserving other entries."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root=Path(os.environ.get("CARDYSSEY_ROOT_DIR",str(Path(__file__).resolve().parent.parent))).resolve()
runtime=Path.home()/".local/lib/cardyssey-maintenance"
state=Path.home()/".local/state/cardyssey-queue"
runtime.mkdir(parents=True,exist_ok=True)
state.mkdir(parents=True,exist_ok=True,mode=0o700)
shutil.copy2(Path(__file__).with_name("maintenance-queue.py"),runtime/"maintenance-queue.py")
subprocess.run([sys.executable,"-m","venv",str(runtime/"venv")],check=True)
subprocess.run([str(runtime/"venv/bin/pip"),"install","-r",str(root/"scripts/japanese-image-price-requirements.txt")],check=True)
jobs=[
 dict(id="health",argv=["python3",str(root/"scripts/maintenance-health.py")],timeout=180,interval=3600,priority=10),
 dict(id="backup",argv=["bash",str(root/"scripts/backup-production.sh")],timeout=1800,interval=86400,priority=20),
 dict(id="regressions",argv=[str(runtime/"venv/bin/python"),str(root/"scripts/maintenance-regressions.py")],timeout=2400,interval=86400,priority=30),
 dict(id="coverage",argv=["python3",str(root/"scripts/audit-price-coverage.py")],timeout=90,interval=21600,priority=40),
 dict(id="ko-variant-audit",argv=["python3",str(root/"scripts/audit-ko-remaining-variants.py")],timeout=240,interval=86400,priority=45),
 dict(id="catalog-conflicts",argv=["python3",str(root/"scripts/audit-catalog-identity-conflicts.py"),"--report",str(state/"catalog-conflicts.json")],timeout=90,interval=86400,priority=50),
]
for job in jobs:
    job["cwd"]=str(root)
    job["max_attempts"]=3
config=state/"jobs.json"
config.write_text(json.dumps(jobs,indent=2)+"\n")
subprocess.run([sys.executable,str(runtime/"maintenance-queue.py"),"configure",str(config)],check=True,stdout=subprocess.DEVNULL)
previous=subprocess.run(["crontab","-l"],text=True,capture_output=True)
if previous.returncode not in (0,1):
    raise SystemExit(previous.stderr)
marker="# cardyssey-maintenance-queue"
lines=[line for line in previous.stdout.splitlines() if marker not in line]
entry=f"* * * * * /usr/bin/python3 {runtime}/maintenance-queue.py tick >> {state}/cron.log 2>&1 {marker}"
lines.append(entry)
(state/"crontab-before-install.txt").write_text(previous.stdout)
subprocess.run(["crontab","-"],input="\n".join(lines)+"\n",text=True,check=True)
print("Installed persistent cron worker; state: "+str(state))
print("Jobs: "+", ".join(job["id"] for job in jobs))
