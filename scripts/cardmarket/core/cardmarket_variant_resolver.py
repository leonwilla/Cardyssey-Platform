#!/usr/bin/env python3
"""Conservative Cardmarket print resolution and language-specific offer pricing.

Input must come from an independently verified Cardmarket product-page / catalog
record. An image hash, V1/V2, a high price, or an unlabelled JP reverse does
NOT independently identify a print. This module NEVER writes price caches.
No external dependencies; optional Pillow/imagehash support is diagnostic.
"""
from __future__ import annotations
# Import helper modules from the repository scripts root and Cardmarket tree.
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_root=_cm_Path(__file__).resolve().parents[2]
for _cm_import in (_cm_root, _cm_root/'cardmarket/core', _cm_root/'cardmarket/admin', _cm_root/'cardmarket/archive'):
    if str(_cm_import) not in _cm_sys.path:
        _cm_sys.path.insert(0,str(_cm_import))
import argparse
import dataclasses
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import Counter
from dataclasses import dataclass, field
import io
import json
import re
import statistics
from pathlib import Path
from urllib.parse import urlsplit

PRINTS={"normal","reverse","pokeball","masterball","stamp","holo","cosmos","unknown"}
LANGUAGES={"de","en","ja","ko","zh-cn","zh-tw"}
CONDITIONS={"NM","MT","NEAR MINT","MINT"}
# Python and Windows PowerShell read the SAME comment rules. Avoid drifting
# classifications between the live browser and the offline median diagnostic.
COMMENT_RULES_PATH=Path(__file__).resolve().parents[3]/'config/cardmarket-comment-rules.json'
COMMENT_RULES=json.loads(COMMENT_RULES_PATH.read_text(encoding='utf-8'))
if COMMENT_RULES.get('schema')!=1 or COMMENT_RULES.get('source')!='CARDYSSEY_DIAGNOSTIC_ONLY':
    raise ValueError('Unsupported Cardmarket comment-rules schema')
BALL_PATTERNS={k:re.compile(v) for k,v in COMMENT_RULES['explicit'].items()}
SHORT_PATTERNS={k:re.compile(v) for k,v in COMMENT_RULES['shorthand'].items()}
NEGATED_BALL=re.compile(COMMENT_RULES['negation'])
NEGATIONS=re.compile(r"(?i)(?:\b(?:no|not|kein(?:e|en|er|es)?|ohne|non|nicht|sin|sans)\b|\b(?:wrong|falsch)\b)")
STAMP_WORDS={k:re.compile(v) for k,v in COMMENT_RULES['stamps'].items()}

def labels(text:str)->set[str]:
    text=str(text or "")
    out={key for key,rx in BALL_PATTERNS.items() if rx.search(text)}
    out|={key for key,rx in STAMP_WORDS.items() if rx.search(text)}
    return out

def classified_comment(comment:str, target:str)->str:
    """'positive', 'contradiction', 'missing', 'ambiguous'.

    An absent comment never proves a special print, even in JP 151.
    Bare PB/MB abbreviations are deliberately NOT accepted as evidence.
    """
    target=str(target or "").casefold()
    found=labels(comment)
    if not comment or not comment.strip():return "missing"
    if NEGATED_BALL.search(comment):return "ambiguous"
    if target in {"pokeball","masterball"}:
        other={"pokeball","masterball"}-{target}
        short_found={key for key,rx in SHORT_PATTERNS.items() if rx.search(comment)}
        if (found|short_found)&other:return "contradiction"
        if target in found:return "positive"
        # MB/PB is useful supporting evidence but isn't an unambiguous
        # product/foil identity. Permit it in prices only for an independently
        # confirmed print, never to certify an unknown printing.
        if target in short_found:return "shorthand_hint"
        return "missing"
    if target.startswith("stamp:"):
        stamp=target.partition(":")[2]
        if stamp in found and not NEGATIONS.search(comment):return "positive"
        return "missing"
    return "not_applicable"

