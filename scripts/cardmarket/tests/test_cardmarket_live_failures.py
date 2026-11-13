import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,importlib.util,io,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
def load(name):
 spec=importlib.util.spec_from_file_location('module_'+name.replace('-','_'),source_path(name))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
fail=load('cardmarket-live-failures.py');retry=load('cardmarket-retry-one.py')
class Tests(unittest.TestCase):
 def setup(self,td):
  base=Path(td);cols=['cardyssey_karte','variante_id','set_id','kartenname_suche','manual_scan_requested_at']
  for lang in ('de','en'):
   with (base/f'queue-{lang}.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
    for card in ('hgss3-5','2019sm-1'):w.writerow({'cardyssey_karte':card,'variante_id':'v1','set_id':card.rsplit('-',1)[0],'kartenname_suche':card})
  return base
 def test_current_failures_paged_and_historical_hidden(self):
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td);start=datetime.now(timezone.utc);(b/'full-rescan-epoch.json').write_text(json.dumps({'requestedAt':start.isoformat()}))
   with (b/'browser-observations-de.jsonl').open('w') as f:
    for card,status,seen in [('2019sm-1','NO_EXACT_NUMBER_SEARCH_HIT',start-timedelta(days=2)),('hgss3-5','FILTER_UNAVAILABLE',start+timedelta(seconds=1))]:
     f.write(json.dumps({'card_id':card,'variant_id':'v1','status':status,'seen_at':seen.isoformat()})+'\n')
   result=fail.list_failures(b,'de',kind='alle')
   self.assertEqual(result['total'],1);self.assertEqual(result['items'][0]['type'],'TECHNISCH')
   self.assertEqual(fail.list_failures(b,'de',scope='all',kind='alle')['total'],2)
   self.assertEqual(fail.list_failures(b,'de')['total'],0)
   self.assertEqual(fail.list_failures(b,'de',kind='technik')['total'],1)
 def test_csv_exports_all_matching_variants_and_safe_cells(self):
  with tempfile.TemporaryDirectory() as td:
   base = self.setup(td)
   start = datetime(2026, 11, 13, 15, tzinfo=timezone.utc)
   (base/'full-rescan-epoch.json').write_text(json.dumps({'requestedAt':start.isoformat()}))
   candidate = 'https://www.cardmarket.com/en/Pokemon/Products/Singles/Test/Pikachu'
   rows = [
    {'card_id':f'set-{i}', 'variant_id':'reverse', 'set_id':'set', 'number':str(i),
     'name':'Pikachü', 'status':'MULTIPLE_SEARCH_HITS',
     'error':'=1+1; "mehrdeutig"\nSet prüfen', 'seen_at':start.isoformat(),
     'score_candidate_count':1, 'score_top_candidate_urls':[candidate]}
    for i in range(52)
   ]
   rows.extend([
    {**rows[0], 'card_id':'other-set-1', 'name':'Raupy'},
    {**rows[0], 'card_id':'old-set-1', 'seen_at':(start-timedelta(days=1)).isoformat()},
    {**rows[0], 'card_id':'technical-1', 'status':'BLOCKED'},
    {**rows[0], 'card_id':'resolved-1'},
   ])
   for language, observations in [('de', rows[:1]), ('en', rows)]:
    log = base/f'browser-observations-{language}.jsonl'
    log.write_text('\n'.join(map(json.dumps, observations)), encoding='utf-8')
   filters = {
    'search':'Pikachü', 'kind':'karten',
    'decisions':{('resolved-1','reverse'):{'status':'CONFIRMED_PRINT','reviewedAt':start.isoformat()}},
   }
   page = fail.list_failures(base,'en',page=1,**filters)
   export = fail.list_failures(base,'en',page=1,for_export=True,**filters)
   self.assertEqual(len(page['items']),2)
   self.assertEqual(export['total'],52)
   self.assertEqual(fail.list_failures(base,'de',for_export=True,**filters)['total'],1)

   stream = io.StringIO(newline='')
   fail.write_failures_csv(export['items'],stream)
   csv_text = stream.getvalue()
   self.assertTrue(csv_text.startswith('\ufeff'))
   cases = list(csv.DictReader(io.StringIO(csv_text[1:]),delimiter=';'))
   self.assertEqual(len(cases),52)
   self.assertEqual({case['Sprache'] for case in cases},{'en'})
   self.assertEqual(cases[-1]['Karten-ID'],'set-51')
   self.assertEqual(cases[-1]['Kartennummer'],'51')
   self.assertEqual(cases[-1]['Varianten-ID'],'reverse')
   self.assertEqual(cases[-1]['Kartenname'],'Pikachü')
   self.assertEqual(cases[-1]['Fehlerdetail'],"'=1+1; \"mehrdeutig\"\nSet prüfen")
   self.assertEqual(cases[-1]['Kandidat 1'],candidate)
   self.assertEqual(cases[-1]['Kandidat 2'],'')
 def test_30th_verified_product_with_incomplete_offers_is_price_only(self):
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td);p=b/'queue-de.csv'
   # A fixture with the real queue shape is preferable to guesswork about
   # optional fields of the old synthetic queue.
   with p.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['cardyssey_karte','variante_id','set_id','kartenname_suche','cardmarket_ids','routing_state','known_url']);w.writeheader()
    w.writerow({'cardyssey_karte':'30th-c-008','variante_id':'v30','set_id':'30th-c','kartenname_suche':'Pikachu & Zekrom GX','cardmarket_ids':'907963','routing_state':'SOURCE_ONLY','known_url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/30th-Celebration/Pikachu-Zekrom-GX-30CTEU-33'})
    w.writerow({'cardyssey_karte':'30th-c-009','variante_id':'v31','set_id':'30th-c','kartenname_suche':'Andere Karte','cardmarket_ids':'907964','routing_state':'SOURCE_ONLY','known_url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/30th-Celebration/Other'})
   now=datetime.now(timezone.utc).isoformat()
   with (b/'browser-observations-de.jsonl').open('w') as f:
    for card,var,pid in [('30th-c-008','v30','907963'),('30th-c-009','v31','999999')]:
     f.write(json.dumps({'card_id':card,'variant_id':var,'status':'FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','product_id':pid,'identity_confirmed':True,'pagination_failure':'LOAD_MORE_DISABLED_OR_LIMIT_REACHED','seen_at':now})+'\n')
   price=fail.list_failures(b,'de',kind='preise');manual=fail.list_failures(b,'de',kind='karten')
   self.assertEqual([x['cardId'] for x in price['items']],['30th-c-008'])
   self.assertEqual([x['cardId'] for x in manual['items']],['30th-c-009'])
   self.assertEqual(price['priceChecks'],1)
   self.assertEqual(manual['assignment'],1)
   self.assertEqual(fail.list_failures(b,'de',kind='alle')['total'],2)
 def test_known_page_with_distinct_stamp_is_not_missing_card_identity(self):
  from pathlib import Path
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td);p=b/'queue-de.csv'
   with p.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['cardyssey_karte','variante_id','set_id','stempel','reference_product_url']);w.writeheader()
    w.writerow({'cardyssey_karte':'basep-1','variante_id':'star','set_id':'basep','stempel':'["grauer stern"]','reference_product_url':'https://www.cardmarket.com/de/Pokemon/Products/Singles/Wizards-Black-Star-Promos/Pikachu-WP1'})
   with (b/'browser-observations-de.jsonl').open('w') as f:f.write(json.dumps({'card_id':'basep-1','variant_id':'star','status':'MULTIPLE_SEARCH_HITS','seen_at':datetime.now(timezone.utc).isoformat()})+'\n')
   self.assertEqual(fail.list_failures(b,'de',kind='karten')['total'],0)
   x=fail.list_failures(b,'de',kind='drucke');self.assertEqual(x['total'],1)
   self.assertEqual(x['items'][0]['printStamp'],'["grauer stern"]')
 def test_other_sets_are_not_auto_exempt(self):
  self.assertEqual(fail.classify('FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE',{'product_id':'907963','identity_confirmed':True},{'set_id':'other','cardmarket_ids':'907963','known_url':'https://example.com'}),'TECHNISCH')
 def test_confirmed_card_disappears_from_current_and_historical_review(self):
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td)
   t=datetime(2026,11,9,19,30,tzinfo=timezone.utc)
   with (b/'browser-observations-de.jsonl').open('w') as f:
    f.write(json.dumps({'card_id':'hgss3-5','variant_id':'v1','status':'MULTIPLE_SEARCH_HITS','seen_at':t.isoformat()})+'\n')
   decisions={('hgss3-5','v1'):{'status':'CONFIRMED_PRINT','reviewedAt':(t+timedelta(minutes=20)).isoformat()}}
   self.assertEqual(fail.list_failures(b,'de',kind='karten',decisions=decisions)['total'],0)
   self.assertEqual(fail.list_failures(b,'de',scope='all',kind='alle',decisions=decisions)['total'],0)
   self.assertEqual(fail.list_failures(b,'de',kind='karten',decisions={})['total'],1)
 def test_human_confirmation_outweighs_later_name_only_failure(self):
  t=datetime(2026,11,9,19,30,tzinfo=timezone.utc)
  decision={'status':'CONFIRMED_PRINT','reviewedAt':t.isoformat(),'selectedProductId':'273703'}
  later=(t+timedelta(minutes=3)).isoformat()
  self.assertTrue(fail.resolved_after_scan({'seen_at':later,'status':'MULTIPLE_SEARCH_HITS','product_id':''},decision))
  self.assertTrue(fail.resolved_after_scan({'seen_at':later,'status':'PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED','product_id':'273703'},decision))
  self.assertFalse(fail.resolved_after_scan({'seen_at':later,'status':'PRODUCT_ID_NOT_VERIFIED_FOR_CARD','product_id':'999999'},decision))
 def test_new_scan_after_confirmation_remains_visible(self):
  t=datetime(2026,11,9,19,30,tzinfo=timezone.utc)
  decision={'status':'CONFIRMED_PRINT','reviewedAt':t.isoformat()}
  obs={'seen_at':(t+timedelta(minutes=5)).isoformat()}
  self.assertFalse(fail.resolved_after_scan(obs,decision))
  self.assertTrue(fail.resolved_after_scan({'seen_at':(t-timedelta(seconds=10)).isoformat()},decision))
 def test_retry_only_requested_variant(self):
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td);r=retry.retry('de','hgss3-5','v1',base=b)
   self.assertTrue(r['ok'])
   with (b/'queue-de.csv').open() as f:rows=list(csv.DictReader(f))
   self.assertTrue(rows[0]['manual_scan_requested_at'])
   self.assertFalse(rows[1]['manual_scan_requested_at'])
 def test_missing_required_fields_are_visible_instead_of_card_missing(self):
  self.assertEqual(fail.classify('MISSING_REQUIRED_SCAN_FIELDS'),'DATEN_FEHLEN')
  self.assertEqual(fail.classify('FILTER_UNAVAILABLE'),'TECHNISCH')
 def test_no_unknown_queue_row(self):
  with tempfile.TemporaryDirectory() as td:
   b=self.setup(td)
   with self.assertRaisesRegex(ValueError,'card_variant_not_in_current_queue'):retry.retry('de','fake-1','v1',base=b)
if __name__=='__main__':unittest.main()
