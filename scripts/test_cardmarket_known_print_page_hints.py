import csv,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('print_hints',ROOT/'cardmarket-apply-print-page-hints.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
class Tests(unittest.TestCase):
 def test_known_urls_are_never_print_verified(self):
  data=json.loads((ROOT.parent/'config/cardmarket-known-print-page-hints.json').read_text())
  self.assertEqual(set(data),{'basep-1','basep-4','base3-1'})
  for card,rule in data.items():
   for variant,x in rule['variants'].items():
    self.assertFalse(x['printVerified']);self.assertTrue(x['slug'].endswith(rule['collectorSuffix']))
  self.assertEqual(data['basep-1']['variants']['zqq5g2u9n315kaa1q7ordzv42kgf7pxg']['slug'],'Pikachu-WP1')
  self.assertEqual(data['basep-4']['variants']['us0ioug2avlzsvzo3l1p89ztq94zgllrr']['slug'],'Pikachu-WP4')
  self.assertEqual(data['base3-1']['variants']['qi4hl156ztevhio39njr8t2eqgmqjdlals']['slug'],'Aerodactyl-V3-FO1')
  self.assertEqual(data['base3-1']['variants']['677yasikk9iggi3g0o8t']['slug'],'Aerodactyl-V1-FO1')
 def test_both_languages_and_no_conflation(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'config').mkdir()
   (root/'config/cardmarket-known-print-page-hints.json').write_text((ROOT.parent/'config/cardmarket-known-print-page-hints.json').read_text())
   fields=['cardyssey_karte','variante_id','set_id','cardmarket_ids','routing_state']
   for lang in ('de','en'):
    with (root/f'queue-{lang}.csv').open('w',encoding='utf-8-sig',newline='') as f:
     w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
     for card,vals in [('base3-1',['113thq6t8j5zpn9aq2h12bi21oykxyl2','qi4hl156ztevhio39njr8t2eqgmqjdlals']),('basep-4',['3a83wf50ts0izkobrpvrjbdwt','us0ioug2avlzsvzo3l1p89ztq94zgllrr'])]:
      for var in vals:w.writerow({'cardyssey_karte':card,'variante_id':var,'set_id':card.rsplit('-',1)[0],'cardmarket_ids':'12345','routing_state':'SOURCE_ONLY'})
    result=h.apply(lang,base=root,root=root)
    self.assertEqual(result['knownPages'],4)
    with (root/f'queue-{lang}.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    self.assertTrue(all(x['reference_print_verified']=='NO' and x['cardmarket_ids']=='12345' for x in rows))
    self.assertTrue(all('/'+lang+'/Pokemon/' in x['reference_product_url'] for x in rows))
    self.assertTrue('V1-FO1' in rows[0]['reference_product_url']);self.assertTrue('V3-FO1' in rows[1]['reference_product_url'])
 def test_scanner_checks_reference_before_search_and_never_confirms_price(self):
  s=(ROOT/'cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
  self.assertIn('reference_page_used=$true',s)
  self.assertIn("$out.status='PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED'",s)
  self.assertIn("[string]$case.reference_print_verified -eq 'NO'",s)
  a=s.index("$out.reference_page_used -eq $true");b=s.index("} elseif ($candidateId -ne",a)
  self.assertNotIn('identity_confirmed = $true',s[a:b]);self.assertNotIn('sample_median_eur=',s[a:b])
if __name__=='__main__':unittest.main()
