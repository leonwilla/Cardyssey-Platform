#!/usr/bin/env python3
"""Allowlisted eBay set-run launcher/status. Never interpolates a shell command."""
import sys,json,subprocess,os,time,fcntl,shutil,hashlib
from pathlib import Path
BASE=Path('/home/tv/cardyssey-ebay-collector');JOBS=BASE/'admin-set-runs';JOBS.mkdir(exist_ok=True)
action=sys.argv[1];setid=sys.argv[2]
incremental='--incremental' in sys.argv[3:]
if any(arg!='--incremental' for arg in sys.argv[3:]):sys.exit('UNKNOWN_OPTION')
if setid not in {'30th','30th-c','mep','sv01','sv02'}:sys.exit('UNSUPPORTED_EBAY_SET')
job=JOBS/setid
if action=='start':
 lock=JOBS/'launch.lock'
 with lock.open('w') as f:
  fcntl.flock(f,fcntl.LOCK_EX)
  active=subprocess.run(['pgrep','-f','^python3 -u anniversary_batch.py'],capture_output=True,text=True).returncode==0
  if active:
   print(json.dumps({'error':'EBAY_BROWSER_BUSY','active':True}));sys.exit(0)
  # Keep the persistent Tiny collector in sync with the tested, git-tracked source.
  source=Path('/home/tv/cardshop/scripts/ebay-collector/anniversary_batch.py')
  target=BASE/'anniversary_batch.py'
  if not source.is_file():
   print(json.dumps({'error':'COLLECTOR_SOURCE_MISSING'}));sys.exit(0)
  if hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(target.read_bytes()).digest():
   shutil.copy2(source,target)
  parser_source=Path('/home/tv/cardshop/scripts/ebay-collector/ebay_sold.py')
  parser_target=BASE/'ebay_sold.py'
  if parser_source.is_file() and hashlib.sha256(parser_source.read_bytes()).digest()!=hashlib.sha256(parser_target.read_bytes()).digest():
   shutil.copy2(parser_source,parser_target)
  cursor_source=Path('/home/tv/cardshop/scripts/ebay-collector/incremental_scan.py')
  cursor_target=BASE/'incremental_scan.py'
  if cursor_source.is_file() and (not cursor_target.exists() or hashlib.sha256(cursor_source.read_bytes()).digest()!=hashlib.sha256(cursor_target.read_bytes()).digest()):
   shutil.copy2(cursor_source,cursor_target)
  policy_source=Path('/home/tv/cardshop/scripts/ebay-collector/source_policy.py')
  policy_target=BASE/'source_policy.py'
  if policy_source.is_file() and (not policy_target.exists() or hashlib.sha256(policy_source.read_bytes()).digest()!=hashlib.sha256(policy_target.read_bytes()).digest()):
   shutil.copy2(policy_source,policy_target)
  purchase_source=Path('/home/tv/cardshop/scripts/ebay-collector/purchase_history.py')
  purchase_target=BASE/'purchase_history.py'
  if purchase_source.is_file() and (not purchase_target.exists() or hashlib.sha256(purchase_source.read_bytes()).digest()!=hashlib.sha256(purchase_target.read_bytes()).digest()):
   shutil.copy2(purchase_source,purchase_target)
  offer_source=Path('/home/tv/cardshop/scripts/ebay-collector/offer_references.py')
  offer_target=BASE/'offer_references.py'
  if offer_source.is_file() and (not offer_target.exists() or hashlib.sha256(offer_source.read_bytes()).digest()!=hashlib.sha256(offer_target.read_bytes()).digest()):
   shutil.copy2(offer_source,offer_target)
  history_source=Path('/home/tv/cardshop/scripts/ebay-collector/price_history.py')
  history_target=BASE/'price_history.py'
  if history_source.is_file() and (not history_target.exists() or hashlib.sha256(history_source.read_bytes()).digest()!=hashlib.sha256(history_target.read_bytes()).digest()):
   shutil.copy2(history_source,history_target)
  # A crashed worker must not block every future set run forever.
  # Preserve all completed card results and mark stale work as interrupted.
  for progress in JOBS.glob('*/progress.json'):
   previous=json.loads(progress.read_text())
   if previous.get('status')=='RUNNING':
    previous['status']='INTERRUPTED'
    temp=progress.with_suffix('.json.tmp')
    temp.write_text(json.dumps(previous,ensure_ascii=False))
    temp.replace(progress)
  if setid in ('sv01','sv02'):
   from subprocess import check_output
   denom=198 if setid=='sv01' else 193
   name='Karmesin & Purpur' if setid=='sv01' else 'Entwicklungen in Paldea'
   sql=f"SELECT COALESCE(json_agg(t),'[]') FROM (SELECT card_id,name,local_id,set_id,variants FROM catalog_cards_mirror WHERE language_code='de' AND set_id='{setid}' AND local_id ~ '^[0-9]+$' AND local_id::int <= {denom} ORDER BY local_id::int) t"
   selected=json.loads(check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-Atc',sql],text=True,timeout=15))
   for c in selected:c.update(denominator=denom,set_name=name)
  else:
   allcards=json.loads((BASE/'anniversary-20261021'/'manifest.json').read_text());selected=[c for c in allcards if c['set_id']==setid]
  if not selected:print(json.dumps({'error':'NO_CARDS'}));sys.exit(0)
  job.mkdir(exist_ok=True)
  # Resume an interrupted run without losing already-checked cards.
  # Completed runs begin fresh, with the previous audit archived.
  previous_file=job/'progress.json'
  previous=json.loads(previous_file.read_text()) if previous_file.exists() else {}
  saved_manifest=json.loads((job/'manifest.json').read_text()) if (job/'manifest.json').exists() else []
  resume=(previous.get('status') in ('INTERRUPTED','RUNNING','QUEUED','STOPPED_SERVICE_ERRORS')
          and {c['card_id'] for c in saved_manifest}=={c['card_id'] for c in selected}
          and bool(saved_manifest))
  if previous_file.exists() and not resume:
   archive=JOBS/(setid+'-history-'+str(int(time.time())));job.rename(archive);job.mkdir()
  if resume:
   previous['status']='QUEUED'
   previous['started_at']=time.time()
   previous['run_start_done']=len(previous.get('results',[]))
   previous_file.write_text(json.dumps(previous,ensure_ascii=False))
  else:
   (job/'manifest.json').write_text(json.dumps(selected,ensure_ascii=False))
   (job/'progress.json').write_text(json.dumps({'status':'QUEUED','total':len(selected),'results':[],'started_at':time.time(),'run_start_done':0}))
  log=(job/'runner.log').open('a')
  subprocess.Popen(['python3','-u','anniversary_batch.py','--out',str(job)]+(['--incremental'] if incremental else []),cwd=str(BASE),stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
  print(json.dumps({'started':True,'total':len(selected),'incremental':incremental}))
elif action=='status':
 p=job/'progress.json';d=json.loads(p.read_text()) if p.exists() else {'status':'NOT_STARTED','results':[]}
 results=d.get('results',[]);total=d.get('total',len(results))
 started=d.get('started_at');completed_since_start=len(results)-d.get('run_start_done',0)
 elapsed=max(1,time.time()-started) if isinstance(started,(int,float)) else None
 remaining=round(elapsed/completed_since_start*(total-len(results))) if elapsed and completed_since_start>0 and d.get('status')=='RUNNING' else None
 print(json.dumps({'status':d.get('status','NOT_STARTED'),'finished':len(results),'total':total,'counts':d.get('counts',{}),'estimatedRemainingSeconds':remaining,'last':results[-1] if results else None}))
else:sys.exit('BAD_ACTION')
