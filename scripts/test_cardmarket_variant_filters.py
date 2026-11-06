#!/usr/bin/env python3
"""Regression checks against actual queued Cardyssey print variants."""
import csv
import re
import unittest
from pathlib import Path

QUEUE=Path("/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector/queue-de.csv")
SCRIPT=Path(__file__).with_name("cardmarket-language-browser-collector.ps1")

def filters(row):
    kind=row["drucktyp"]
    reverse="Y" if re.search("reverse",kind,re.I) else "N" if re.search("normal",kind,re.I) else "0"
    stamp=row["stempel"]
    first="Y" if re.search(r"1\. auflage|first.edition",stamp,re.I) else (
        "N" if re.fullmatch(r"unbegrenzt|unlimited",row["sonderdruck"],re.I) else "0")
    return reverse,first
def selected():
    wanted={"base1-8","sm10-16","mep-095"}
    with QUEUE.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if r["cardyssey_karte"] in wanted:yield r

class CheckVariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=list(selected())
    def test_first_edition_machamp(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="base1-8" and "1. Auflage" in r["stempel"]]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("0","Y"))
    def test_unlimited_machamp(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="base1-8" and r["sonderdruck"]=="unbegrenzt"]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("0","N"))
    def test_tangela_reverse_does_not_imply_first(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="sm10-16" and "reverse" in r["drucktyp"].lower()]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("Y","0"))
    def test_tangela_normal(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="sm10-16" and "normal" in r["drucktyp"].lower()]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("N","0"))
    def test_lucario_not_auto_cosmos_filter(self):
        rows=[r for r in self.rows if r["cardyssey_karte"]=="mep-095"]
        self.assertEqual(len(rows),1)
        self.assertEqual(filters(rows[0]),("0","0"))
    def test_live_script_independent_filters_and_query_verification(self):
        s=SCRIPT.read_text(encoding="utf-8-sig")
        for token in ("expected_reverse_holo","expected_first_edition","extra[isReverseHolo]","extra[isFirstEd]","searchParams.get(k)","all_pages_complete=$false"):
            self.assertIn(token,s)
if __name__=="__main__":
    unittest.main()
