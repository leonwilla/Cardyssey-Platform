#!/usr/bin/env python3
"""Median of ALL eligible Cardmarket asking offers, not the cheapest subset.

Fail closed on incomplete pages or print/language mismatches. One listing counts
once regardless of its quantity; quantity-weighted median is diagnostic only.
Never writes collection/price cache.
"""
import argparse
import json
import re
import statistics
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

VALID_LANGUAGE={"de","en"}
VALID_CONDITION={"NM","MT","NEAR MINT","MINT"}
def money(value):
    if isinstance(value,(int,float,Decimal)):
        v=Decimal(str(value))
    elif isinstance(value,str):
        s=value.strip().replace("€","").replace(" ","")
        if not re.fullmatch(r"[0-9.,]+",s):raise ValueError("invalid price text")
        if "." in s and "," in s:
            s=s.replace(".","").replace(",",".") if s.rfind(",")>s.rfind(".") else s.replace(",","")
        elif "," in s:s=s.replace(",",".")
        elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+",s):s=s.replace(".","")
        v=Decimal(s)
    else:raise ValueError("invalid price type")
    if not v.is_finite() or v<=0:raise ValueError("nonpositive price")
    return v
def median_eur(values):
    return str(statistics.median(values).quantize(Decimal("0.01")))
def evaluate(data):
    expected=data.get("expected") or {}
    lang=expected.get("language")
    pid=str(expected.get("product_id") or "")
    if lang not in VALID_LANGUAGE or not pid.isdigit():
        raise ValueError("expected product ID and de/en required")
    finish=expected.get("finish")
    edition=expected.get("edition")
    if finish not in ("normal","holo","reverse","cosmos"):
        raise ValueError("explicit finish required")
    if edition not in ("unlimited","first_edition","other"):
        raise ValueError("explicit edition required")
    rows=data.get("offers")
    if not isinstance(rows,list):raise ValueError("offers list required")
    prices=[];weighted=[];seen=set();reject=Counter()
    for row in rows:
        if not isinstance(row,dict):reject["invalid_row"]+=1;continue
        id=str(row.get("offer_id") or "").strip()
        if not id or id in seen:reject["duplicate_or_missing_id"]+=1;continue
        seen.add(id)
        if str(row.get("product_id"))!=pid:reject["product"]+=1;continue
        if row.get("language")!=lang:reject["language"]+=1;continue
        if str(row.get("condition") or "").upper() not in VALID_CONDITION:reject["condition"]+=1;continue
        if row.get("finish")!=finish:reject["finish"]+=1;continue
        if row.get("edition")!=edition:reject["edition"]+=1;continue
        if row.get("signed") is not False or row.get("altered") is not False or row.get("graded") is not False:
            reject["modified_or_unverified"]+=1;continue
        if row.get("bundle") is not False:reject["bundle_or_unverified"]+=1;continue
        try:
            price=money(row.get("price_eur"))
            qty=row.get("quantity")
            if type(qty) is not int or qty<1:raise ValueError("missing quantity")
        except (InvalidOperation,ValueError,TypeError):
            reject["price_or_quantity"]+=1;continue
        prices.append(price)
        if len(weighted)+qty<=100000:weighted.extend([price]*qty)
    pages=data.get("pagination") or {}
    count=pages.get("total_offers")
    complete=(
        pages.get("all_pages_fetched") is True and pages.get("capped") is False
        and type(count) is int and count==len(seen)
        and reject["duplicate_or_missing_id"]==0
    )
    result={"product_id":pid,"language":lang,"finish":finish,"edition":edition,
        "listed_offers":len(seen),"accepted_offers":len(prices),
        "reject_reasons":dict(reject),
        "median_all_offers_eur":median_eur(prices) if prices else None,
        "median_quantity_weighted_eur":median_eur(weighted) if weighted else None,
        "all_pages_complete":complete,
        "status":"COMPLETE_ASKING_MEDIAN" if prices and complete else
            "PARTIAL_ASKING_MEDIAN" if prices else "NO_MATCHING_OFFERS",
        "price_basis":"ACTIVE_ASKING_NOT_SOLD",
        "can_publish_print_price":bool(prices and complete and not reject and
           data.get("print_identity_independently_verified") is True)}
    return result
def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=evaluate(json.loads(a.input.read_text(encoding="utf-8-sig")))
    out=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if a.output:a.output.write_text(out,encoding="utf-8")
    print(out,end="")
if __name__=="__main__":main()
