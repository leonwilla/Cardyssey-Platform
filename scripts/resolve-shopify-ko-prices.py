#!/usr/bin/env python3
"""Exact Korean NM ordinary-print offers from verified public Shopify retailers.

Discover only public singles feeds, verify variant-specific structured EUR offers,
and cross-check official Korean identities with independent species names.
No JavaScript is executed; preview by default. Separate reports per shop.
"""
import argparse
import concurrent.futures
import importlib.util
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

spec = importlib.util.spec_from_file_location("ko", Path(__file__).with_name("resolve-uturi-ko-prices.py"))
ko = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ko)
SHOPS = {
    "nero": dict(host="https://nerocards.de", prefix="", collection="pok-mon-single", source="WEB_NERO_KO"),
    "anvil": dict(host="https://cardanvil.sk", prefix="", collection="pok-mon-single", source="WEB_CARDANVIL_KO"),
    "lake": dict(host="https://lakecards.de", prefix="/en", collection="pok-mon-single", source="WEB_LAKE_KO"),
    "mana": dict(host="https://manamarket.eu", prefix="", collection="pokemon-singles", source="WEB_MANA_KO"),
}
TITLE = re.compile(r"^(.+) - .+ \(([^()]+)\) \[([A-Za-z0-9]+)-(\d+)\]$")
RARITIES = {"Common": "C", "Uncommon": "U", "Rare": "R", "Double Rare": "RR",
            "Illustration Rare": "AR", "Special Illustration Rare": "SAR", "Ultra Rare": "SR",
            "Secret Rare": "SR", "Character Rare": "CHR"}


def get_text(url):
    time.sleep(0.6)
    with urllib.request.urlopen(urllib.request.Request(url, headers={
        "User-Agent": "Cardyssey/0.4 exact-public-price-audit",
    }), timeout=12) as response:
        return response.read().decode("utf-8")


def get_json(url):
    return json.loads(get_text(url))


def collection(shop):
    products, seen = [], set()
    deadline = time.monotonic() + 130
    for page in range(1, 81):
        if time.monotonic() > deadline:
            raise TimeoutError("singles collection deadline")
        url = shop["host"] + shop["prefix"] + "/collections/" + shop["collection"] + "/products.json?"
        batch = get_json(url + urllib.parse.urlencode(dict(limit=250, page=page))).get("products")
        if not isinstance(batch, list):
            raise ValueError("invalid singles feed")
        for p in batch:
            if p.get("id") in seen or type(p.get("id")) is not int:
                raise ValueError("duplicate/missing product identity")
            seen.add(p["id"])
        products.extend(batch)
        if len(batch) < 250:
            return products
    raise ValueError("singles pagination limit")


def korean_variant(product):
    options = product.get("options") or []
    if [o.get("position") for o in options] != [1, 2, 3]:
        return None
    if options[0].get("name") not in ("Language", "Sprache") or options[1].get("name") not in ("Condition", "Zustand") or options[2].get("name") != "Edition":
        return None
    matches = [v for v in product.get("variants", []) if v.get("option1") in ("Korean", "Koreanisch")
               and v.get("option2") == "Near Mint" and v.get("option3") in ("Normal", "Regulär")]
    return matches[0] if len(matches) == 1 else None


def structured_product(text, detail=None):
    products = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', text, re.S):
        data = json.loads(block)
        if isinstance(data, dict) and data.get("@type") in ("Product", "ProductGroup"):
            products.append(data)
    if len(products) != 1:
        raise ValueError("ambiguous product structured data")
    product = dict(products[0])
    if product.get("@type") == "ProductGroup":
        if (detail is None or product.get("productGroupID") != str(detail.get("id"))
                or product.get("name") != detail.get("title") or not isinstance(product.get("hasVariant"), list)):
            raise ValueError("product group identity mismatch")
        variants = {v["id"]: v for v in detail.get("variants", [])}
        offers = []
        for child in product["hasVariant"]:
            offer = child.get("offers")
            if child.get("@type") != "Product" or not isinstance(offer, dict):
                raise ValueError("invalid product group offer")
            m = re.fullmatch(re.escape(product["url"]) + r"\?variant=(\d+)", offer.get("url", ""))
            variant = variants.get(int(m[1])) if m else None
            if (variant is None or not child.get("sku") or child["sku"] != variant.get("sku")
                    or child.get("name") != detail["title"] + " - " + variant["title"]):
                raise ValueError("product group variant mismatch")
            offers.append(dict(offer, sku=child["sku"]))
        product["offers"] = offers
    elif isinstance(product.get("offers"), dict):
        # Single-variant Shopify JSON-LD puts the SKU on Product rather than Offer.
        offer = product["offers"]
        if not product.get("sku"):
            raise ValueError("single product SKU absent")
        product["offers"] = [dict(offer, sku=product["sku"])]
    return product


