#!/usr/bin/env python3
"""One-date guarded S3 delta comparison, then weekly apply ONLY if scanner idle.

Executed by a few one-shot local cron slots on 2026-11-12. Never restarts,
closes or interacts with the browser. No change to published price cache.
"""
import json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from cardmarket_delta_scan import BASE,apply,compile_guide,parsed_time,write_atomic
from cardmarket_game_profile import load_game_profile
from price_feed_client import fetch_json

ROOT=Path('/home/tv/cardshop')
REPORT=BASE/'cardmarket-next-day-delta-report-20261112.json'
APPLIED=BASE/'cardmarket-next-day-delta-applied-20261112.json'

def save(result):
    result['checkedAt']=datetime.now(timezone.utc).isoformat()
    write_atomic(REPORT,(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result,ensure_ascii=False),flush=True)

def run():
    local=datetime.now(ZoneInfo('Europe/Berlin'))
    if local.date().isoformat()!='2026-11-12':
        raise RuntimeError('This one-shot job is only for 2026-11-12')
    if APPLIED.exists():
        print(APPLIED.read_text(encoding='utf-8'));return
    old_path=BASE/'cardmarket-guide-delta-state.json'
    if not old_path.exists():raise RuntimeError('today baseline missing; do not guess a comparison')
    baseline=json.loads(old_path.read_text(encoding='utf-8'))
    if baseline.get('gameId')!=6:raise RuntimeError('wrong baseline game')
    before=parsed_time(baseline.get('createdAt'))
    if not before:raise RuntimeError('baseline without timestamp')
    feed=fetch_json(load_game_profile()['price_url'],max_age=0,attempts=2)
    current=compile_guide(feed)
    after=parsed_time(current['createdAt'])
    if not after or after<=before:
        save({'status':'WAITING_FOR_NEW_OFFICIAL_GUIDE',
              'baselineAt':baseline['createdAt'],
              'latestGuideAt':current['createdAt'],'pricesPublished':0})
        return
    preview=apply(base=BASE,feed=feed,old=baseline,dry_run=True)
    output={'status':'PREVIEW_READY','baselineAt':baseline['createdAt'],
       'latestGuideAt':current['createdAt'],'preview':preview,'pricesPublished':0}
    save(output)

    # Separate Windows process guard: status JSON alone can be stale.
    checker='C:\\Users\\TV\\AppData\\Local\\Cardyssey\\CardmarketCollector\\pre-weekly-process-check-20261111.ps1'
    guard=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',checker],
         capture_output=True,text=True,timeout=25)
    if guard.returncode or 'ACTIVE_CARDMARKET_WINDOWS_SCANNERS=0' not in guard.stdout:
        output['status']='PREVIEW_ONLY_SCANNER_ACTIVE'
        save(output)
        return
    # Re-run full pipeline only if its own active-run prechecks agree.
    cmd=[sys.executable,str(ROOT/'scripts/run-cardmarket-identity-guarded-once.py')]
    attempt=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=1650)
    if attempt.returncode:
        output['status']='PREVIEW_ONLY_WEEKLY_APPLY_BLOCKED'
        output['weeklyError']=(attempt.stderr or attempt.stdout)[-550:]
        save(output)
        return
    final=json.loads((BASE/'cardmarket-guide-delta-state.json').read_text(encoding='utf-8'))
    if final['createdAt']!=current['createdAt']:
        output['status']='PREVIEW_ONLY_GUIDE_CHANGED_DURING_APPLY'
        save(output)
        return
    output['status']='APPLIED_WITHOUT_BROWSER_RESTART'
    output['queueUpdated']=True
    output['pricesPublished']=0
    save(output)
    write_atomic(APPLIED,(json.dumps(output,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))

if __name__=='__main__':
    run()
