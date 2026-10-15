#!/usr/bin/env python3
"""Shared conservative downloader for Cardyssey's DE/EN JSON price feeds.

Uses explicit host allowlist, bounded response, atomic disk cache, lock against
duplicate concurrent downloads, and Retry-After aware retries. No challenges
or login bypass. Read-only: never writes prices.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import time
from urllib.parse import urlsplit
import requests

HOSTS={"tcgcsv.com","downloads.s3.cardmarket.com"}
CACHE=Path(os.environ.get("CARDYSSEY_FEED_CACHE","/home/tv/.local/state/cardyssey-queue/price-feeds"))
MAX_BYTES=80_000_000

def fetch_json(url,*,headers=None,max_age=20*3600,timeout=45,attempts=3):
    parsed=urlsplit(url)
    if parsed.scheme!="https" or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port:
        raise ValueError("Unapproved feed host")
    CACHE.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(url.encode()).hexdigest()
    cache=CACHE/(key+".json")
    with (CACHE/(key+".lock")).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if cache.exists() and time.time()-cache.stat().st_mtime<max_age:
            try:return json.loads(cache.read_text())
            except (ValueError,OSError):pass
        error=None
        for attempt in range(attempts):
            try:
                with requests.get(url,headers=headers,timeout=(10,timeout),stream=True,allow_redirects=False) as r:
                    if r.status_code in (301,302,303,307,308):raise RuntimeError("Redirect disabled")
                    if r.status_code in (401,403):raise RuntimeError("Provider denied access: "+str(r.status_code))
                    if r.status_code in (429,500,502,503,504):
                        wait=r.headers.get("Retry-After")
                        delay=min(90,max(2,float(wait))) if wait and wait.isdigit() else min(45,2**attempt*4)
                        if attempt+1<attempts:time.sleep(delay)
                        else:raise RuntimeError("Provider unavailable: "+str(r.status_code))
                        continue
                    r.raise_for_status()
                    if "json" not in r.headers.get("Content-Type","").lower():raise ValueError("Unexpected feed content type")
                    data=bytearray()
                    for chunk in r.iter_content(131072):
                        data.extend(chunk)
                        if len(data)>MAX_BYTES:raise ValueError("Feed too large")
                decoded=json.loads(data)
                tmp=cache.with_suffix(".tmp."+str(os.getpid()))
                tmp.write_text(json.dumps(decoded,separators=(",",":")))
                tmp.replace(cache)
                return decoded
            except (requests.Timeout,requests.ConnectionError) as exc:
                error=exc
                if attempt+1<attempts:time.sleep(min(30,2**attempt*3))
        raise RuntimeError("Feed request failed: "+url) from error
