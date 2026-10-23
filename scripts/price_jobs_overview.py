#!/usr/bin/env python3
import json,subprocess,time
from pathlib import Path
root=Path('/home/tv/cardyssey-ebay-collector')
active=subprocess.run(['pgrep','-f','^python3 -u anniversary_batch.py'],capture_output=True,text=True).stdout.strip()
queued=subprocess.run(['pgrep','-f','^python3 -u queue_extra_sets.py'],capture_output=True,text=True).stdout.strip()
names={'sv01':'Karmesin & Purpur','sv02':'Entwicklungen in Paldea','30th':'30 Jahre – Jubiläum','30th-c':'30 Jahre – Classic','mep':'MEP-Promos'}
jobs=[]
for parent in [root/'anniversary-precise-search-20261023',*(root/'admin-set-runs'/s for s in names)]:
 p=parent/'progress.json'
 if not p.exists():continue
 data=json.loads(p.read_text());results=data.get('results',[]);total=data.get('total',0);status=data.get('status','UNKNOWN');running=bool(active) and (parent.name=='anniversary-precise-search-20261023' or status=='RUNNING')
 if status=='RUNNING' and not running:status='INTERRUPTED'
 elapsed=max(1,time.time()-p.stat().st_ctime)
 eta=None # No reliable start timestamp for historical batch; do not invent ETA
 jobs.append({'id':parent.name,'name':'30 Jahre – fehlende eBay-Preise' if parent.name=='anniversary-precise-search-20261023' else names.get(parent.name,parent.name),'status':status,'done':len(results),'total':total,'counts':data.get('counts',{}),'etaSeconds':eta,'running':running})
# External queued sets must not be reported as already running.
for setid in ('sv01','sv02'):
 if queued and not any(j['id']==setid for j in jobs):jobs.append({'id':setid,'name':names[setid],'status':'WAITING','done':0,'total':0,'counts':{},'etaSeconds':None,'running':False})
print(json.dumps({'jobs':jobs,'collectorActive':bool(active),'queueActive':bool(queued),'checkedAt':int(time.time())}))
