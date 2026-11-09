#!/usr/bin/env python3
"""Start a new resumable verification epoch; preserve previous observations.

Only called by the authenticated Cardyssey founder/admin action. Refuse to
replace an active epoch while an actual Cardmarket queue process is running.
"""
import argparse,datetime,json,os,subprocess,tempfile
from pathlib import Path
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')

def reset(base=BASE, check_process=True, now=None):
    if check_process:
        ps=r'''$p=@(Get-CimInstance Win32_Process|Where-Object{$_.Name -eq 'powershell.exe' -and $_.CommandLine -match '-File.*Cardmarket-Queue-Runner[.]ps1'});[Console]::WriteLine($p.Count)'''
        r=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-Command',ps],text=True,capture_output=True,timeout=12)
        if r.returncode or r.stdout.strip()!='0':raise RuntimeError('cardmarket_scan_running_or_process_status_unavailable')
    for lang in ('de','en'):
        p=base/f'queue-{lang}.csv'
        if not p.is_file() or p.stat().st_size<1000:raise RuntimeError('cardmarket_queue_missing_'+lang)
    timestamp=(now or datetime.datetime.now(datetime.timezone.utc)).isoformat()
    epoch={'requestedAt':timestamp,'scope':['de','en'],'reason':'User-triggered complete Cardmarket DE/EN rescan','preserveHistory':True}
    base.mkdir(parents=True,exist_ok=True)
    path=base/'full-rescan-epoch.json'
    # One atomic epoch write; previous result files deliberately remain intact.
    fd,tmp=tempfile.mkstemp(prefix='full-rescan-',suffix='.tmp',dir=base)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(epoch,f,ensure_ascii=False)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    for lang in ('de','en'):
        p=base/f'progress-{lang}.json'
        old={}
        if p.exists():
            try:old=json.loads(p.read_text(encoding='utf-8-sig'))
            except ValueError:pass
        old.update(status='QUEUED',done=0,updated_at=timestamp,last_card='',full_rescan_started_at=timestamp)
        fd,tmp=tempfile.mkstemp(prefix='progress-'+lang+'-',suffix='.tmp',dir=base)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(old,f,ensure_ascii=False)
            os.replace(tmp,p)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    return {'ok':True,'startedAt':timestamp,'languages':['de','en'],'historyPreserved':True}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--execute',action='store_true');args=a.parse_args()
    if not args.execute:raise SystemExit('missing --execute')
    print(json.dumps(reset(),ensure_ascii=False))
