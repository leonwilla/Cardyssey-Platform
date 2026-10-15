#!/usr/bin/env python3
"""Conservative single-page price capture with provenance and review staging.

No proxy rotation, bot-challenge solving, account/session impersonation or
product-search crawling. Source URLs must be explicitly queued and supported.
The worker never writes tcg_price_cache; all results are review-only.
"""
import argparse,json,re,subprocess,time,urllib.parse,urllib.request,urllib.error,multiprocessing
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from html.parser import HTMLParser
from pathlib import Path

DOMAINS={"tcgplayer.com":"TCGPLAYER","www.tcgplayer.com":"TCGPLAYER"}
OPTIONAL_DOMAINS={"www.cardmarket.com":"CARDMARKET","www.pricecharting.com":"PRICECHARTING"}

WAIT_SECONDS=10
COOLDOWN_SECONDS=6*60*60

class MetadataParser(HTMLParser):
 def __init__(self):
  super().__init__();self.meta={};self.title=[];self.in_title=False
 def handle_starttag(self,tag,attrs):
  attr=dict(attrs)
  if tag=="title":self.in_title=True
  if tag=="meta":
   key=attr.get("property") or attr.get("name") or attr.get("itemprop")
   if key and attr.get("content"):self.meta[key.lower()]=attr["content"][:350]
 def handle_endtag(self,tag):
  if tag=="title":self.in_title=False
 def handle_data(self,data):
  if self.in_title:self.title.append(data)

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None

OPENER=urllib.request.build_opener(NoRedirect())

def get_page(url, use_cloudscraper=False):
 try:uri=urllib.parse.urlsplit(url)
 except ValueError:return "INVALID_URL",None
 allowed={**DOMAINS,**OPTIONAL_DOMAINS} if use_cloudscraper else DOMAINS
 if uri.scheme!="https" or uri.hostname not in allowed or uri.username or uri.password or uri.port:return "BLOCKED_HOST",None
 if len(url)>1500:return "INVALID_URL",None
 if use_cloudscraper:
  try:
   import cloudscraper
  except ImportError:return "CLOUDSCRAPER_NOT_INSTALLED",None
  try:
   # Explicit single-page request. Do not auto-follow off-host redirects.
   scraper=cloudscraper.create_scraper()
   response=scraper.get(url,timeout=18,allow_redirects=False,headers={"Accept":"text/html"})
   if response.status_code in (301,302,303,307,308):return "REDIRECTED_HOST",None
   if (response.headers.get("cf-mitigated") or "").lower()=="challenge":return "BOT_CHALLENGE",None
   if response.status_code in (403,429,503):return "HTTP_"+str(response.status_code),None
   if response.status_code!=200:return "HTTP_"+str(response.status_code),None
   if "html" not in response.headers.get("content-type","").lower():return "NOT_HTML",None
   parsed=MetadataParser();parsed.feed(response.text[:700000])
   title=" ".join(parsed.title).strip()[:200]
   if "just a moment" in title.lower():return "BOT_CHALLENGE",None
   return "FETCHED",dict(title=title,metadata=parsed.meta)
  except Exception:
   return "NETWORK_ERROR",None
 req=urllib.request.Request(url,headers={"User-Agent":"CardysseyPricingResearch/1.0 (contact: https://cardyssey.de)","Accept":"text/html"})
 try:
  with OPENER.open(req,timeout=13) as result:
   if urllib.parse.urlsplit(result.url).hostname not in DOMAINS:return "REDIRECTED_HOST",None
   content=result.read(700000).decode("utf-8","replace")
   if (result.headers.get("cf-mitigated") or "").lower()=="challenge":return "BOT_CHALLENGE",None
   parsed=MetadataParser();parsed.feed(content)
   title=" ".join(parsed.title).strip()[:200]
   if "just a moment" in title.lower():return "BOT_CHALLENGE",None
   return "FETCHED",dict(title=title,metadata=parsed.meta)
 except urllib.error.HTTPError as exc:return "HTTP_"+str(exc.code),None
 except (urllib.error.URLError,TimeoutError):return "NETWORK_ERROR",None

def guarded_cloudscraper_page(url, seconds=30):
 # Some challenge solvers can ignore socket timeouts. Bound the entire
 # attempt in a separate process, never blocking the queued worker.
 ctx=multiprocessing.get_context("fork")
 parent,child=ctx.Pipe(duplex=False)
 def work():
  try:child.send(get_page(url,use_cloudscraper=True))
  except BaseException:child.send(("NETWORK_ERROR",None))
  finally:child.close()
 process=ctx.Process(target=work,daemon=True)
 process.start();child.close()
 try:
  if parent.poll(seconds):
   return parent.recv()
  return "PAGE_TIMEOUT",None
 except EOFError:
  return "NETWORK_ERROR",None
 finally:
  if process.is_alive():
   process.terminate()
  process.join(timeout=2)
  if process.is_alive():process.kill();process.join(timeout=2)
  parent.close()

