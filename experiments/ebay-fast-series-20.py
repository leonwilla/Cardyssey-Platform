#!/usr/bin/env python3
"""Bounded read-only 20-query eBay sold-search series on the existing Selenium Chrome session."""
import json, urllib.request, urllib.error, time, statistics, sys
from pathlib import Path
from urllib.parse import urlencode
base="http://localhost:4444"
def send(method,path,payload=None,timeout=23):
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(base+path,data=data,headers={"Content-Type":"application/json"},method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as f:return json.load(f)["value"]
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        return {"webdriver_error":e.code,"detail":raw[:300]}
s=send("GET","/status",timeout=5)
sessions=[slot["session"]["sessionId"] for node in s["nodes"] for slot in node["slots"] if slot.get("session")]
assert len(sessions)==1, "Expected single existing Selenium session"
sid=sessions[0]
old=send("GET",f"/session/{sid}/timeouts",timeout=5)
print("ORIGINAL_TIMEOUTS",old,flush=True)
send("POST",f"/session/{sid}/timeouts",{"script":24000},timeout=5)
queries=[
"Machomei 8/102 deutsch holo","Lucario MEP095 Pokemon","Pikachu 58/102 Pokemon",
"Glurak 4/102 deutsch holo","Turtok 2/102 deutsch","Bisaflor 15/102 deutsch",
"Dragoran 4/62 deutsch","Mewtwo 10/102 deutsch","Lugia 9/111 deutsch",
"Evoli 51/64 Pokemon","Nachtara 13/75 deutsch","Psiana 1/75 deutsch",
"Quajutsu 099 SVP Pokemon","Pikachu ex 238 Surging Sparks","Gengar 5/62 deutsch",
"Garados 6/102 deutsch","Raichu 14/102 deutsch","Arkani 23/102 deutsch",
"Relaxo 11/64 deutsch","Mew 8/15 Pokemon"
]
script=r"""const url=arguments[0],done=arguments[arguments.length-1];(async()=>{
 const start=performance.now();
 try{
  const ctl=new AbortController();
  const timer=setTimeout(()=>ctl.abort(),10000);
  let r;
  try{r=await fetch(url,{credentials:'include',signal:ctl.signal});}
  finally{clearTimeout(timer)}
  const t=await r.text();
  const d=new DOMParser().parseFromString(t,'text/html');
  const cards=[...d.querySelectorAll('.s-item,.s-card')];
  const raw=d.body?.innerText||'';
  const soldDateMarkers=(raw.match(/(?:Verkauft(?: am)?|Sold)\s*:?\s*(?:\d{1,2}[. /-]|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))/gi)||[]).length;
  done({status:r.status,ms:Math.round(performance.now()-start),bytes:t.length,title:d.title,
   offers:cards.length,soldDateMarkers,blocked:r.status===403||r.status===429||/captcha|pardon our interruption|security measure|verify you are human/i.test(d.title+' '+raw.slice(0,700)),
   endedUrl:r.url});
 }catch(e){done({error:String(e),ms:Math.round(performance.now()-start)});}
})();"""
output=Path("/tmp/cardyssey-ebay-fast-series-20.json")
results=[]
try:
 for i,q in enumerate(queries,1):
    u="/sch/i.html?"+urlencode({"_nkw":q,"LH_Sold":"1","LH_Complete":"1"})
    start=time.monotonic()
    res=send("POST",f"/session/{sid}/execute/async",{"script":script,"args":[u]},timeout=30)
    item={"index":i,"query":q,**res}
    results.append(item)
    print("CASE",json.dumps(item,ensure_ascii=False),flush=True)
    output.write_text(json.dumps(results,ensure_ascii=False,indent=2))
    if res.get("blocked") or res.get("status") in (403,429) or res.get("webdriver_error"):
        print("BREAK_PROVIDER_BLOCK_OR_WEBDRIVER_ERROR",flush=True);break
    if "error" in res:
        print("CASE_REQUEST_ERROR_CONTINUING",flush=True)
    if i<len(queries):time.sleep(1)
finally:
 send("POST",f"/session/{sid}/timeouts",old,timeout=5)
 try:print("TAB_STILL",send("GET",f"/session/{sid}/url",timeout=5),flush=True)
 except Exception as e:print("TAB_INSPECTION_ERROR",str(e),flush=True)
success=[x for x in results if x.get("status")==200 and x.get("offers",0)>0 and not x.get("blocked")]
print("SUMMARY",json.dumps({"attempted":len(results),"usable_html":len(success),
 "blocked":sum(bool(x.get("blocked")) for x in results),
 "errors":sum("error" in x or "webdriver_error" in x for x in results),
 "avg_ms_success":round(statistics.mean(x["ms"] for x in success),1) if success else None,
 "sold_markers_total":sum(x.get("soldDateMarkers",0) for x in success)},ensure_ascii=False),flush=True)