@dataclass(frozen=True)
class Product:
    product_id:str
    set_slug:str
    product_url:str
    number:str
    name:str=""
    title:str=""
    version:str=""
    price_trend:float|None=None
    image_url:str|None=None
    confirmed_product_page:bool=False
    official_expansion_id:str|None=None

@dataclass
class Decision:
    product_id:str
    print_type:str="unknown"
    confidence:str="LOW"
    evidence:list[str]=field(default_factory=list)
    review_required:bool=True
    safe_to_publish_price:bool=False
    # HIGH refers to identity only; price requires independent offer validation

def valid_product_url(u:str)->bool:
    try:x=urlsplit(u)
    except (TypeError,ValueError):return False
    return bool(x.scheme=="https" and x.hostname=="www.cardmarket.com" and
      x.port in (None,443) and not x.username and not x.password and
      re.fullmatch(r"/(?:de|en)/Pokemon/Products/Singles/[A-Za-z0-9-]+/[A-Za-z0-9-]+",x.path))

def classify_product(product:Product,*,valid_set_slugs:set[str],
                     matched_number:str, confirmed_print_evidence:str|None=None,
                     foil_image_evidence:dict|None=None)->Decision:
    """Classify a page only if set+number were independently validated.

    A high-cost product is not evidence of a Master Ball. A generic phash
    cannot distinguish shared artwork with different foil; image proof must
    explicitly be 'human_verified' and identify the printed feature.
    """
    result=Decision(product_id=str(product.product_id))
    if not product.confirmed_product_page or not valid_product_url(product.product_url):
        result.evidence.append("PRODUCT_PAGE_NOT_VERIFIED");return result
    if product.set_slug not in valid_set_slugs or not valid_set_slugs:
        result.evidence.append("SET_NOT_VERIFIED");return result
    a=re.search(r"0*(\d+)$",str(product.number))
    b=re.search(r"0*(\d+)$",str(matched_number))
    if not a or not b or a.group(1)!=b.group(1):
        result.evidence.append("NUMBER_MISMATCH");return result
    result.evidence+=["SET_VERIFIED","COLLECTOR_NUMBER_VERIFIED","PRODUCT_PAGE_VERIFIED"]
    # A Trainer card can itself be named "Master Ball". Only a structured
    # provider version/print field, not the card name/title, is foil evidence.
    explicit=labels(product.version)
    if "masterball" in explicit and "pokeball" in explicit:
        result.evidence.append("CONFLICTING_PRINT_LABELS");return result
    if "masterball" in explicit or "pokeball" in explicit:
        result.print_type="masterball" if "masterball" in explicit else "pokeball"
        result.confidence="HIGH"
        result.evidence.append("EXPLICIT_PROVIDER_PRINT_LABEL")
        result.review_required=False
        return result
    if confirmed_print_evidence in PRINTS-{"unknown"}:
        # Human/manual evidence must be supplied by a verified review action,
        # not by untrusted comments or price heuristics.
        result.print_type=confirmed_print_evidence
        result.confidence="HIGH";result.review_required=False
        result.evidence.append("HUMAN_CONFIRMED_PRINT")
        return result
    if foil_image_evidence:
        if (foil_image_evidence.get("method")=="human_verified_roi"
                and foil_image_evidence.get("subjectProductId")==str(product.product_id)
                and foil_image_evidence.get("print") in PRINTS-{"unknown"}
                and foil_image_evidence.get("reviewer")):
            result.print_type=foil_image_evidence["print"]
            result.confidence="HIGH";result.review_required=False
            result.evidence.append("HUMAN_VERIFIED_FOIL_REGION")
            return result
        result.evidence.append("IMAGE_SIMILARITY_ONLY_NOT_FOIL_PROOF")
    result.evidence.append("V1_V2_OR_PRICE_NOT_PRINT_PROOF")
    return result