def fetch_product(shop, p):
    handle = p.get("handle", "")
    if not re.fullmatch(r"[a-z0-9-]+", handle):
        raise ValueError("invalid product handle")
    url = shop["host"] + shop["prefix"] + "/products/" + handle
    data = get_json(url + ".js")
    ld = structured_product(get_text(url), data)
    return data, ld, url


def species_match(title, row, names):
    matches = [n for n in names if any(re.search(r"(?<![A-Za-z0-9])" + re.escape(n[k]) + r"(?![A-Za-z0-9])", title, re.I)
                                     for k in ("9", "6"))]
    matches = [n for n in matches if ko.normalize(n["6"]) == ko.normalize(row["german_species"])
               and ko.normalize(n["3"]) in ko.normalize(row["native_name"])]
    return len(matches) == 1


def catalog_rejection(row, p, names):
    if row["language_code"] != "ko" or row["identity_count"] != 1 or not row["card_id"].startswith("official_ko_"):
        return "catalog_identity"
    match = TITLE.fullmatch(p.get("title", ""))
    if not match or ko.normalize(match[3]) != ko.normalize(row["set_id"]) or int(match[4]) != int(row["local_id"]):
        return "set_number"
    label = match[2]
    if label == "Fixed":
        if row["rarity"] not in ("C", "U"):
            return "rarity"
    elif RARITIES.get(label) != row["rarity"]:
        return "rarity"
    if re.search(r"promo|master.?ball|pok[eé].?ball|reverse|stamp|graded|PSA|BGS|CGC|edition|oversized|jumbo|shiny", p["title"], re.I):
        return "printing"
    if not species_match(match[1], row, names):
        return "species"
    return None


