#!/usr/bin/env python3
"""Read-only health checks for live API, Web, Shop and authentication boundaries."""
import json
import subprocess

def get(url):
    result=subprocess.run(["curl","-sS","-L","--connect-timeout","8","--max-time","20",
        "-w","\n%{http_code}",url],text=True,capture_output=True,check=True,timeout=25)
    body,status=result.stdout.rsplit("\n",1)
    return int(status),body

def main():
    failures=[]
    checks=[
        ("web","https://cardyssey.de/",200),
        ("shop","https://shop.cardyssey.de/",200),
        ("collection-auth","https://api.cardyssey.de/api/v1/collection",401),
        ("pricing-auth","https://api.cardyssey.de/api/v1/pricing/cards/__smoke__?language=en&variant=NORMAL",401),
    ]
    for name,url,expected in checks:
        try:
            status,_=get(url)
            if status!=expected:
                failures.append(f"{name}: HTTP {status}, expected {expected}")
            print(f"{name}: HTTP {status}",flush=True)
        except Exception as error:
            failures.append(f"{name}: {error}")
    try:
        status,body=get("http://127.0.0.1:8081/api/v1/health")
        data=json.loads(body)
        if status!=200 or data.get("status")!="ok" or data.get("database")!="connected":
            failures.append("API/database unhealthy")
        if data.get("tcgPriceCacheTtlHours")!=168 or data.get("tcgPriceWorkerEnabled") is not True:
            failures.append("weekly TCG price worker not configured")
        print(json.dumps(data),flush=True)
    except Exception as error:
        failures.append(f"api: {error}")
    for failure in failures:
        print("FAIL: "+failure,flush=True)
    raise SystemExit(bool(failures))
if __name__=="__main__":
    main()
