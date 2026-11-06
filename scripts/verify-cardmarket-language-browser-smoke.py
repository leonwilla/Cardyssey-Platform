#!/usr/bin/env python3
"""Validate the DE/EN Cardmarket browser smoke-test. No price cache writes.

A correct product URL and checkbox are not enough: every sampled offer must
explicitly display the requested language and at least Near Mint.
The metric is the median of the five lowest *asking* prices, not a sold price.
"""
import argparse
import json
import re
import statistics
from decimal import Decimal
from pathlib import Path

DEFAULT=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector/language-nm-three-cards-result.json")
REPORT=Path("/home/tv/cardshop/reports/cardmarket-language-smoke-results.json")
LANGS={"de":("3","Deutsch"),"en":("1","Englisch")}

def euros(text):
    m=re.search(r"\d[\d., ]*",str(text or ""))
    if not m:raise ValueError("missing offer price")
    raw=m.group().strip().replace(" ","")
    if "." in raw and "," in raw:
        if raw.rfind(",")>raw.rfind("."):raw=raw.replace(".","").replace(",",".")
        else:raw=raw.replace(",","")
    elif "," in raw:
        if re.search(r",\d{1,2}$",raw):raw=raw.replace(",",".")
        else:raw=raw.replace(",","")
    elif "." in raw and re.fullmatch(r"\d{1,3}(?:\.\d{3})+",raw):
        raw=raw.replace(".","")
    amount=Decimal(raw)
    if not amount.is_finite() or amount<=0:raise ValueError("invalid offer price")
    return amount

def check(rows):
    entries={}
    for row in rows:
        if "data" not in row:raise ValueError("browser probe failed")
        data=row["data"]
        language=row["lang"]
        if language not in LANGS:raise ValueError("unexpected language")
        code,display=LANGS[language]
        if data.get("checked")!=[f"language[{code}]"]:
            raise ValueError("mixed or missing language checkbox")
        if str(data.get("condition"))!="2":
            raise ValueError("wrong condition filter")
        from urllib.parse import urlsplit,parse_qs
        query=parse_qs(urlsplit(data.get("url","")).query)
        if query.get("language")!=[code] or query.get("minCondition")!=["2"]:
            raise ValueError("filtered URL not committed")
        pid=str(data.get("productId") or "")
        if not pid.isdigit():raise ValueError("no actual product id")
        samples=data.get("offers") or []
        if len(samples)<5:raise ValueError("too few verified rows")
        five=[]
        for offer in samples:
            if display not in offer.get("labels",[]):
                raise ValueError(f"offer language mismatch for {language}")
            if offer.get("condition") not in ("Mint","Near Mint"):
                raise ValueError("offer worse than NM")
            five.append(euros(offer.get("price")))
        five=sorted(five)[:5]
        key=(row["card"],language)
        if key in entries:raise ValueError("duplicate card-language")
        entries[key]={"card":row["card"],"language":language,"product_id":pid,
            "visible_offers":int(data.get("rows",0)),"verified_sample_rows":len(samples),
            "lowest_ask_eur":str(five[0].quantize(Decimal("0.01"))),
            "entry_five_median_eur":str(statistics.median(five).quantize(Decimal("0.01"))),
            "basis":"active_asking_5_lowest_visible_offers_NOT_SOLD_OR_NM_ONLY",
            "printing_verified":False,"market_wide":False}
    cards={c for c,_ in entries}
    for card in cards:
        if (card,"de") not in entries or (card,"en") not in entries:
            raise ValueError("missing language")
        if entries[(card,"de")]["product_id"]!=entries[(card,"en")]["product_id"]:
            raise ValueError("different product IDs for language pair")
    return sorted(entries.values(),key=lambda x:(x["card"],x["language"]))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=DEFAULT)
    p.add_argument("--report",type=Path,default=REPORT)
    args=p.parse_args()
    result=check(json.loads(args.input.read_text(encoding="utf-8-sig")))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