def match_offer(row, feed, detail, ld, url, shop, names, currency):
    if row["language_code"] != "ko" or row["identity_count"] != 1 or not row["card_id"].startswith("official_ko_"):
        return None, "catalog_identity"
    if feed.get("id") != detail.get("id") or detail.get("url") != urllib.parse.urlsplit(url).path or ld.get("url") != url:
        return None, "product_identity"
    if feed.get("product_type") != "Pokémon Single" or detail.get("type") != "Pokémon Single":
        return None, "product_type"
    for p in (feed, detail):
        reason = catalog_rejection(row, p, names)
        if reason:
            return None, reason
    fv, dv = korean_variant(feed), korean_variant(detail)
    if not fv or not dv or type(dv.get("id")) is not int or fv.get("id") != dv["id"] or fv.get("sku") != dv.get("sku"):
        return None, "retailer_variant"
    sku = str(dv.get("sku", ""))
    if not re.fullmatch(re.escape(row["set_id"]) + r"0*" + str(int(row["local_id"])) + r"-\d+", sku, re.I):
        return None, "sku"
    if fv.get("available") is not True or dv.get("available") is not True:
        return None, "stock"
    if dv.get("requires_selling_plan") or dv.get("selling_plan_allocations") or dv.get("quantity_price_breaks"):
        return None, "retailer_variant"
    rule = dv.get("quantity_rule") or {}
    if rule.get("min") != 1 or rule.get("increment") != 1:
        return None, "bundle"
    selected_url = url + "?variant=" + str(dv["id"])
    offers = ld.get("offers")
    if not isinstance(offers, list):
        return None, "offer"
    exact = [o for o in offers if o.get("url") == selected_url and o.get("sku") == sku]
    if len(exact) != 1:
        return None, "offer"
    offer = exact[0]
    if offer.get("availability") not in ("http://schema.org/InStock", "https://schema.org/InStock"):
        return None, "stock"
    if currency != "EUR" or offer.get("priceCurrency") != "EUR":
        return None, "currency"
    cents = dv.get("price")
    if type(cents) is not int or cents <= 0:
        return None, "price"
    amount = Decimal(cents) / 100
    if amount != ko.retail.positive_decimal(fv.get("price")) or amount != ko.retail.positive_decimal(offer.get("price")):
        return None, "price"
    return dict(source=shop["source"], currency="EUR", amount=str(amount),
                title=detail["title"], url=selected_url, product_id=detail["id"],
                offer_variant_id=dv["id"], sku=sku, condition="Near Mint", printing="Normal",
                rarity=row["rarity"], price_basis="displayed retail asking price"), None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shop", choices=sorted(SHOPS), required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    shop = SHOPS[args.shop]
    names = ko.species_names()
    ct = ko.module("resolve-cardtrader-ko-nm-prices")
    rows = ct.extra.load_targets(shop["source"]) + ct.pinned.load_targets(ko, shop["source"], names)
    if args.missing_only:
        rows = ct.missing.filter_targets(rows, ko.retail)
    by_key = defaultdict(list)
    for row in rows:
        by_key[(ko.normalize(row["set_id"]), int(row["local_id"]))].append(row)
    currency = get_json(shop["host"] + shop["prefix"] + "/cart.js").get("currency")
    if currency != "EUR":
        raise SystemExit("shop currency is not verified EUR")
    products = collection(shop)
    candidates = []
    rejected = Counter()
    for p in products:
        v = korean_variant(p)
        match = TITLE.fullmatch(p.get("title", ""))
        if not v or v.get("available") is not True or not match:
            continue
        if (ko.normalize(match[3]), int(match[4])) not in by_key:
            rejected["no_eligible_catalog_target"] += 1
            continue
        eligible = [r for r in by_key[(ko.normalize(match[3]), int(match[4]))] if catalog_rejection(r, p, names) is None]
        if not eligible:
            for r in by_key[(ko.normalize(match[3]), int(match[4]))]:
                rejected[catalog_rejection(r, p, names)] += 1
            continue
        candidates.append(p)
    def fetch(p):
        try:
            return p, fetch_product(shop, p), None
        except Exception as e:
            return p, None, type(e).__name__ + ": " + str(e)
    updates, errors = [], []
    observed = datetime.now(timezone.utc).isoformat()
    chosen = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        for feed, result, error in pool.map(fetch, candidates):
            if error:
                errors.append(dict(handle=feed["handle"], error=error))
                continue
            detail, ld, url = result
            match = TITLE.fullmatch(feed["title"])
            for row in by_key[(ko.normalize(match[3]), int(match[4]))]:
                offer, reason = match_offer(row, feed, detail, ld, url, shop, names, currency)
                if reason:
                    rejected[reason] += 1
                    continue
                base = (Decimal(offer["amount"]) / Decimal(".92")).quantize(Decimal(".0001"), rounding=ROUND_HALF_UP)
                u = dict(row=row, offer=offer, base_eur=str(base), observed_at=observed)
                old = chosen.get(row["card_id"])
                if old is None or Decimal(offer["amount"]) < Decimal(old["offer"]["amount"]):
                    chosen[row["card_id"]] = u
    updates = list(chosen.values())
    # Distinguish refreshed known cards from genuinely new coverage.
    new_matches = sum(u["row"].get("old_status") != "PRICE_FOUND" for u in updates)
    report = dict(shop=args.shop, source=shop["source"], catalog_candidates=len(rows), retail_products=len(products),
                  product_candidates=len(candidates), matched=len(updates), new_price_candidates=new_matches,
                  previously_priced_matches=len(updates)-new_matches, rejected=dict(rejected), errors=errors,
                  updates=updates, applied=ko.apply_updates(updates, shop["source"], missing_only=args.missing_only) if args.apply and not errors else dict(variants=0, prices=0, history=0))
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "updates"}, ensure_ascii=False), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
