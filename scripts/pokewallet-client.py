#!/usr/bin/env python3
"""Private server-side PokéWallet client with persistent request budgets.
No credentials in repository, command arguments, reports or error messages.
"""
import argparse,fcntl,json,os,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
from datetime import datetime,timezone
BASE="https://api.pokewallet.io"
KEY_FILE=Path("/home/tv/.config/cardyssey/secrets/pokewallet-api-key")
STATE_DIR=Path("/home/tv/.cache/cardyssey-pokewallet")
class ProviderError(RuntimeError):pass
class Client:
 def __init__(self,key_file=KEY_FILE,state_dir=STATE_DIR,hour_budget=90,day_budget=900):
  self.key_file=Path(key_file);self.state_dir=Path(state_dir);self.hour_budget=hour_budget;self.day_budget=day_budget
  if not 1<=hour_budget<=90 or not 1<=day_budget<=900:raise ValueError("budget exceeds free-plan reserve")
  self.state_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
 def get(self,path,params=None):
  if not path.startswith("/") or "://" in path or "?" in path:raise ValueError("invalid provider path")
  if self.key_file.stat().st_mode & 0o077:raise ProviderError("API key file must have permissions 0600")
  key=self.key_file.read_text().strip()
  if not key.startswith("pk_live_"):raise ProviderError("API key format invalid")
  # Lock covers reservation and response: concurrent workers share the same budget.
  ledger=self.state_dir/"budget.json"
  fd=os.open(self.state_dir/"budget.lock",os.O_CREAT|os.O_RDWR,0o600)
  with os.fdopen(fd,"a+") as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   now=time.time()
   state=json.loads(ledger.read_text()) if ledger.exists() else {}
   events=[t for t in state.get("requests",[]) if now-t<86400]
   if now<state.get("blocked_until",0):raise ProviderError("provider rate limit active")
   if sum(now-t<3600 for t in events)>=self.hour_budget or len(events)>=self.day_budget:raise ProviderError("local request budget exhausted")
   state["requests"]=events+[now]
   def save():
    tmp=ledger.with_suffix(".tmp");tmp.write_text(json.dumps(state));tmp.chmod(0o600);tmp.replace(ledger)
   save()
   url=BASE+path+("?" + urllib.parse.urlencode(params) if params else "")
   req=urllib.request.Request(url,headers={"X-API-Key":key,"User-Agent":"Cardyssey/0.5 provider-integration","Accept":"application/json"})
   try:
    with urllib.request.urlopen(req,timeout=45) as response:
     result=json.load(response)
     remaining=response.headers.get("X-RateLimit-Remaining-Hour")
     if remaining is not None and int(remaining)<=10:
      state["blocked_until"]=now+3600;save()
     return result
   except urllib.error.HTTPError as error:
    if error.code==429:state["blocked_until"]=now+3600;save()
    raise ProviderError("PokéWallet HTTP "+str(error.code)) from None
   except (urllib.error.URLError,TimeoutError,ValueError):
    raise ProviderError("PokéWallet request failed") from None
def inventory(client):
 data=client.get("/sets")
 if data.get("success") is not True or not isinstance(data.get("data"),list):raise ProviderError("unexpected set inventory schema")
 counts={}
 for row in data["data"]:
  language=row.get("language","unknown");counts[language]=counts.get(language,0)+1
 return {"observed_at":datetime.now(timezone.utc).isoformat(),"set_count":len(data["data"]),"provider_language_codes":counts,
         "note":"Set-language inventory is not verified price coverage. Image languages do not identify priced printings.","sets":data["data"]}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--inventory",action="store_true",required=True);p.add_argument("--report",type=Path,required=True);args=p.parse_args()
 report=inventory(Client());tmp=args.report.with_suffix(".tmp");tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2));tmp.replace(args.report)
 print(json.dumps({k:v for k,v in report.items() if k!="sets"}))
if __name__=="__main__":main()
