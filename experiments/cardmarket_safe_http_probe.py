#!/usr/bin/env python3
"""Conservative Cardmarket product-page probe based on the uploaded PriceCharting wreq transport.

Reads 10 known candidates, verifies product identity, and retains diagnostic metadata.
No price writes, no automated challenge solving after rate limits, and no proxy rotation.
"""
import argparse
import fcntl
import importlib.util
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("cardmarket_transport", ROOT/"cardmarket_cf_exact_transport.py")
transport=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=transport
SPEC.loader.exec_module(transport)

def parse_product(body):
    text=body.decode("utf-8","replace")
    title=re.search(r"<title>(.*?)</title>",text,re.S|re.I)
    product_id=re.search(r'name=["\']idProduct["\']\s+value=["\'](\d+)["\']',text,re.I)
    return {
        "title":unescape(title.group(1).strip()) if title else None,
        "product_id":product_id.group(1) if product_id else None,
        "article_rows_visible":len(re.findall(r'class=["\'][^"\']*\barticle-row\b',text,re.I)),
        "price_markup_present":bool(re.search(r'\d+[,.]\d{2}\s*€',text)),
        "german_nm_confirmed":False,
        "price_published":False,
    }

def calculate_wait(seconds, elapsed):
    return max(0,seconds-elapsed)

def run(cases, output, min_interval, cooldown_minutes):
    session=transport.load_session("direct")
    if session is None:raise RuntimeError("No valid session; initialize only with the original transport on Cardmarket first")
    client=transport.build_client(session.identity,None,False,session.exit_ip)
    out=Path(output)
    out.parent.mkdir(parents=True,exist_ok=True)
    summary={"attempted":0,"successful":0,"rate_limited":0,"identity_matches":0,"stopped_reason":None}
    for i,case in enumerate(cases,1):
        url=case["url"]
        parsed=urlparse(url)
        if parsed.scheme!="https" or parsed.hostname!="www.cardmarket.com" or not parsed.path.startswith("/de/Pokemon/Products/Singles/"):
            raise ValueError("Invalid or untrusted Cardmarket product URL")
        started=time.monotonic()
        entry={"index":i,"card_id":case["card_id"],"expected_product_id":str(case["expected_product_id"]),"checked_at":datetime.now(timezone.utc).isoformat()}
        try:
            response,body=transport.navigate(client,session,url)
            status=response.status.as_int()
            entry.update(http_status=status,classification=transport.classify(response,body),seconds=round(time.monotonic()-started,3),bytes=len(body),cf_mitigated=transport._header(response,"cf-mitigated"),retry_after=transport._header(response,"retry-after"))
            if status==200 and entry["classification"]=="ok":
                page=parse_product(body)
                entry.update(page)
                entry["product_id_matches"]=page["product_id"]==entry["expected_product_id"]
                if entry["product_id_matches"]:summary["identity_matches"]+=1
                summary["successful"]+=1
            elif status==429 or entry["classification"] in ("blocked","challenge"):
                summary["rate_limited"]+=1
                summary["stopped_reason"]="HTTP_"+str(status)+"_RATE_LIMIT_OR_CHALLENGE"
                # Honor a requested cooldown; do not immediately retry, re-solve, rotate, or evade.
                until=datetime.now(timezone.utc)+timedelta(minutes=cooldown_minutes)
                retry=entry["retry_after"]
                if retry.isdecimal():
                    until=max(until,datetime.now(timezone.utc)+timedelta(seconds=int(retry)))
                elif retry:
                    try:
                        requested=parsedate_to_datetime(retry)
                        if requested.tzinfo is not None:
                            until=max(until,requested.astimezone(timezone.utc))
                    except (TypeError,ValueError,OverflowError):pass
                entry["not_before_utc"]=until.isoformat()
                (out.parent/"cardmarket_http_cooldown.json").write_text(json.dumps({"until":entry["not_before_utc"],"reason":summary["stopped_reason"]}))
            else:
                summary["stopped_reason"]="HTTP_"+str(status)
        except Exception as exc:
            entry["error"]=str(exc)[:160]
            summary["stopped_reason"]="REQUEST_ERROR"
        summary["attempted"]+=1
        with out.open("a") as handle:handle.write(json.dumps(entry,ensure_ascii=False)+"\n")
        print(json.dumps(entry,ensure_ascii=False),flush=True)
        if summary["stopped_reason"]:break
        if i<len(cases):
            time.sleep(calculate_wait(min_interval,time.monotonic()-started))
    transport.save_session(session)
    print("SUMMARY",json.dumps(summary),flush=True)
    return summary

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=Path("/tmp/cardyssey-cm-test-10-input.json"))
    parser.add_argument("--output",type=Path,default=Path("/tmp/cardyssey-cm-safe-test-results.jsonl"))
    parser.add_argument("--min-interval",type=float,default=12)
    parser.add_argument("--cooldown-minutes",type=int,default=30)
    args=parser.parse_args()
    if args.min_interval<10:parser.error("minimum safe request spacing is 10 seconds")
    lock=Path("/tmp/cardyssey-cardmarket-safe-http.lock")
    with lock.open("a+") as lock_file:
        try:fcntl.flock(lock_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit("Another HTTP test is already running")
        cooldown=args.output.parent/"cardmarket_http_cooldown.json"
        if cooldown.exists():
            state=json.loads(cooldown.read_text())
            if datetime.fromisoformat(state["until"])>datetime.now(timezone.utc):
                raise SystemExit("Cooldown active until "+state["until"])
        cases=json.loads(args.input.read_text())
        return run(cases,args.output,args.min_interval,args.cooldown_minutes)

if __name__=="__main__":main()
