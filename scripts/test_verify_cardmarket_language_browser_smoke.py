#!/usr/bin/env python3
"""Regression tests: don't accept the wrong language or condition as pricing."""
import importlib.util
import json
import unittest
from pathlib import Path

module_path=Path(__file__).with_name("verify-cardmarket-language-browser-smoke.py")
spec=importlib.util.spec_from_file_location("language_probe",module_path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def pair():
    def row(lang,price):
        language_id,display=module.LANGS[lang]
        return {"card":"test Mewtwo","lang":lang,"data":{
            "url":"https://www.cardmarket.com/de/Pokemon/Products/Singles/Base-Set/Mewtwo-V1-BS10?language="+language_id+"&minCondition=2",
            "checked":["language["+language_id+"]"],"condition":"2","productId":"273705",
            "rows":6,"offers":[{"condition":"Near Mint","labels":[display],"price":price} for _ in range(6)]}}
    return [row("de","1.234,56 €"),row("en","1,234.56 €")]

class BrowserLanguageTests(unittest.TestCase):
    def test_separated_languages(self):
        x=module.check(pair())
        self.assertEqual(len(x),2)
        self.assertEqual(x[0]["entry_five_median_eur"],"1234.56")
        self.assertEqual(x[1]["entry_five_median_eur"],"1234.56")
    def test_reject_mixed_language(self):
        rows=pair()
        rows[0]["data"]["checked"].append("language[1]")
        with self.assertRaises(ValueError):module.check(rows)
    def test_reject_language_in_offer(self):
        rows=pair()
        rows[1]["data"]["offers"][0]["labels"]=["Deutsch"]
        with self.assertRaises(ValueError):module.check(rows)
    def test_reject_no_committed_query(self):
        rows=pair()
        rows[0]["data"]["url"]="https://www.cardmarket.com/de/Pokemon/Products/Singles/Base-Set/Mewtwo-V1-BS10"
        with self.assertRaises(ValueError):module.check(rows)
    def test_reject_bad_condition(self):
        rows=pair()
        rows[0]["data"]["offers"][0]["condition"]="Excellent"
        with self.assertRaises(ValueError):module.check(rows)
    def test_reject_product_drift(self):
        rows=pair()
        rows[1]["data"]["productId"]="999999"
        with self.assertRaises(ValueError):module.check(rows)
if __name__=="__main__":unittest.main()