def phash_distance(a:bytes,b:bytes)->int|None:
    """Optional diagnostic; near-equal artwork != equal foil."""
    try:
        from PIL import Image
        import imagehash
        x=imagehash.phash(Image.open(io.BytesIO(a)).convert("RGB"))
        y=imagehash.phash(Image.open(io.BytesIO(b)).convert("RGB"))
        return int(x-y)
    except (ImportError,OSError,ValueError,TypeError):
        return None

def price_hint(products:list[Product])->dict:
    """Trend-price only ranks candidates for manual review; never maps prints."""
    valid=sorted([p for p in products if p.price_trend and p.price_trend>0],
                 key=lambda p:p.price_trend or 0)
    ratio=(valid[-1].price_trend/valid[0].price_trend) if len(valid)==2 else None
    return {"orderedProductIds":[p.product_id for p in valid],
            "priceRatio":round(ratio,2) if ratio else None,
            "reviewSuggestion":"CHEAPER_POKEBALL_MORE_EXPENSIVE_MASTERBALL_POSSIBLE" if ratio and ratio>=2.5 else None,
            "printVerified":False,"safeToAutoPublish":False}

def parse_money(value)->Decimal:
    if isinstance(value,bool):raise ValueError("price")
    if isinstance(value,str):
        value=value.replace("€","").replace("\u00a0","").replace(" ","").strip()
        if not re.fullmatch(r"[0-9.,]+",value):raise ValueError("price")
        if "," in value and "." in value:
            value=value.replace(".","").replace(",",".") if value.rfind(",")>value.rfind(".") else value.replace(",","")
        elif "," in value:value=value.replace(",",".")
    try:amount=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError):raise ValueError("price")
    if not amount.is_finite() or amount<=0:raise ValueError("price")
    return amount

def percentile(values:list[Decimal],p:Decimal)->Decimal:
    values=sorted(values)
    i=Decimal(len(values)-1)*p
    low=int(i)
    return values[low]+(values[min(low+1,len(values)-1)]-values[low])*(i-Decimal(low))

