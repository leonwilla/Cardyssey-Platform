#!/usr/bin/env python3
"""Start a new resumable verification epoch; preserve previous observations.

Only called by the authenticated Cardyssey founder/admin action. Refuse to
replace an active epoch while an actual Cardmarket queue process is running.
"""
import argparse,datetime,json,os,subprocess,tempfile,fcntl,time
from pathlib import Path
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')

def reset(base=BASE, check_process=True, now=None):
    # A full restart must work WHILE the scan is running. Stop only the
    # Cardmarket queue-runner's process tree, wait for it to exit, then create
    # a new epoch. No observation logs, reviewed routes, or prices are deleted.
    if check_process:
        ps=r'''
$ErrorActionPreference='Stop'
$match='Cardmarket-(Queue-Runner|language-browser-collector)[.]ps1'
$all=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -match $match})
$ids=@($all | Select-Object -ExpandProperty ProcessId)
foreach($x in $all | Sort-Object ParentProcessId -Descending){
 try {Stop-Process -Id $x.ProcessId -Force -ErrorAction Stop} catch {if(Get-Process -Id $x.ProcessId -ErrorAction SilentlyContinue){throw}}
}
Start-Sleep -Seconds 2
$remaining=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -match $match})
if($remaining.Count){throw 'CARDMARKET_RUNNER_STILL_ACTIVE'}
[Console]::WriteLine('STOPPED='+$ids.Count)
'''
        r=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-Command',ps],text=True,capture_output=True,timeout=24)
        if r.returncode or 'STOPPED=' not in r.stdout:raise RuntimeError('cardmarket_scan_stop_failed: '+r.stderr[-250:])
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
