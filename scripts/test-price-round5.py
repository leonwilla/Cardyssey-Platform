#!/usr/bin/env python3
"""Offline safety and tax/stock/identity regressions for the Mewtwo Korean source."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

shop = load("resolve-mewtwo-ko-prices")


class KoreanSourceTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(language_code="ko", card_id="official_ko_test", identity_count=1,
                        set_id="SV1V", local_id="089", rarity="AR", german_species="Adebom",
                        native_name="떨구새", old_variants=[], old_updated=None, old_status=None,
                        image_source_url="https://official/image")
        self.url = shop.HOST + shop.CATEGORY + "pokemon-bombirdier--sv1v-089-korejsky/"
        self.data = dict(pageType="productDetail", currency="EUR", product=dict(
            id=4050, name="Pokémon Bombirdier (sv1V 089) - Korean", currency="EUR",
            currentCategory="Pokémon Single Cards | Korean", defaultCategory="Pokémon Single Cards | Korean",
            hasVariants=True, priceWithVat=1.6000000000000001, codes=[dict(code="4050/NEA", quantity="4")]))
        self.meta = {key: [value] for key, value in dict(
            productID="4050", sku="4050/NEA", availability="https://schema.org/InStock",
            url=self.url, price="1.60", priceCurrency="EUR", itemCondition="https://schema.org/NewCondition").items()}
        self.options = [dict(value="7119", text="Stav: Near Mint - In Stock 4 pcs (€1.60)", **{"data-customerprice": "1.6"})]
        self.names = [{"9": "Bombirdier", "6": "Adebom", "3": "떨구새"}]

    def match(self):
        return shop.match_offer(self.row, self.data, self.meta, self.options, self.url, self.names)

    def test_exact_gross_price_with_documented_cent_rounding(self):
        offer, reason = self.match()
        self.assertIsNone(reason)
        self.assertEqual("1.60", offer["amount"])
        self.assertEqual("gross including VAT", offer["tax_basis"])
        self.assertEqual("Near Mint", offer["condition"])

    def test_net_tracking_price_cannot_replace_gross_price(self):
        self.meta["price"] = ["1.32"]
        self.assertEqual("gross_price", self.match()[1])
        self.setUp()
        self.options[0]["data-customerprice"] = "1.32"
        self.assertEqual("gross_price", self.match()[1])

    def test_currency_and_ambiguous_price_metadata_fail_closed(self):
        self.data["currency"] = "CZK"
        self.assertEqual("currency", self.match()[1])
        self.setUp(); self.meta["priceCurrency"].append("CZK")
        self.assertEqual("currency", self.match()[1])
        self.setUp(); self.meta["price"].append("1.60")
        self.assertEqual("price", self.match()[1])

    def test_wrong_set_number_language_and_species_rejected(self):
        for key, value in [("set_id", "SV1S"), ("local_id", "088"), ("language_code", "ja"),
                           ("identity_count", 2), ("native_name", "피카츄"), ("german_species", "Pikachu")]:
            with self.subTest(key=key):
                self.setUp(); self.row[key] = value
                self.assertIsNotNone(self.match()[1])
        self.setUp(); self.data["product"]["name"] = "Pokémon Pikachu (sv1V 089) - Korean"
        self.assertEqual("species", self.match()[1])

    def test_special_prints_and_multiple_conditions_are_rejected(self):
        self.data["product"]["name"] = "Pokémon Bombirdier Reverse (sv1V 089) - Korean"
        self.assertEqual("printing", self.match()[1])
        self.setUp(); self.options.append(dict(self.options[0], value="other"))
        self.assertEqual("retailer_variant", self.match()[1])
        self.setUp(); self.options[0]["text"] = "Stav: Played - In Stock 4 pcs (€1.60)"
        self.assertEqual("condition", self.match()[1])

    def test_stock_must_agree_on_product_and_offer(self):
        self.data["product"]["codes"][0]["quantity"] = "0"
        self.assertEqual("stock", self.match()[1])
        self.setUp(); self.meta["availability"] = ["https://schema.org/OutOfStock"]
        self.assertEqual("stock", self.match()[1])

    def test_product_identity_and_default_language_category_must_agree(self):
        self.meta["url"] = ["https://untrusted.example/product"]
        self.assertEqual("product_identity", self.match()[1])
        self.setUp(); self.meta["sku"] = ["different/NEA"]
        self.assertEqual("product_identity", self.match()[1])
        self.setUp(); self.data["product"]["defaultCategory"] = "Japanese"
        self.assertEqual("language", self.match()[1])

    def test_parser_ignores_related_product_metadata_and_never_executes_js(self):
        html = "<script>dataLayer.push({'shoptet':" + json.dumps(self.data) + "});</script>"
        html += '<form data-testid="formProduct">'
        for key, values in self.meta.items():
            for value in values:
                html += '<meta itemprop="' + key + '" content="' + value + '">'
        html += '<select id="simple-variants-select"><option value="7119" data-customerprice="1.6">Stav: Near Mint - In Stock 4 pcs (€1.60)</option></select></form>'
        html += '<meta itemprop="price" content="999999"><script>throw "do not execute";</script>'
        data, meta, options = shop.parse_product(html)
        self.assertIsNone(shop.match_offer(self.row, data, meta, options, self.url, self.names)[1])
        with self.assertRaises(ValueError):
            shop.parse_product("<script>dataLayer.push({'shoptet':runCode()});</script>")

    def test_discovery_ignores_recommendations_outside_primary_list(self):
        html = '<div data-micro="product" data-micro-product-id="excluded"></div>'
        html += '<div id="products"><div data-micro="product" data-micro-product-id="good"><a data-micro="url" href="/en/korean-pokemon-cards/good/"></a><div data-micro-availability="https://schema.org/InStock"></div></div></div>'
        html += '<div data-micro="product" data-micro-product-id="also-excluded"></div><a href="/en/korean-pokemon-cards/page-33/"></a>'
        listing = shop.Listing(); listing.feed(html)
        self.assertEqual(["good"], [product["id"] for product in listing.products])
        self.assertEqual(33, listing.last_page)

    def test_untrusted_source_and_mixed_source_writes_are_rejected(self):
        with self.assertRaises(ValueError): shop.ko.load_targets(source="untrusted")
        with self.assertRaises(ValueError): shop.ko.apply_updates([], source="untrusted")
        update = dict(row=self.row, offer=self.match()[0], base_eur="1.7391", observed_at="2026-10-09T12:00:00Z")
        with self.assertRaises(ValueError): shop.ko.apply_updates([update])
        bad = copy.deepcopy(update); bad["row"]["language_code"] = "ja"
        with self.assertRaises(ValueError): shop.ko.apply_updates([bad], source=shop.SOURCE)


if __name__ == "__main__":
    if "--postgres" in sys.argv:
        existing = load("test-price-round3")
        existing.postgres_tests(source=shop.SOURCE)
    else:
        unittest.main()
