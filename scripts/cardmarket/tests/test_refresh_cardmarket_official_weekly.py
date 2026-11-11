#!/usr/bin/env python3
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location(
    "weekly",source_path("refresh-cardmarket-official-weekly.py"))
# Importing module is safe: argparse only runs in __main__.
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class OfficialGuideTests(unittest.TestCase):
    def test_30day_preferred(self):
        self.assertEqual(mod.value_for({"avg30":1.25,"trend":2.7},"trend"),(1.25,"avg30"))
    def test_holo_separate(self):
        self.assertEqual(mod.value_for({"avg30":1.25,"avg30-holo":3.5},"trend-holo"),(3.5,"avg30-holo"))
    def test_missing_uses_trend(self):
        self.assertEqual(mod.value_for({"avg30":None,"trend":2.1},"avg30"),(2.1,"trend"))
    def test_no_price_preserves_existing(self):
        self.assertEqual(mod.value_for({"avg30":None,"trend":None},"avg30"),(None,None))
    def test_special_print_not_written(self):
        rows=[{"card_id":"x","language":"de","variant_id":"v",
               "failure_detail":"Cardmarket product 123; key avg30; via refresh",
               "variant":{"id":"v","type":"normal","stamps":["staff"]},"old_price":5}]
        updates,stats=mod.prepare(rows,{"123":{"avg30":9}})
        self.assertEqual(updates,[])
        self.assertEqual(stats["ambiguous_variant"],1)
    def test_regular_print(self):
        rows=[{"card_id":"x","language":"en","variant_id":"v",
               "failure_detail":"Cardmarket product 123; key trend; via refresh",
               "variant":{"id":"v","type":"normal","stamps":[],"foil":None},"old_price":5}]
        updates,stats=mod.prepare(rows,{"123":{"avg30":9,"trend":4}})
        self.assertEqual(updates[0]["price"],9)
        self.assertEqual(stats["avg30"],1)

if __name__=="__main__":
    unittest.main()
