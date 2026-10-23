#!/usr/bin/env python3
"""Allowlisted eBay set-run launcher/status. Never interpolates a shell command."""
import sys,json,subprocess,os,time,fcntl
from pathlib import Path
BASE=Path('/home/tv/cardyssey-ebay-collector');JOBS=BASE/'admin-set-runs';JOBS.mkdir(exist_ok=True)
action=sys.argv[1];setid=sys.argv[2]
if setid not in {'30th','30th-c','mep'}:sys.exit('UNSUPPORTED_EBAY_SET')
job=JOBS/setid
if action=='start':
 lock=JOBS/'launch.lock'
 with lock.open('w') as f:
  fcntl.flock(f,fcntl.LOCK_EX)
  existing=[p for p in JOBS.glob('*/progress.json') if json.loads(p.read_text()).get('status')=='RUNNING']
  active=subprocess.run(['pgrep','-f','^python3 -u anniversary_batch.py'],capture_output=True,text=True).returncode==0
  if active or existing:print(json.dumps({'error':'EBAY_BROWSER_BUSY','active':True}));sys.exit(0)
  allcards=json.loads((BASE/'anniversary-20261021'/'manifest.json').read_text());selected=[c for c in allcards if c['set_id']==setid]
  if not selected:print(json.dumps({'error':'NO_CARDS'}));sys.exit(0)
  job.mkdir(exist_ok=True)
  # New run, preserve previous batch audit.
  if (job/'progress.json').exists():
   archive=JOBS/(setid+'-history-'+str(int(time.time())));job.rename(archive);job.mkdir()
  (job/'manifest.json').write_text(json.dumps(selected,ensure_ascii=False))
  log=(job/'runner.log').open('a')
  subprocess.Popen(['python3','-u',str(BASE/'anniversary_batch.py'),'--out',str(job)],cwd=str(BASE),stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
  print(json.dumps({'started':True,'total':len(selected)}))
elif action=='status':
 p=job/'progress.json';d=json.loads(p.read_text()) if p.exists() else {'status':'NOT_STARTED','results':[]}
 results=d.get('results',[]);total=d.get('total',len(results));started=job.stat().st_mtime if job.exists() else None
 elapsed=max(1,time.time()-started) if started else None
 remaining=round(elapsed/max(1,len(results))*(total-len(results))) if results and d.get('status')=='RUNNING' else None
 print(json.dumps({'status':d.get('status','NOT_STARTED'),'finished':len(results),'total':total,'counts':d.get('counts',{}),'estimatedRemainingSeconds':remaining,'last':results[-1] if results else None}))
else:sys.exit('BAD_ACTION')
