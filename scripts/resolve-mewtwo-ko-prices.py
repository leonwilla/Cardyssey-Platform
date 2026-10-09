#!/usr/bin/env python3
"""Exact in-stock Korean singles with explicit Near Mint condition and gross EUR prices."""
import argparse
import concurrent.futures
import importlib.util
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from html.parser import HTMLParser
from pathlib import Path

spec = importlib.util.spec_from_file_location("ko", Path(__file__).with_name("resolve-uturi-ko-prices.py"))
ko = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ko)
HOST = "https://www.mewtwo.eu"
CATEGORY = "/en/korean-pokemon-cards/"
SOURCE = "WEB_MEWTWO_KO"
TITLE = re.compile(r"^Pokémon (.+) \(([A-Za-z0-9]+) (\d+)\) - Korean$")


def get_text(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={
        "User-Agent": "Cardyssey/0.3 public-price-audit",
    }), timeout=12) as response:
        return response.read().decode("utf-8")


class Listing(HTMLParser):
    """Limit discovery to the category's primary product list, excluding recommendations."""
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.root = None
        self.current = None
        self.products = []
        self.last_page = 1

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            match = re.fullmatch(re.escape(CATEGORY) + r"page-(\d+)/", attrs.get("href", ""))
            if match:
                self.last_page = max(self.last_page, int(match[1]))
        if tag == "div":
            self.depth += 1
            if attrs.get("id") == "products":
                self.root = self.depth
        if self.root is None:
            return
        if attrs.get("data-micro") == "product":
            if self.current:
                self.products.append(self.current)
            self.current = {"id": attrs.get("data-micro-product-id")}
        if self.current is not None:
            if attrs.get("data-micro") == "url":
                self.current["path"] = attrs.get("href")
            if "data-micro-availability" in attrs:
                self.current["availability"] = attrs["data-micro-availability"]

    def handle_endtag(self, tag):
        if tag == "div":
            if self.depth == self.root:
                if self.current:
                    self.products.append(self.current)
                self.current = None
                self.root = None
            self.depth -= 1


class ProductForm(HTMLParser):
    """Extract only public metadata and condition options from the main product form."""
    def __init__(self):
        super().__init__()
        self.active = False
        self.select = False
        self.option = None
        self.options = []
        self.metadata = defaultdict(list)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.active = attrs.get("data-testid") == "formProduct"
        if not self.active:
            return
        if tag in ("meta", "link") and attrs.get("itemprop"):
            self.metadata[attrs["itemprop"]].append(attrs.get("content", attrs.get("href")))
        if tag == "select" and attrs.get("id") == "simple-variants-select":
            self.select = True
        if tag == "option" and self.select:
            self.option = dict(attrs, text="")
            self.options.append(self.option)

    def handle_data(self, data):
        if self.option is not None:
            self.option["text"] += data

    def handle_endtag(self, tag):
        if tag == "option":
            self.option = None
        if tag == "select":
            self.select = False
        if tag == "form":
            self.active = False


def parse_product(html):
    # JSON only: never evaluate retailer JavaScript.
    objects = []
    for script in re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S | re.I):
        marker = re.search(r"dataLayer\.push\(\s*\{\s*'shoptet'\s*:\s*", script)
        if marker:
            objects.append(json.JSONDecoder().raw_decode(script[marker.end():])[0])
    if len(objects) != 1:
        raise ValueError("ambiguous retailer product data")
    form = ProductForm()
    form.feed(html)
    return objects[0], dict(form.metadata), form.options


def one(metadata, key):
    values = metadata.get(key, [])
    return values[0] if len(values) == 1 else None


