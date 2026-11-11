import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('crosslang',source_path('cardmarket-build-cross-language-page-cache.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CrossLanguageCacheTests(unittest.TestCase):
    def row(self,card,pid='836551',foil='',variant='normal',set_id='sv10.5w'):
        return {'cardyssey_karte':card,'variante_id':variant,'set_id':set_id,
        'drucktyp':'Normal','foil':foil,'stempel':'[]','sonderdruck':'',
        'catalog_singleton_id':pid,'catalog_expansion_id':'5001'}
    def test_precise_identity_and_language_without_query_leak(self):
        with tempfile.TemporaryDirectory() as t:
            b=Path(t)
            for lang in ('de','en'):
                rows=[self.row('regular'),self.row('special',foil='Masterball'),
                      self.row('different',pid='11001' if lang=='de' else '11002')]
                with (b/f'queue-{lang}.csv').open('w',encoding='utf-8-sig',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
                with (b/f'browser-observations-{lang}.jsonl').open('w') as f:
                    for row in rows:
                        f.write(json.dumps({'card_id':row['cardyssey_karte'],'variant_id':'normal',
                           'set_id':row['set_id'],'identity_confirmed':True,
                           'catalog_direct_id_verified':True,'card_number_url_verified':True,
                           'product_id':row['catalog_singleton_id'],
                           'url':f'https://www.cardmarket.com/{lang}/Pokemon/Products/Singles/White-Flare/Joltik-V1-WHT033?language=3&isReverseHolo=Y'})+'\n')
            out=m.build(base=b)
            self.assertEqual(len(out['entries']),2)
            self.assertEqual(out['entries']['en|regular|normal']['productId'],'836551')
            self.assertEqual(out['entries']['en|regular|normal']['url'],
               'https://www.cardmarket.com/en/Pokemon/Products/Singles/White-Flare/Joltik-V1-WHT033')
            self.assertFalse(out['entries']['en|regular|normal']['exactPrintVerified'])
            self.assertNotIn('en|special|normal',out['entries'])
            self.assertNotIn('en|different|normal',out['entries'])
    def test_host_and_uri_rejected(self):
        self.assertIsNone(m.page_url('https://www.cardmarket.com.evil.org/de/Pokemon/Products/Singles/A/B','en'))
        self.assertIsNone(m.page_url('https://evil.org/de/Pokemon/Products/Singles/A/B','en'))
        self.assertIsNone(m.page_url('https://www.cardmarket.com@evil.org/de/Pokemon/Products/Singles/A/B','en'))
        self.assertIsNone(m.page_url('https://www.cardmarket.com/de/Pokemon/Products/Singles/A/../../../B','en'))
if __name__=='__main__':unittest.main()