def price_diagnostic(data:dict)->dict:
    """Read-only robust asking median; requires complete list for certification.

    Same idProduct, language, condition, special print positive comments where
    required, reverse/edition flags, no duplicates. IQR only with >=8 offers.
    No automatic cross-language conversion or price-feed publication.
    """
    exp=data.get("expected") or {}
    target=str(exp.get("print") or "").casefold()
    lang=exp.get("language")
    pid=str(exp.get("product_id") or "")
    if lang not in LANGUAGES or target not in PRINTS-{"unknown"} or not pid.isdigit():
        raise ValueError("language, print and numeric product_id required")
    rows=data.get("offers")
    if not isinstance(rows,list):raise ValueError("offers must be list")
    accepted=[];excluded=Counter();seen=set()
    for row in rows:
        if not isinstance(row,dict):
            excluded["INVALID_ROW"]+=1;continue
        oid=str(row.get("offer_id") or "")
        if not oid or oid in seen:
            excluded["DUPLICATE_OR_MISSING_OFFER_ID"]+=1;continue
        seen.add(oid)
        if str(row.get("product_id"))!=pid:
            excluded["WRONG_PRODUCT"]+=1;continue
        if row.get("language")!=lang:
            excluded["WRONG_LANGUAGE"]+=1;continue
        if str(row.get("condition") or "").upper() not in CONDITIONS:
            excluded["NOT_NM_OR_BETTER"]+=1;continue
        if row.get("signed") is not False or row.get("altered") is not False or row.get("graded") is not False:
            excluded["MODIFIED_OR_UNVERIFIED"]+=1;continue
        if row.get("bundle") is not False:
            excluded["BUNDLE_OR_UNVERIFIED"]+=1;continue
        reverse=row.get("is_reverse")
        if not isinstance(reverse,bool):
            excluded["UNKNOWN_REVERSE_FLAG"]+=1;continue
        if target=="normal" and reverse or target=="reverse" and not reverse:
            excluded["WRONG_REVERSE_FLAG"]+=1;continue
        if target in {"pokeball","masterball"}:
            comment_status=classified_comment(row.get("comment") or "",target)
            if comment_status!="positive" and not (
                    comment_status=="shorthand_hint" and
                    exp.get("confirmed_print_identity") is True):
                excluded["PRINT_COMMENT_"+comment_status.upper()]+=1;continue
            if lang=="ja" and not reverse:
                excluded["JAPANESE_SPECIAL_REQUIRES_REVERSE"]+=1;continue
        if target=="stamp" and not (exp.get("confirmed_print_identity") is True):
            excluded["STAMP_TYPE_UNVERIFIED"]+=1;continue
        try:accepted.append(parse_money(row["price_eur"]))
        except (KeyError,ValueError):excluded["INVALID_PRICE"]+=1
    complete_info=data.get("pagination") or {}
    all_complete=(complete_info.get("all_pages_fetched") is True
                  and complete_info.get("capped") is False
                  and isinstance(complete_info.get("total_offers"),int)
                  and complete_info["total_offers"]==len(seen)
                  and excluded["DUPLICATE_OR_MISSING_OFFER_ID"]==0)
    med=statistics.median(accepted) if accepted else None
    cleaned=list(accepted)
    outlier_count=0
    if len(cleaned)>=8:
        q1=percentile(cleaned,Decimal("0.25"))
        q3=percentile(cleaned,Decimal("0.75"))
        iqr=q3-q1
        if iqr>0:
            low=q1-Decimal("1.5")*iqr
            high=q3+Decimal("1.5")*iqr
            cleaned=[x for x in cleaned if low<=x<=high]
            outlier_count=len(accepted)-len(cleaned)
    cleaned_median=statistics.median(cleaned) if cleaned else None
    trend=data.get("product_wide_trend")
    ratio=None
    try:
        tr=parse_money(trend)
        if cleaned_median is not None:ratio=float(cleaned_median/tr)
    except ValueError:pass
    result={
       "basis":"ACTIVE_ASKING_NOT_SOLD",
       "language":lang,"product_id":pid,"print":target,
       "total_rows":len(rows),"unique_offers":len(seen),
       "accepted_offers":len(accepted),"rejected":dict(excluded),
       "all_pages_complete":all_complete,"iqr_removed":outlier_count,
       "median_all_accepted_eur":str(med.quantize(Decimal(".01"),rounding=ROUND_HALF_UP)) if med else None,
       "median_iqr_diagnostic_eur":str(cleaned_median.quantize(Decimal(".01"),rounding=ROUND_HALF_UP)) if cleaned_median else None,
       "product_guide_ratio":round(ratio,2) if ratio is not None else None,
       "guide_outlier_warning":ratio is not None and (ratio<0.5 or ratio>2),
       "exact_print_verified":exp.get("confirmed_print_identity") is True,
       "safe_to_publish":bool(all_complete and accepted and exp.get("confirmed_print_identity") is True
          and not excluded["PRINT_COMMENT_AMBIGUOUS"]
          and (target not in {"pokeball","masterball"} or all_complete)),
    }
    return result

def main():
    a=argparse.ArgumentParser()
    a.add_argument("input",type=Path)
    a.add_argument("--output",type=Path)
    args=a.parse_args()
    data=json.loads(args.input.read_text(encoding="utf-8-sig"))
    if data.get("operation")=="price":result=price_diagnostic(data)
    else:
        p=Product(**data["product"])
        d=classify_product(p,valid_set_slugs=set(data.get("verified_set_slugs",[])),
            matched_number=data["card_number"],confirmed_print_evidence=data.get("manual_print"),
            foil_image_evidence=data.get("foil_image_evidence"))
        result=dataclasses.asdict(d)
    rendered=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:args.output.write_text(rendered,encoding="utf-8")
    print(rendered,end="")
if __name__=="__main__":main()
