#!/usr/bin/env python3
import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from PIL import Image

spec=importlib.util.spec_from_file_location('art',Path(__file__).with_name('resolve-cardtrader-ko-art-prices.py'))
art=importlib.util.module_from_spec(spec);spec.loader.exec_module(art)

class IdentityTests(unittest.TestCase):
    def setUp(self):
        url='https://pokemoncard.co.kr/cards/detail/test123'
        self.row=dict(card_id='official_ko_'+hashlib.sha256(url.encode()).hexdigest()[:24],language_code='ko',identity_count=1,rarity='C',set_id='SV1',local_id='001',native_name='native',image_source_url='https://cards.image.pokemonkorea.co.kr/card.png',source_url=url,source_revision='pin')
        self.raw=dict(url=url,ko_id='test123',lang='ko',rarity='C',set_name='SV1',number='001',name='native',img=self.row['image_source_url'],set_total=78)
        self.exp=dict(id=1,game_id=5,code='SV1')
        self.bp=dict(id=1,game_id=5,category_id=73,expansion_id=1,version='001/078',fixed_properties=dict(collector_number='001',pokemon_rarity='Common'),editable_properties=[dict(name='pokemon_language',possible_values=['kr','jp'])])
    def test_official_metadata_pin(self):
        self.assertEqual(art.pinned_record(self.row,self.raw,'pin')['official_count'],78)
    def test_changed_metadata_or_revision_rejected(self):
        for key,value in [('name','wrong'),('img','wrong'),('set_name','SV2'),('number','002'),('rarity','U'),('url','wrong'),('lang','ja')]:
            with self.subTest(key=key):
                r=dict(self.raw);r[key]=value;self.assertIsNone(art.pinned_record(self.row,r,'pin'))
        self.assertIsNone(art.pinned_record(self.row,self.raw,'wrong'))
    def test_ambiguous_identity_and_rare_prints_rejected(self):
        for key,value in [('identity_count',2),('rarity','RR'),('language_code','ja')]:
            r=dict(self.row);r[key]=value;self.assertIsNone(art.pinned_record(r,self.raw,'pin'))
    def test_blueprint_number_denominator_language_and_finish(self):
        row=dict(self.row,official_count=78)
        self.assertTrue(art.blueprint_matches(row,self.bp,self.exp))
        for version in ['002/078','001/079','Reverse | 001/078','First edition | 001/078']:
            self.assertFalse(art.blueprint_matches(row,dict(self.bp,version=version),self.exp))
        self.assertFalse(art.blueprint_matches(row,dict(self.bp,editable_properties=[]),self.exp))
    def test_both_art_patches_and_separate_controls_required(self):
        self.assertTrue(art.separated([2,3],[[25,25],[30,30],[40,40]]))
        self.assertFalse(art.separated([2,7],[[40,40]]))
        self.assertFalse(art.separated([2,3],[[40,10]]))
        self.assertFalse(art.separated([2,3],[]))
        self.assertFalse(art.separated([2,3],[[40,40],[2,3]]))
    def test_small_or_noncard_image_rejected(self):
        for size in [(206,288),(500,500)]:
            stream=io.BytesIO();Image.new('RGB',size).save(stream,format='PNG')
            with self.assertRaises(ValueError):art.prepare(stream.getvalue())
    def test_untrusted_blueprint_path_rejected(self):
        self.assertIsNone(art.image_url(dict(image=dict(url='https://evil.example/card.jpg'))))
        self.assertIsNone(art.image_url(dict(image=dict(url='/uploads/blueprints/image/../card.jpg'))))

class BatchIsolationTests(unittest.TestCase):
    def run_case(self,provider_error=False):
        rows=[dict(card_id='official_ko_'+str(i),language_code='ko',identity_count=1,rarity='C',set_id='SV1',local_id=str(i+1),native_name='native'+str(i),official_count=4,image_source_url='https://cards.image.pokemonkorea.co.kr/'+str(i)+'.png',source_url='official',source_revision='pin',old_variants=[],old_updated=None,old_status=None) for i in range(2)]
        exp=dict(id=1,game_id=5,code='SV1');bps=[]
        for i in range(4):bps.append(dict(id=i+1,name='card'+str(i+1),game_id=5,category_id=73,expansion_id=1,version=str(i+1)+'/4',fixed_properties=dict(collector_number=str(i+1),pokemon_rarity='Common'),editable_properties=[dict(name='pokemon_language',possible_values=['kr'])],image=dict(url='/uploads/blueprints/image/'+str(i+1)+'.png')))
        offer=dict(id=123,properties_hash=dict(condition='Near Mint'))
        products={str(i+1):[offer] for i in range(4)}
        black=io.BytesIO();Image.new('RGB',(500,700),'black').save(black,format='PNG')
        white=io.BytesIO();Image.new('RGB',(500,700),'white').save(white,format='PNG')
        def response(req,timeout):
            url=req.full_url
            if '/blueprints/export' in url:
                if provider_error:raise TimeoutError('provider unavailable')
                return io.BytesIO(json.dumps(bps).encode())
            if '/marketplace/products' in url:return io.BytesIO(json.dumps(products).encode())
            if url.endswith('/1.png') and 'pokemonkorea' in url:return io.BytesIO(b'not an image')
            if url.endswith('/0.png') or url.endswith('/image/1.png'):return io.BytesIO(black.getvalue())
            return io.BytesIO(white.getvalue())
        original=Path.read_text
        def read(p,*a,**kw):
            if str(p)=='/home/tv/cardshop/platform/.env':return 'CARDTRADER_API_TOKEN=test-only'
            return original(p,*a,**kw)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);inventory=directory/'inventory';inventory.mkdir()
            (inventory/'1.json').write_text(json.dumps(dict(expansion=exp,blueprints=bps,products=products)))
            report=directory/'result.json'
            argv=['reader','--apply','--inventory-dir',str(inventory),'--report',str(report)]
            with patch('sys.argv',argv),patch.object(Path,'read_text',read),patch.object(art,'load_targets',return_value=rows),patch.object(art.urllib.request,'urlopen',response),patch.object(art.time,'sleep'),patch.object(art.m,'listing_amount',return_value=Decimal('1')),patch.object(art.m.ko.retail,'db',return_value='[]'),patch.object(art.m.ko,'apply_updates',return_value=dict(prices=1,variants=1,history=1)) as writer,contextlib.redirect_stdout(io.StringIO()):
                try:art.main()
                except SystemExit as e:self.assertTrue(provider_error);self.assertEqual(e.code,1)
                calls=writer.call_count
                if calls:self.assertEqual(len(writer.call_args.args[0]),1)
            return calls,json.loads(report.read_text())
    def test_bad_image_skipped_valid_card_imported(self):
        calls,r=self.run_case()
        self.assertEqual(calls,1);self.assertEqual(r['matched'],1)
        self.assertEqual(len(r['image_failures']),1);self.assertEqual(r['errors'],[])
        self.assertTrue(r['import_gate']['allowed'])
    def test_provider_failure_blocks_batch(self):
        calls,r=self.run_case(True)
        self.assertEqual(calls,0);self.assertEqual(len(r['errors']),1)
        self.assertFalse(r['import_gate']['allowed'])

if __name__=='__main__':unittest.main()
