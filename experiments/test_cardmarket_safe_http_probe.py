import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("cm_safe",ROOT/"cardmarket_safe_http_probe.py")
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

class SafeCardmarketTests(unittest.TestCase):
    def test_extracts_cardmarket_identity_but_never_publishes_price(self):
        body=b'<title>Lucario | Cardmarket</title><input name="idProduct" value="895610"><div class="article-row">0,05 \xe2\x82\xac</div>'
        result=mod.parse_product(body)
        self.assertEqual("895610",result["product_id"])
        self.assertEqual(1,result["article_rows_visible"])
        self.assertFalse(result["german_nm_confirmed"])
        self.assertFalse(result["price_published"])

    def test_backoff_interval(self):
        self.assertEqual(10.5,mod.calculate_wait(12,1.5))
        self.assertEqual(0,mod.calculate_wait(12,20))

    def test_429_stops_before_next_card(self):
        class Response:
            class Status:
                def as_int(self):return 429
            status=Status()
            headers={}
        fake_session=SimpleNamespace(identity=SimpleNamespace(),exit_ip="")
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/"test.jsonl"
            cases=[{"card_id":str(i),"expected_product_id":str(i),
                    "url":"https://www.cardmarket.com/de/Pokemon/Products/Singles/Base-Set/Card-"+str(i)} for i in range(10)]
            with patch.object(mod.transport,"load_session",return_value=fake_session),\
                 patch.object(mod.transport,"build_client",return_value=object()),\
                 patch.object(mod.transport,"navigate",return_value=(Response(),b"Just a moment")),\
                 patch.object(mod.transport,"classify",return_value="challenge"),\
                 patch.object(mod.transport,"_header",return_value=""),\
                 patch.object(mod.transport,"save_session",return_value=None) as save,\
                 patch.object(mod.transport,"navigate",return_value=(Response(),b"Just a moment")) as nav:
                report=mod.run(cases,out,12,30)
            self.assertEqual(1,nav.call_count)
            self.assertEqual(1,report["attempted"])
            self.assertEqual(1,report["rate_limited"])
            self.assertEqual(1,len(out.read_text().splitlines()))
            self.assertTrue((out.parent/"cardmarket_http_cooldown.json").exists())
            save.assert_called_once()

if __name__=="__main__":unittest.main()
