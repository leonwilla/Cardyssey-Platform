#!/usr/bin/env python3
"""Install canonical Cardmarket PowerShell modules into the dedicated Windows profile.

Do not touch browser profile, cookies, price files, queues or progress. Never
replace modules while an actual Windows collector is executing.
"""
from __future__ import annotations
import argparse,os,subprocess,shutil,tempfile,hashlib
from pathlib import Path

CORE=Path(__file__).resolve().parent
ADMIN=CORE.parent/'admin'
REPO=CORE.parents[2]
DEFAULT_DEST=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
CHECK=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector/pre-weekly-process-check-20261111.ps1')
PS='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'

def manifest():
    result={}
    for p in CORE.glob('*.ps1'):
        result[p.name]=p
    for p in ADMIN.glob('*.ps1'):
        if p.name.startswith(('Cardmarket-','cardmarket-')):result[p.name]=p
    for n in ('cardmarket-game-profile.json','cardmarket-comment-rules.json'):
        result[n]=REPO/'config'/n
    for src in result.values():
        if not src.is_file():raise RuntimeError('Missing source: '+str(src))
    return result

def scanner_idle():
    if not CHECK.is_file():raise RuntimeError('Windows process checker missing')
    p=subprocess.run([PS,'-NoProfile','-ExecutionPolicy','Bypass','-File',
                      str(CHECK).replace('/mnt/c/','C:/').replace('/','\\')],
                     capture_output=True,text=True,timeout=25)
    if p.returncode or 'ACTIVE_CARDMARKET_WINDOWS_SCANNERS=0' not in p.stdout:
        raise RuntimeError('Windows scanner active or process check failed')

def deploy(dest=DEFAULT_DEST,dry_run=True,require_idle=True):
    files=manifest()
    if not dest.is_dir():raise ValueError('Windows collector directory missing')
    changes=[]
    for name,src in files.items():
        target=dest/name
        contents=src.read_bytes()
        if target.exists() and target.read_bytes()==contents:continue
        changes.append((name,src,contents))
    if not dry_run and changes and require_idle:
        scanner_idle()
    if dry_run:return {'mode':'DRY_RUN','changed':[name for name,_,_ in changes]}
    # Preserve exact prior modules for rollback. Never modify running data.
    backup=dest/'module-backups'
    backup.mkdir(exist_ok=True)
    for name,_,data in changes:
        target=dest/name
        if target.exists():shutil.copy2(target,backup/name)
        fd,temp=tempfile.mkstemp(prefix='cm-module-',suffix='.tmp',dir=dest)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(temp,target)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    mismatches=[name for name,src in files.items() if not (dest/name).is_file() or
                hashlib.sha256(src.read_bytes()).digest()!=hashlib.sha256((dest/name).read_bytes()).digest()]
    if mismatches:raise RuntimeError('Module SHA256 mismatches: '+','.join(mismatches))
    return {'mode':'APPLIED','changed':[name for name,_,_ in changes],
            'verified':len(files),'sha256_identical':True}

if __name__=='__main__':
    import json
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    print(json.dumps(deploy(dry_run=not args.apply)))
