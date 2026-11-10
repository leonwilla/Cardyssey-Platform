"""Targeted recheck queue is lossless and never reclassifies a print or price."""
import csv, importlib.util, json, tempfile, unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('schedule',ROOT/'scripts/cardmarket-schedule-variant-rechecks.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
class SchedulerTest(unittest.TestCase):
    def test_marks_only_actual_failures_and_keeps_ids_and_prices(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Path(tmp)
            cols=['cardyssey_karte','variante_id','set_id','kartennummer','kartenname_suche','drucktyp','foil',
                  'stempel','sonderdruck','cardmarket_ids','routing_state','existing_price_eur','manual_scan_requested_at']
            rows=[
                dict(zip(cols,['sv10.5w-033','poke','sv10.5w','033','Wattzapf','Reverse','Pokéball','[]','','836551','UNVERIFIED','7.58',''])),
                dict(zip(cols,['sv10.5w-033','master','sv10.5w','033','Wattzapf','Reverse','Meisterball','[]','','836552','UNVERIFIED','0.21',''])),
                dict(zip(cols,['sv10.5w-034','regular','sv10.5w','034','Test','Normal','','[]','','9999','VERIFIED_PRODUCT_ID','0.03','']))]
            with (b/'queue-de.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
            with (b/'browser-observations-de.jsonl').open('w') as f:
                for cid,var,status in [('sv10.5w-033','poke','MULTIPLE_SEARCH_HITS'),
                                      ('sv10.5w-033','master','MULTIPLE_SEARCH_HITS'),
                                      ('sv10.5w-034','regular','MAPPED_NO_PRICE_REQUIRED')]:
                    f.write(json.dumps({'card_id':cid,'variant_id':var,'status':status,'seen_at':'2026-11-10T09:00:00Z'})+'\n')
            at=datetime(2026,11,10,14,30,tzinfo=timezone.utc)
            draft=mod.select('de',limit=2,base=b,now=at,dry_run=True)
            self.assertEqual(draft['scheduled'],2)
            with (b/'queue-de.csv').open(encoding='utf-8-sig') as f:
                self.assertTrue(all(not x['manual_scan_requested_at'] for x in csv.DictReader(f)))
            previous_root=mod.ROOT
            mod.ROOT=b
            try:real=mod.select('de',limit=2,base=b,now=at,dry_run=False)
            finally:mod.ROOT=previous_root
            self.assertEqual(real['scheduled'],2)
            with (b/'queue-de.csv').open(encoding='utf-8-sig') as f: out={x['variante_id']:x for x in csv.DictReader(f)}
            for r in rows:
                self.assertEqual(out[r['variante_id']]['cardmarket_ids'],r['cardmarket_ids'])
                self.assertEqual(out[r['variante_id']]['existing_price_eur'],r['existing_price_eur'])
                self.assertEqual(out[r['variante_id']]['routing_state'],r['routing_state'])
            self.assertEqual(out['regular']['manual_scan_requested_at'],'')
            self.assertEqual(out['poke']['manual_scan_requested_at'],at.isoformat())
    def test_epoch_respects_manual_retry_and_family_leads_never_price(self):
        src=(ROOT/'scripts/cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('-not $manualRefreshDue',src)
        self.assertIn('BROWSER_OBSERVED_PRODUCT_CANDIDATE_PRINT_UNVERIFIED',src)
        self.assertIn('VERSION_FAMILY_PAGE_AND_NUMBER_PROVED_PRINT_UNVERIFIED',src)
        self.assertIn("$out.status='PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED'",src)
        self.assertNotIn("$out.status='PRICE_FOUND'",src)
if __name__=='__main__':unittest.main()
