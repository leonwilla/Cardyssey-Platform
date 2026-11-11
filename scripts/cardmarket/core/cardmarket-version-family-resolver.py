#!/usr/bin/env python3
"""Parse Cardmarket's *observed* /Cards/.../Versions DOM into safe candidate evidence.

The real browser probe runs in a separate tab of the authenticated browser.
A version page can prove a reprint family and its set/number links, NOT the
physical foil, stamp, edition, sale price, or even product ID without opening
the corresponding product page. No automatic price publication or DB writes.
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
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

BASE = "https://www.cardmarket.com"
SINGLES = re.compile(r"^/(de|en)/Pokemon/Products/Singles/([^/]+)/([^/]+)$")
VERSIONS = re.compile(r"^/(de|en)/Pokemon/Cards/[^/]+/Versions$")
PRODUCT_ID = re.compile(r"^[0-9]{4,12}$")


def safe_url(value: str):
    try:
        u = urlsplit(value)
    except (TypeError, ValueError):
        return None
    if u.scheme != "https" or u.hostname != "www.cardmarket.com" or u.port not in (None, 443):
        return None
    if u.username or u.password:
        return None
    return u


def resolve_version_family(raw: dict, *, card_id: str, set_slug: str,
                           collector_suffix: str, observations: list[dict] = (),
                           catalog: dict | None = None,
                           additional_print_groups: list[dict] = ()) -> dict:
    page = safe_url(raw.get("href", ""))
    if not page or not VERSIONS.fullmatch(page.path):
        raise ValueError("A verified Cardmarket Cards/.../Versions page is required")
    if raw.get("challenge") or raw.get("ready") != "complete":
        raise ValueError("Browser challenge/incomplete page: refuse candidate extraction")
    if not re.fullmatch(r"[A-Za-z0-9-]{2,90}", set_slug):
        raise ValueError("Unsafe set slug")
    if not re.fullmatch(r"[A-Za-z0-9-]{2,32}", collector_suffix):
        raise ValueError("Unsafe collector code")
    groups = [(set_slug, collector_suffix)]
    for group in additional_print_groups:
        gs, gn = str(group.get('setSlug', '')), str(group.get('collectorSuffix', ''))
        if not re.fullmatch(r"[A-Za-z0-9-]{2,90}", gs) or not re.fullmatch(r"[A-Za-z0-9-]{2,32}", gn):
            raise ValueError("Unsafe additional group")
        groups.append((gs, gn))
    expected_path = "/" + page.path.strip("/").split("/")[0] + "/Pokemon/Products/Singles/"
    seen = set()
    all_versions, matched = [], []
    for item in raw.get("anchors", []):
        link = safe_url(item.get("url", ""))
        if not link:
            continue
        m = SINGLES.fullmatch(link.path)
        if not m or (expected_path + m.group(2) + "/" + m.group(3)) != link.path:
            continue
        if link.path in seen:
            continue
        seen.add(link.path)
        product_slug = m.group(3)
        version = re.search(r"(?:^|-)V([1-9][0-9]?)(?:-|$)", product_slug, re.I)
        record = {
            "productUrl": BASE + link.path,
            "setSlug": m.group(2),
            "productSlug": product_slug,
            "version": "V" + version.group(1) if version else None,
            "versionLabel": str(item.get("text", ""))[:160],
            "productId": None,
            "productIdChecked": False,
            "exactPrintVerified": False,
            "priceVerified": False,
        }
        all_versions.append(record)
        if any(m.group(2) == gs and product_slug.upper().endswith("-" + gn.upper()) for gs, gn in groups):
            matched.append(record)
    if not all_versions:
        raise ValueError("No Cardmarket version links visible")
    # A live product-page observation (matching path AND official catalog metadata)
    # is required before recording the exact idProduct. Never guess by V1/V2.
    observations_by_path = {}
    for o in observations:
        u = safe_url(o.get("url", ""))
        pid = str(o.get("id", ""))
        if not u or not SINGLES.fullmatch(u.path) or not PRODUCT_ID.fullmatch(pid):
            continue
        source = next((im.get("src") for im in o.get("imgs", [])
                       if str(im.get("src", "")).startswith("https://product-images.s3.cardmarket.com/")
                       and str(im.get("src", "")).endswith("/" + pid + "/" + pid + ".jpg")), None)
        observations_by_path[u.path] = (pid, source)
    for entry in matched:
        path = urlsplit(entry["productUrl"]).path
        verified = observations_by_path.get(path)
        if verified:
            pid, source_image = verified
            metadata = (catalog or {}).get(pid)
            if catalog is not None and (not metadata or not metadata.get("idExpansion")):
                continue
            entry["productId"] = pid
            entry["productIdChecked"] = True
            if source_image:
                entry["imageUrl"] = source_image
            if metadata:
                entry["expansionId"] = str(metadata["idExpansion"])
                entry["metacardId"] = str(metadata.get("idMetacard", ""))
    # A version family is a candidate set only. Different sets using the same
    # artwork/attacks must not be assigned to this card.
    return {
        "cardId": card_id,
        "versionPageUrl": BASE + page.path,
        "pageHeading": str(raw.get("heading", ""))[:180],
        "totalVersionsObserved": len(all_versions),
        "otherSetVersionsExcluded": len(all_versions) - len(matched),
        "sameSetCardNumberCandidates": matched,
        "candidateCount": len(matched),
        "allCandidatesHaveCheckedProductId": bool(matched) and all(x["productIdChecked"] for x in matched),
        "exactPrintVerified": False,
        "safeToAutoPrice": False,
        "status": "VERSION_FAMILY_PRINT_UNVERIFIED" if matched else "NO_SAME_SET_NUMBER_CANDIDATE",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case-file", required=True, help="JSON case with versionsFile, productsFiles, setSlug, collectorSuffix, cardId")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    case = json.loads(Path(a.case_file).read_text(encoding="utf-8-sig"))
    raw = json.loads(Path(case["versionsFile"]).read_text(encoding="utf-8-sig"))
    observations = [json.loads(Path(name).read_text(encoding="utf-8-sig")) for name in case.get("productsFiles", [])]
    catalog = None
    if case.get("catalogFile"):
        feed = json.loads(Path(case["catalogFile"]).read_text(encoding="utf-8-sig"))
        catalog = {str(x["idProduct"]): x for x in feed["products"]}
    result = resolve_version_family(raw, card_id=case["cardId"], set_slug=case["setSlug"],
        collector_suffix=case["collectorSuffix"], observations=observations, catalog=catalog,
        additional_print_groups=case.get("additionalPrintGroups", []))
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"cardId": result["cardId"], "familyVersions": result["totalVersionsObserved"],
        "matched": result["candidateCount"], "allIdChecked": result["allCandidatesHaveCheckedProductId"],
        "status": result["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