def match_offer(row, data, metadata, options, url, names):
    if row["language_code"] != "ko" or row["identity_count"] != 1 or not row["card_id"].startswith("official_ko_"):
        return None, "catalog_identity"
    product = data.get("product") or {}
    title = product.get("name", "")
    match = TITLE.fullmatch(title)
    if not match or data.get("pageType") != "productDetail":
        return None, "title"
    english, code, number = match.groups()
    if ko.normalize(code) != ko.normalize(row["set_id"]) or int(number) != int(row["local_id"]):
        return None, "set_number"
    if product.get("currentCategory") != "Pokémon Single Cards | Korean" or product.get("defaultCategory") != "Pokémon Single Cards | Korean":
        return None, "language"
    if re.search(r"promo|master.?ball|pok[eé].?ball|reverse|stamp|graded|PSA|BGS|CGC|1st.?edition", title, re.I):
        return None, "printing"
    if row["rarity"] not in ("C", "U", "R", "RR", "RRR", "AR", "SR", "SAR", "UR", "HR", "S", "SSR"):
        return None, "catalog_rarity"
    matches = [name for name in names if re.search(
        r"(?<![A-Za-z0-9])" + re.escape(name["9"]) + r"(?![A-Za-z0-9])", english, re.I)]
    if not matches:
        return None, "species"
    longest = max(len(name["9"]) for name in matches)
    matches = [name for name in matches if len(name["9"]) == longest]
    if len(matches) != 1:
        return None, "species"
    name = matches[0]
    if ko.normalize(name["6"]) != ko.normalize(row["german_species"]) or ko.normalize(name["3"]) not in ko.normalize(row["native_name"]):
        return None, "species"
    codes = product.get("codes") or []
    if len(codes) != 1 or len(options) != 1 or not product.get("hasVariants"):
        return None, "retailer_variant"
    sku = codes[0].get("code", "")
    if sku != one(metadata, "sku") or str(product.get("id")) != one(metadata, "productID"):
        return None, "product_identity"
    if not sku.endswith("/NEA") or not options[0].get("text", "").replace("\xa0", " ").startswith("Stav: Near Mint - In Stock"):
        return None, "condition"
    if one(metadata, "itemCondition") != "https://schema.org/NewCondition":
        return None, "condition"
    quantity = ko.retail.positive_decimal(codes[0].get("quantity"))
    if quantity is None or one(metadata, "availability") != "https://schema.org/InStock":
        return None, "stock"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "www.mewtwo.eu" or not parsed.path.startswith(CATEGORY) or one(metadata, "url") != url:
        return None, "product_identity"
    if data.get("currency") != "EUR" or product.get("currency") != "EUR" or one(metadata, "priceCurrency") != "EUR":
        return None, "currency"
    amount = ko.retail.positive_decimal(one(metadata, "price"))
    gross = ko.retail.positive_decimal(product.get("priceWithVat"))
    option_price = ko.retail.positive_decimal(options[0].get("data-customerprice"))
    if amount is None or gross is None or option_price is None:
        return None, "price"
    # JavaScript may serialize 1.6 as 1.6000000000000001; round only documented EUR cents.
    if amount != amount.quantize(Decimal("0.01")) or gross.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) != amount or option_price != amount:
        return None, "gross_price"
    option_id = options[0].get("value", "")
    if not option_id.isdigit():
        return None, "retailer_variant"
    return dict(source=SOURCE, currency="EUR", amount=str(amount), title=title, url=url,
                product_id=product["id"], offer_variant_id=option_id, rarity=row["rarity"],
                condition="Near Mint", tax_basis="gross including VAT",
                identity_method="exact-korean-set-number-species-condition"), None


def get_listings():
    def fetch(page):
        url = HOST + CATEGORY + (f"page-{page}/" if page > 1 else "")
        listing = Listing()
        listing.feed(get_text(url))
        if not listing.products:
            raise ValueError(f"missing category products on page {page}")
        return listing
    first = fetch(1)
    if first.last_page > 40:
        raise ValueError("category pagination limit")
    products = {}
    signatures = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        listings = [first] + list(pool.map(fetch, range(2, first.last_page + 1)))
    for listing in listings:
        signature = tuple(product["id"] for product in listing.products)
        if signature in signatures:
            raise ValueError("repeated pagination")
        signatures.add(signature)
        for product in listing.products:
            path = product.get("path", "")
            if not re.fullmatch(re.escape(CATEGORY) + r"[a-z0-9-]+/", path):
                raise ValueError("unexpected category product path")
            products[product["id"]] = product
    return list(products.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    targets = ko.load_targets(source=SOURCE)
    by_key = defaultdict(list)
    for row in targets:
        by_key[(ko.normalize(row["set_id"]), int(row["local_id"]))].append(row)
    names = ko.species_names()
    products = get_listings()
    candidates = [product for product in products if product["availability"] == "https://schema.org/InStock"]
    def fetch(product):
        url = HOST + product["path"]
        try:
            return url, parse_product(get_text(url)), None
        except Exception as error:
            return url, None, type(error).__name__ + ": " + str(error)
    updates, errors, rejected, seen = [], [], Counter(), set()
    observed = datetime.now(timezone.utc).isoformat()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for url, result, error in pool.map(fetch, candidates):
            if error:
                errors.append(dict(url=url, error=error))
                continue
            data, metadata, options = result
            match = TITLE.fullmatch((data.get("product") or {}).get("name", ""))
            if not match:
                rejected["title"] += 1
                continue
            rows = by_key[(ko.normalize(match[2]), int(match[3]))]
            if not rows:
                rejected["no_eligible_catalog_target"] += 1
            for row in rows:
                offer, reason = match_offer(row, data, metadata, options, url, names)
                if reason:
                    rejected[reason] += 1
                    continue
                if row["card_id"] in seen:
                    raise ValueError("ambiguous duplicate retail identity")
                seen.add(row["card_id"])
                base = (Decimal(offer["amount"]) / ko.retail.NM_FACTOR).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                updates.append(dict(row=row, offer=offer, base_eur=str(base), observed_at=observed))
    report = dict(catalog_candidates=len(targets), retail_products=len(products), in_stock=len(candidates),
                  updates=updates, errors=errors, rejected=dict(rejected),
                  applied=ko.apply_updates(updates, source=SOURCE) if args.apply and not errors else dict(variants=0, prices=0, history=0))
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "updates"} | {"matched": len(updates)}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
