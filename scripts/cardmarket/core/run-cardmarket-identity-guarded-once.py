#!/usr/bin/env python3
"""Run a user-requested weekly Cardmarket refresh in protected quiet period.

Backup both queues, preserve scan progress, reject active runner, rollback
queue CSV on any failed subprocess/validation. No browser starts or stops.
"""
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import csv,fcntl,hashlib,json,os,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/home/tv/cardshop')
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
BACKUP=ROOT/'backups'/('cardmarket-weekly-guarded-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
LOG=ROOT/'logs'/('cardmarket-weekly-guarded-'+datetime.now(timezone.utc).strftime('%Y%m%d')+'.log')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    from cardmarket_delta_scan import lock_queue_active
    BACKUP.mkdir(parents=True,exist_ok=True)
    lock_queue_active(BASE,datetime.now(timezone.utc))
    checker='C:\\Users\\TV\\AppData\\Local\\Cardyssey\\CardmarketCollector\\pre-weekly-process-check-20261111.ps1'
    guard=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',checker],capture_output=True,text=True,timeout=20)
    if guard.returncode!=0 or 'ACTIVE_CARDMARKET_WINDOWS_SCANNERS=0' not in guard.stdout:
        raise RuntimeError('Windows scanner still active or unavailable: refuse queue rewrite')
    paths=['queue-de.csv','queue-en.csv','progress-de.json','progress-en.json']
    prior={}
    for name in paths:
        source=BASE/name
        if not source.exists():raise RuntimeError('Missing '+name)
        before=BACKUP/name
        if not before.exists():shutil.copy2(source,before)
        prior[name]=sha(source)
    lock=Path('/tmp/cardyssey-cardmarket-identity-weekly.lock')
    with lock.open('a+') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            with LOG.open('a',encoding='utf-8') as log:
                log.write('BEGIN '+datetime.now(timezone.utc).isoformat()+'\n');log.flush()
                res=subprocess.run([sys.executable,str(ROOT/'scripts/cardmarket/core/run-cardmarket-identity-weekly.py'),'--apply'],
                   cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=1500)
            if res.returncode:raise RuntimeError('weekly returned '+str(res.returncode))
            for lang in ('de','en'):
                dest=BASE/f'queue-{lang}.csv'
                with dest.open(encoding='utf-8-sig',newline='') as f:
                    rows=list(csv.DictReader(f))
                if len(rows)<30000 or len({(r['cardyssey_karte'],r['variante_id']) for r in rows})!=len(rows):
                    raise ValueError('weekly queue count or uniqueness invalid for '+lang)
            for name in ('progress-de.json','progress-en.json'):
                if sha(BASE/name)!=prior[name]:raise RuntimeError('weekly mutated '+name)
            state=BASE/'cardmarket-guide-delta-state.json'
            info=json.loads(state.read_text(encoding='utf-8'))
            assert info['gameId']==6 and len(info['products'])>10000
            print(json.dumps({'status':'APPLIED','date':info['createdAt'],
                'products':len(info['products']),'log':str(LOG),
                'progressUnchanged':True,'priceCacheWrites':False}))
        except BaseException as ex:
            for lang in ('de','en'):
                shutil.copy2(BACKUP/f'queue-{lang}.csv',BASE/f'queue-{lang}.csv')
            with LOG.open('a') as log:log.write('ROLLBACK '+repr(ex)+'\n')
            print('ROLLBACK_ERROR',repr(ex),file=sys.stderr)
            raise
if __name__=='__main__':main()
