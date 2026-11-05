#!/usr/bin/env python3
"""Non-charging CapSolver readiness and getBalance check.

No captcha tasks are created. Never logs the key or private proxy details.
Config: CAPSOLVER_API_KEY in process env or chmod 600
~/.config/cardyssey/capsolver.key; optional CAPSOLVER_PROXY in environment.
"""
import json, os, stat
from pathlib import Path
import requests

KEYFILE=Path.home()/'.config/cardyssey/capsolver.key'

def preflight():
    result={'api':'https://api.capsolver.com/getBalance','taskCreated':False}
    proxy=os.getenv('CAPSOLVER_PROXY','').strip()
    result['staticProxyConfigured']=bool(proxy)
    key=os.environ.get('CAPSOLVER_API_KEY','').strip()
    if not key and KEYFILE.exists():
        if stat.S_IMODE(KEYFILE.stat().st_mode) != 0o600:
            result['status']='INSECURE_KEY_FILE_PERMISSIONS'
            return result
        key=KEYFILE.read_text().strip()
    if not key:
        result['status']='MISSING_API_KEY'
        return result
    try:
        resp=requests.post('https://api.capsolver.com/getBalance',json={'clientKey':key},timeout=15)
        data=resp.json()
        accepted=getattr(resp,'status_code',200) < 400 and data.get('errorId') == 0
        result.update(status='API_ACCEPTED' if accepted else 'API_REJECTED',
                      httpStatus=getattr(resp,'status_code',200),
                      errorCode=data.get('errorCode') if not accepted else None,
                      balanceUsd=data.get('balance') if accepted else None,
                      packagesCount=len(data.get('packages') or []))
    except (requests.RequestException, ValueError) as exc:
        result.update(status='API_CONNECTION_ERROR',errorType=type(exc).__name__)
    return result

if __name__=='__main__':
    print(json.dumps(preflight(),ensure_ascii=False))
