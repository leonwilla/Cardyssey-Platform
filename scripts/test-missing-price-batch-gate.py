#!/usr/bin/env python3
"""Threshold boundaries and CLI writer prevention, with no live writes/network."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parent

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

gate = load('missing-price-targets.py')

def updates(n):
    return [dict(row=dict(card_id='card'+str(i)), base_eur='1.00') for i in range(n)]

class BatchGateTests(unittest.TestCase):
    def check(self, batch, priced=(), **kwargs):
        return gate.import_gate(batch, lambda sql: json.dumps(list(priced)), missing_only=True, **kwargs)

    def test_999_writes_blocked(self):
        r = self.check(updates(999))
        self.assertFalse(r['allowed']); self.assertEqual(r['distinct_new_cards'],999)

    def test_1000_distinct_new_cards_allowed(self):
        self.assertTrue(self.check(updates(1000))['allowed'])

    def test_duplicate_variant_rows_do_not_meet_threshold(self):
        r = self.check(updates(999)+updates(1))
        self.assertFalse(r['allowed']); self.assertEqual(r['duplicate_cards'],1)

    def test_existing_price_on_any_variant_blocks_stale_batch(self):
        r = self.check(updates(1000), priced=['card999'])
        self.assertFalse(r['allowed']); self.assertEqual(r['distinct_new_cards'],999)
        self.assertEqual(r['reason'],'already_priced_cards')

    def test_existing_rows_block_even_above_threshold(self):
        self.assertFalse(self.check(updates(1001), priced=['card1000'])['allowed'])

    def test_price_found_snapshot_blocks(self):
        batch=updates(1001);batch[-1]["row"]["old_status"]="PRICE_FOUND"
        self.assertFalse(self.check(batch)["allowed"])

    def test_invalid_and_nonfinite_prices_block(self):
        for value in ['0','-1','NaN','Infinity',None,'bad']:
            batch=updates(1001);batch[-1]['base_eur']=value
            self.assertFalse(self.check(batch)['allowed'], value)

    def test_provider_failure_blocks(self):
        self.assertEqual(self.check(updates(1000),errors=[{'error':'HTTPError'}])['reason'],'provider_errors')

    def test_weekly_refresh_has_no_manual_minimum(self):
        def no_db(sql): raise AssertionError('weekly gate must not query new-only coverage')
        self.assertTrue(gate.import_gate(updates(1),no_db,missing_only=False)['allowed'])

class CliTests(unittest.TestCase):
    def run_reader(self,n,missing_only):
        m=load('resolve-cardtrader-ko-nm-prices.py')
        rows=[dict(card_id='card'+str(i), set_id='SV1', local_id=str(i), language_code='ko') for i in range(n)]
        expansion=dict(id=1,game_id=5,code='SV1')
        def response(req,timeout):
            if req.full_url.endswith('/expansions'): data=[expansion]
            elif '/blueprints/' in req.full_url: data=[]
            else: data={}
            return io.StringIO(json.dumps(data))
        original=Path.read_text
        def read(path,*a,**kw):
            if str(path)=='/home/tv/cardshop/platform/.env':return 'CARDTRADER_API_TOKEN=test-only'
            return original(path,*a,**kw)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'report.json'
            argv=['reader','--apply','--report',str(target)]+(['--missing-only'] if missing_only else [])
            with patch('sys.argv',argv), patch.object(Path,'read_text',read), patch.object(m.urllib.request,'urlopen',response), patch.object(m.time,'sleep'), patch.object(m.ko,'species_names',return_value=[]), patch.object(m.extra,'load_targets',return_value=rows), patch.object(m.pinned,'load_targets',return_value=[]), patch.object(m.missing,'filter_targets',side_effect=lambda rows,retail:rows), patch.object(m,'match',return_value=(dict(amount='1.00'),None)), patch.object(m.ko.retail,'db',return_value='[]'), patch.object(m.ko,'apply_updates',return_value=dict(prices=n,variants=n,history=n)) as writer, contextlib.redirect_stdout(io.StringIO()):
                try:
                    m.main()
                except SystemExit as e:
                    self.assertEqual(e.code,2)
                    self.assertTrue(missing_only and n<1000)
                calls=writer.call_count
            return calls,json.loads(target.read_text())

    def test_manual_999_never_calls_writer(self):
        calls,r=self.run_reader(999,True)
        self.assertEqual(calls,0);self.assertEqual(r['applied']['prices'],0)
        self.assertEqual(r['import_gate']['reason'],'below_minimum_new_cards')

    def test_manual_1000_calls_writer(self):
        calls,r=self.run_reader(1000,True)
        self.assertEqual(calls,1);self.assertEqual(r['applied']['prices'],1000)

    def test_weekly_small_batch_still_calls_writer(self):
        calls,r=self.run_reader(1,False)
        self.assertEqual(calls,1);self.assertEqual(r['import_gate']['reason'],'weekly_refresh')

if __name__=='__main__':unittest.main()
