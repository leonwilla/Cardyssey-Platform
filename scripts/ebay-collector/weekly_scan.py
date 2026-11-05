#!/usr/bin/env python3
"""Conservative, serialized seven-day refresh for the five monitored DE sets.

Only launches the next due set when no eBay collector is running. A completed
set is not re-launched for seven days; unsuccessful attempts retry next day.
Each card uses its own successful-scan cursor and 2-day overlap.
"""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import json,os,subprocess,sys

ROOT=Path('/home/tv/cardyssey-ebay-collector/admin-set-runs')
SCHEDULE=ROOT/'weekly-schedule.json'
SET_IDS=('30th','30th-c','mep','sv02','sv01')

def as_date(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError,AttributeError,TypeError):return None

def due_set(now,schedule,jobs):
    for set_id in SET_IDS:
        recorded=schedule.get(set_id,{})
        last=as_date(recorded.get('last_attempt'))
        job=jobs.get(set_id,{})
        # A complete, successful run was already performed recently, whether
        # manually or by this timer.
        completed=as_date(job.get('checked_at')) if job.get('status')=='COMPLETE' else None
        anchor=max((x for x in (last,completed) if x is not None),default=None)
        incomplete=job.get('status') in ('STOPPED_SERVICE_ERRORS','STOPPED_LOGIN_REQUIRED','STOPPED_BLOCKED','INTERRUPTED') or (
            job.get('status')=='COMPLETE' and any(
                row.get('status') in ('FETCH_INCOMPLETE','CATALOG_CHANGED') or
                row.get('scan_checkpoint_updated') is False
                for row in job.get('results',[])))
        # A queued launch with no active worker can be stranded after a restart.
        # The run() worker gate prevents concurrent collectors; retry only after a cooldown.
        if job.get("status")=="QUEUED" and last and (now-last)>=timedelta(minutes=30):return set_id
        if incomplete and anchor and (now-anchor)>=timedelta(days=1):return set_id
        if anchor is None or (now-anchor)>=timedelta(days=7):return set_id
    return None

def run():
    import fcntl
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'weekly-schedule.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        workers=subprocess.run(['pgrep','-f','^python3 -u anniversary_batch.py'],capture_output=True,text=True)
        if workers.returncode==0:
            print(json.dumps({'status':'BUSY','workers':len(workers.stdout.splitlines())}));return 0
        jobs={}
        for name in SET_IDS:
            p=ROOT/name/'progress.json'
            try:jobs[name]=json.loads(p.read_text())
            except (OSError,ValueError):jobs[name]={}
        try:schedule=json.loads(SCHEDULE.read_text())
        except (OSError,ValueError):schedule={}
        now=datetime.now(timezone.utc)
        selected=due_set(now,schedule,jobs)
        if selected is None:
            print(json.dumps({'status':'UP_TO_DATE'}));return 0
        proc=subprocess.run([sys.executable,'/home/tv/cardshop/scripts/price_set_jobs.py',
                             'start',selected,'--incremental'],capture_output=True,text=True,timeout=90)
        try:result=json.loads(proc.stdout)
        except ValueError:result={'error':'INVALID_LAUNCH_RESPONSE'}
        if not result.get('started'):
            print(json.dumps({'status':'LAUNCH_FAILED','set':selected,'result':result}));return 1
        schedule[selected]={'last_attempt':now.isoformat(), 'mode':'INCREMENTAL',
                            'latest_result':result}
        temp=SCHEDULE.with_suffix('.json.tmp')
        temp.write_text(json.dumps(schedule,indent=2,ensure_ascii=False))
        temp.replace(SCHEDULE)
        print(json.dumps({'status':'STARTED','set':selected,'mode':'INCREMENTAL'}));return 0

if __name__=='__main__':raise SystemExit(run())
