#!/usr/bin/env python3
"""Stage complete Cardyssey card catalog as unpublished WooCommerce products.

DRY RUN by default. Requires CARDYSSEY_API_URL, CARDYSSEY_ADMIN_TOKEN,
CARDYSSEY_WC_URL, CARDYSSEY_WC_CONSUMER_KEY and CARDYSSEY_WC_CONSUMER_SECRET.
Run with --apply only after database backup, image rights review and pilot test.

This intentionally imports one draft per card/printed language only.
Commercial variants/conditions are created separately from verified stock
through the admin editor; guessing foil/condition would be incorrect.
"""
import argparse
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

def request_json(url, headers=None, data=None, method="GET"):
    body = json.dumps(data).encode() if data is not None else None
    headers = dict(headers or {})
    if body is not None: headers["Content-Type"]="application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--language", default="de",choices=["de","en","ja","ko","zh-cn","zh-tw"])
    ap.add_argument("--limit",type=int,default=0,help="Max new cards to process, 0=all")
    ap.add_argument("--checkpoint",default="shop-catalog-import-checkpoint.json")
    args=ap.parse_args()
    backend=os.getenv("CARDYSSEY_API_URL","http://127.0.0.1:8081").rstrip("/")
    token=os.getenv("CARDYSSEY_ADMIN_TOKEN","")
    wc=os.getenv("CARDYSSEY_WC_URL","https://shop.cardyssey.de").rstrip("/")
    key=os.getenv("CARDYSSEY_WC_CONSUMER_KEY","")
    secret=os.getenv("CARDYSSEY_WC_CONSUMER_SECRET","")
    if not token:sys.exit("CARDYSSEY_ADMIN_TOKEN missing")
    if args.apply and (not key or not secret or not wc.startswith("https://")):sys.exit("WC credentials / HTTPS missing")
    baseheaders={"Authorization":"Bearer "+token}
    wcauth={}
    if args.apply:
        import base64
        pair=base64.b64encode((key+":"+secret).encode()).decode()
        wcauth={"Authorization":"Basic "+pair}
    def api(path):
        return request_json(backend+path,baseheaders)
    def wcapi(path,data=None,method="GET"):
        return request_json(wc+"/wp-json/wc/v3/"+path,wcauth,data,method)
    sets=api("/api/v1/sets?language="+args.language)
    if not isinstance(sets,list):sys.exit("Unexpected set catalog response")
    checkpoint=pathlib.Path(args.checkpoint)
    done=set()
    if checkpoint.exists():
        old=json.loads(checkpoint.read_text())
        done=set(old.get("completed",[]))
    def persist():
        checkpoint.write_text(json.dumps({"completed":sorted(done)},indent=2))
    roots={}
    categories={}
    def cat(name,parent):
        ident=(parent,name)
        if ident in categories:return categories[ident]
        if not args.apply:return 0
        found=wcapi("products/categories?per_page=100&search="+urllib.parse.quote(name))
        match=next((c for c in found if c.get("name")==name and c.get("parent",0)==parent),None)
        result=match or wcapi("products/categories",{"name":name,"parent":parent},"POST")
        categories[ident]=result["id"]
        return result["id"]
    root=cat("Einzelkarten",0)
    for name in ("Booster","Displays","Elite Trainer Boxen","Kollektionen & Boxen","Zubehör"):
        cat(name,0)
    count=0
    for record in sets:
        set_id=record.get("id")
        set_name=record.get("name")
        if not isinstance(set_id,str) or not isinstance(set_name,str):continue
        detail=api("/api/v1/sets/"+urllib.parse.quote(set_id,safe="")+"?language="+args.language)
        if not isinstance(detail,dict) or not isinstance(detail.get("cards"),list):continue
        set_category=cat(set_name,root)
        for card in detail["cards"]:
            card_id=card.get("id")
            if not isinstance(card_id,str) or not card.get("name"):continue
            unique="|".join((args.language,set_id,card_id))
            if unique in done:continue
            if args.limit and count>=args.limit:
                print("Reached limit",count)
                return
            print("STAGE",unique,card.get("name"),flush=True)
            if args.apply:
                sku="CDY-CATALOG-"+str(len(unique))+"-"+__import__("hashlib").sha256(unique.encode()).hexdigest()[:28].upper()
                lookup=wcapi("products?sku="+urllib.parse.quote(sku)+"&per_page=2")
                if len(lookup)>1:raise RuntimeError("Ambiguous SKU: "+sku)
                if not lookup:
                    # No reference image in bulk by default: rights and reachable URL must be verified.
                    payload={"type":"simple","name":card["name"]+" · "+str(card.get("localId",""))+" · "+set_name,
                             "sku":sku,"status":"draft","catalog_visibility":"hidden","manage_stock":True,
                             "stock_quantity":0,"stock_status":"outofstock","backorders":"no",
                             "description":"Katalogeintrag. Aktuell nicht zum Verkauf verfügbar.",
                             "categories":[{"id":set_category}] if set_category else [],
                             "meta_data":[{"key":"_cardyssey_card_id","value":card_id},
                                          {"key":"_cardyssey_set_id","value":set_id},
                                          {"key":"_cardyssey_language","value":args.language}]}
                    wcapi("products",payload,"POST")
                    time.sleep(0.15)
                done.add(unique)
                persist()
            count+=1
    print("Finished staged cards",count,"apply=",args.apply)

if __name__=="__main__":
    try:main()
    except (urllib.error.HTTPError,urllib.error.URLError) as exc:
        sys.exit("Remote API failed: "+str(exc))
