import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sp=importlib.util.spec_from_file_location('print_hints',source_path('cardmarket-apply-print-page-hints.py'));h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
class Tests(unittest.TestCase):
 def test_known_urls_are_never_print_verified(self):
  data=json.loads((ROOT.parent/'config/cardmarket-known-print-page-hints.json').read_text())
  self.assertEqual(set(data),{'basep-1','basep-4','base3-1','sv01-013'})
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
 def test_felori_standard_vs_special_are_independent(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'config').mkdir()
   (root/'config/cardmarket-known-print-page-hints.json').write_text((ROOT.parent/'config/cardmarket-known-print-page-hints.json').read_text())
   fields=['cardyssey_karte','variante_id','set_id','cardmarket_ids','routing_state','drucktyp','stempel','foil','sonderdruck']
   names=[('endfynwn4n10gzq','Normal','[]',''),('cm4kqul3x1bwlz1f','Reverse','[]',''),('curated:de:sv01:013:grass-stamp','Reverse','["grass-symbol"]','Grass symbol'),('curated:de:sv01:013:holo','Holo','[]','')]
   for lang in ('de','en'):
    with (root/f'queue-{lang}.csv').open('w',encoding='utf-8-sig',newline='') as f:
     w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
     for var,typ,st,foil in names:
      w.writerow({'cardyssey_karte':'sv01-013','variante_id':var,'set_id':'sv01','cardmarket_ids':'689763,691000','routing_state':'UNVERIFIED','drucktyp':typ,'stempel':st,'foil':foil,'sonderdruck':''})
    result=h.apply(lang,base=root,root=root)
    self.assertEqual(result['standardOfferFilterCandidates'],2)
    with (root/f'queue-{lang}.csv').open(encoding='utf-8-sig') as f:rows={x['variante_id']:x for x in csv.DictReader(f)}
    for var in ('endfynwn4n10gzq','cm4kqul3x1bwlz1f'):
     self.assertEqual(rows[var]['catalog_singleton_id'],'689763')
     self.assertEqual(rows[var]['catalog_expansion_id'],'5223')
     self.assertEqual(rows[var]['reference_standard_filter_supported'],'YES')
     self.assertEqual(rows[var]['reference_print_verified'],'NO')
     self.assertEqual(rows[var]['cardmarket_ids'],'689763,691000')
    for var in ('curated:de:sv01:013:grass-stamp','curated:de:sv01:013:holo'):
     self.assertEqual(rows[var]['catalog_singleton_id'],'')
     self.assertEqual(rows[var]['reference_standard_filter_supported'],'NO')
     self.assertIn('/Sprigatito-V2-SVI013',rows[var]['reference_product_url'])
 def test_scanner_checks_reference_before_search_and_never_confirms_price(self):
  s=(source_path('cardmarket-language-browser-collector.ps1')).read_text(encoding='utf-8-sig')
  self.assertIn('reference_page_used=$true',s)
  self.assertIn("$out.status='PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED'",s)
  self.assertIn("[string]$case.reference_print_verified -eq 'NO'",s)
  a=s.index("$out.reference_page_used -eq $true");b=s.index("} elseif ($candidateId -ne",a)
  self.assertNotIn('identity_confirmed = $true',s[a:b]);self.assertNotIn('sample_median_eur=',s[a:b])
  self.assertIn("[string]$case.reference_standard_filter_supported -ne 'YES'",s)
  self.assertIn("$out.standard_offer_filter_candidate=$true",s)
  self.assertIn('expected_reverse_holo',s)
  self.assertIn('all_pages_complete',s)

 def test_cross_locale_vintage_page_is_card_only(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'config').mkdir()
   hints=ROOT.parent/'config/cardmarket-known-print-page-hints.json'
   (root/'config'/hints.name).write_bytes(hints.read_bytes())
   fields=['cardyssey_karte','variante_id','set_id','kartennummer','drucktyp','stempel',
           'sonderdruck','cardmarket_ids','known_url','routing_state']
   expected={'base1':('8','Machamp-V1-BS8','1523','273703','schattenlos'),
             'base2':('13','Venomoth-V1-JU13','1525','273810','Fehlendes Erweiterungssymbol'),
             'base3':('15','Zapdos-V1-FO15','1526','273883','Copyright 1999-2000')}
   guards={'base1':'Base-Set','base2':'Jungle','base3':'Fossil'}
   for lang in ('de','en'):
    with (root/f'queue-{lang}.csv').open('w',encoding='utf-8-sig',newline='') as f:
     writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
     for sid,(number,slug,_,pid,subtype) in expected.items():
      card=dict(cardyssey_karte=f'{sid}-{number}',set_id=sid,kartennummer=number,
                drucktyp='Holo',stempel='[]',routing_state='SOURCE_ONLY')
      url=f'https://www.cardmarket.com/en/Pokemon/Products/Singles/{guards[sid]}/{slug}'
      writer.writerow(dict(card,variante_id='base',cardmarket_ids=pid,known_url=url if lang=='en' else ''))
      writer.writerow(dict(card,variante_id='sub',cardmarket_ids='',sonderdruck=subtype))
   products={pid:{'idExpansion':int(exp)} for _,_,exp,pid,_ in expected.values()}
   counts=h.apply('de',base=root,root=root,products=products)
   with (root/'queue-de.csv').open(encoding='utf-8-sig') as f:
    cases=[r for r in csv.DictReader(f) if r['variante_id']=='sub']
   self.assertEqual(counts['vintagePages'],3)
   for row in cases:
    sid=row['set_id'];_,slug,_,pid,_=expected[sid]
    self.assertEqual(row['reference_product_id'],pid)
    self.assertEqual(row['reference_product_url'],f'https://www.cardmarket.com/de/Pokemon/Products/Singles/{guards[sid]}/{slug}')
    self.assertEqual(row['reference_print_verified'],'NO')
    self.assertEqual(row['reference_standard_filter_supported'],'NO')
    self.assertEqual(row['exact_print_filter_supported'],'false')
    self.assertEqual(row['cardmarket_ids'],'')

 def test_stamp_routes_validate_original_set_number_and_scope(self):
  from cardmarket_print_routes import stamp_route, subset_urls
  row={'set_id':'dp6','kartennummer':'144','stempel':'["David Cohen"]'}
  correct='https://www.cardmarket.com/en/Pokemon/Products/Singles/WCD-2009/Mewtwo-LVX-WCD09LA-144'
  wrong=[
      correct.replace('09LA','09GE'),
      correct.replace('144','140'),
      correct.replace('WCD-2009','WCD-2008'),
      correct.replace('www.cardmarket.com','evil.example'),
  ]
  route=stamp_route(row)
  self.assertEqual(route,'WORLD_CHAMPIONSHIPS')
  self.assertEqual(subset_urls(row,[correct,*wrong],'de',route),[correct.replace('/en/','/de/')])
  self.assertEqual(stamp_route({**row,'stempel':'["Jason Klaczynski"]'}),route)
  self.assertEqual(stamp_route({**row,'stempel':'["michael-pramawat"]'}),route)
  self.assertEqual(stamp_route({**row,'set_id':'sv05'}),'')

if __name__=='__main__':unittest.main()