def analyze(page):
 if not page:return None,None
 m=page["metadata"]
 raw=next((m.get(k) for k in ("product:price:amount","og:price:amount","price") if m.get(k)),None)
 currency=next((m.get(k) for k in ("product:price:currency","pricecurrency") if m.get(k)),None)
 try:
  price=Decimal(str(raw).replace(",",".")) if raw else None
  if price is None or not price.is_finite() or price<=0 or price>1000000:price=None
 except (ValueError,InvalidOperation):price=None
 return str(price) if price else None,currency

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",type=Path,required=True,help="JSONL queue: language, card_id, variant_id, url")
 p.add_argument("--output",type=Path,required=True)
 p.add_argument("--limit",type=int,default=25)
 p.add_argument("--apply-review",action="store_true")
 p.add_argument("--cloudscraper",action="store_true",help="Opt-in protected-page diagnostic; review only")
 p.add_argument("--provider-state",type=Path,default=Path("/home/tv/.local/state/cardyssey-queue/scrape-provider-state.json"))
 args=p.parse_args()
 rows=[json.loads(x) for x in args.input.read_text().splitlines() if x.strip()][:max(0,min(args.limit,100))]
 args.provider_state.parent.mkdir(parents=True,exist_ok=True)
 try: health=json.loads(args.provider_state.read_text())
 except (FileNotFoundError,ValueError):health={}
 output=[];last_request=None;blocked_providers=set()
 allowed={**DOMAINS,**OPTIONAL_DOMAINS} if args.cloudscraper else DOMAINS
 for x in rows:
  provider=urllib.parse.urlsplit(x.get("url","")).hostname
  if provider in allowed and health.get(provider,0)>time.time():
   status,page="PROVIDER_COOLDOWN",None
  else:
   status,page=None,None
  if status is None and provider in allowed:
   delay=WAIT_SECONDS-(time.monotonic()-last_request) if last_request is not None else 0
   if delay>0:time.sleep(delay)
   last_request=time.monotonic()
  if status=="PROVIDER_COOLDOWN":pass
  elif provider in blocked_providers:
   status,page="SKIPPED_PROVIDER_BLOCKED",None
  else:
   status,page=guarded_cloudscraper_page(x.get("url","")) if args.cloudscraper else get_page(x.get("url",""))
   if status in ("BOT_CHALLENGE","HTTP_403","HTTP_429"):
    blocked_providers.add(provider)
    if provider in allowed:health[provider]=time.time()+COOLDOWN_SECONDS
  amount,currency=analyze(page)
  row={k:x.get(k) for k in ("language","card_id","variant_id","url")}
  row.update(status=status,title=(page or {}).get("title"),amount=amount,currency=currency,
   verified=False,reason="Source page/asking metadata is not an exact verified sale, condition or print",
   checked_at=datetime.now(timezone.utc).isoformat())
  output.append(row);print(row["card_id"],status,flush=True)
 args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
 tmp=args.provider_state.with_suffix(".tmp")
 tmp.write_text(json.dumps(health,indent=2)+"\n")
 tmp.replace(args.provider_state)
 if args.apply_review and output:
  payload="'"+json.dumps(output,ensure_ascii=False).replace("'","''")+"'"
  sql="""WITH inputs AS(SELECT jsonb_array_elements("""+payload+"""::jsonb) x),
 patched AS(SELECT p.language_code,p.card_id,p.variant_id,
 COALESCE((SELECT jsonb_agg(v) FROM jsonb_array_elements(p.candidates) v
 WHERE v->>'match_type'<>'PUBLIC_PAGE_PRICE_SCRAPER'),'[]'::jsonb)
 ||jsonb_build_array(jsonb_build_object('match_type','PUBLIC_PAGE_PRICE_SCRAPER',
 'source_url',inputs.x->>'url','status',inputs.x->>'status',
 'amount',inputs.x->>'amount','currency',inputs.x->>'currency',
 'title',inputs.x->>'title','verified',false,
 'checked_at',inputs.x->>'checked_at')) updated
 FROM price_review_cases p JOIN inputs ON p.language_code=inputs.x->>'language'
 AND p.card_id=inputs.x->>'card_id' AND p.variant_id=inputs.x->>'variant_id')
 UPDATE price_review_cases p SET candidates=patched.updated FROM patched
 WHERE p.language_code=patched.language_code AND p.card_id=patched.card_id AND p.variant_id=patched.variant_id"""
  subprocess.run(["docker","exec","-i","cardyssey-db","psql","-v","ON_ERROR_STOP=1",
    "-U","cardyssey","-d","cardyssey"],input=sql,text=True,check=True,stdout=subprocess.DEVNULL)
 print(json.dumps({"checked":len(output),"price_proposals":sum(x["amount"] is not None for x in output),"published":0,"review_written":args.apply_review}))
if __name__=="__main__":main()
