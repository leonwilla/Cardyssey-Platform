import unittest
import tempfile
import json
from datetime import datetime,timezone
from unittest.mock import patch
from datetime import date
from pathlib import Path
from anniversary_batch import exact_number,select_rows,import_result,search_query,explicit_print_variant,recent_verified_report

class AnniversaryTests(unittest.TestCase):
    def card(self,set_id='30th'):
        return dict(card_id='30th-001',name='Owei',local_id='001',set_id=set_id,variants=[dict(id='generated',type='normal')])
    def row(self,i='1',**changes):
        return dict(dict(item_id=i,title='Owei 001/128 Deutsch NM',eligible=True,language='de',condition='nm',sold_date=date.today().isoformat(),price_eur=1.0),**changes)
    def test_incremental_reuse_requires_identical_cutoff_and_complete_boundary(self):
        from anniversary_batch import recent_verified_report
        from datetime import datetime,timezone
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            report={'config':{'query':'Raichu 064/193','language':'de','sold_since':'2026-11-02'},
                    'pages':[{'status':'OK'}],'collected_at':datetime.now(timezone.utc).isoformat(),
                    'incremental_boundary_reached':True,'rows':[]}
            (path/'sales.json').write_text(json.dumps(report))
            self.assertIsNotNone(recent_verified_report(path,'Raichu 064/193',sold_since='2026-11-02'))
            self.assertIsNone(recent_verified_report(path,'Raichu 064/193',sold_since='2026-11-01'))
            report['incremental_boundary_reached']=False
            (path/'sales.json').write_text(json.dumps(report))
            self.assertIsNone(recent_verified_report(path,'Raichu 064/193',sold_since='2026-11-02'))

    def test_reuses_recent_complete_sold_pages_without_old_date_cutoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            report=dict(config=dict(query='Tannza 001/198',language='de',max_age_days=30),
                collected_at=datetime.now(timezone.utc).isoformat(),pages=[dict(status='OK')],
                rows=[dict(exclusions='SALE_TOO_OLD',eligible=False),
                      dict(exclusions='OFFER_OR_STRIKETHROUGH_PRICE;SALE_TOO_OLD',eligible=False)])
            (d/'sales.json').write_text(json.dumps(report))
            replay=recent_verified_report(d,'Tannza 001/198')
            self.assertTrue(replay['reused_recent_sales_page'])
            self.assertTrue(replay['rows'][0]['eligible'])
            self.assertFalse(replay['rows'][1]['eligible'])
            self.assertIsNone(recent_verified_report(d,'Other card'))

    def test_search_queries_include_print_identity(self):
        self.assertEqual(search_query(self.card('30th-c')), 'Owei 001/030 30 Jahre')
        self.assertEqual(search_query(self.card('30th')), 'Owei 001/128 30 Jahre')
        c=self.card('mep'); c['local_id']='099'
        self.assertEqual(search_query(c), 'Owei MEP 099 deutsch')

    def test_number_boundaries_and_set(self):
        c=self.card()
        self.assertTrue(exact_number('Owei 1 / 128',c))
        for t in ['Owei 11/128','Owei 001/030','Owei 001/1280','Owei 001/128abc']:
            self.assertFalse(exact_number(t,c))
        self.assertTrue(exact_number('Owei 001/030',self.card('30th-c')))
    def test_modern_set_hash_number_requires_set_identity(self):
        c=self.card('sv02');c.update(local_id='064',name='Raichu',set_name='Entwicklungen in Paldea',denominator=193)
        self.assertTrue(exact_number('Pokémon Raichu Entwicklungen in Paldea #64 NM DE',c))
        self.assertTrue(exact_number('Raichu PAL Nr. 064 deutsch NM',c))
        for title in ('Raichu #64 NM DE', 'Raichu #65 Entwicklungen in Paldea NM DE',
                      'Raichu #64 #65 Entwicklungen in Paldea NM DE',
                      'Raichu 064/198 Entwicklungen in Paldea #64 NM DE'):
            self.assertFalse(exact_number(title,c),title)
        self.assertFalse(exact_number('Owei #1 30 Jahre',self.card()))

    def test_promo_requires_mep(self):
        c=self.card('mep');c['local_id']='095'
        self.assertTrue(exact_number('Lucario MEP 095 NM',c))
        for t in ['Lucario 095 NM','Lucario MEP 095/128','Lucario MEP 0950']:
            self.assertFalse(exact_number(t,c))
    def test_all_30_day_sales_counted_without_arbitrary_30_sale_cap(self):
        report=dict(rows=[self.row(str(i)) for i in range(40)])
        rows,_=select_rows(report,self.card())
        self.assertEqual(len(rows),40)

    def test_explicit_variant_never_assumes_unmarked_normal(self):
        self.assertEqual(explicit_print_variant('Raichu Reverse Holo Deutsch NM'),'REVERSE')
        self.assertEqual(explicit_print_variant('Raichu Non-Holo Deutsch NM'),'NORMAL')
        self.assertIsNone(explicit_print_variant('Raichu Holo Deutsch NM'))
        self.assertIsNone(explicit_print_variant('Raichu Reverse Non-Holo NM'))

    def test_modern_print_defaults_normal_and_keeps_reverse_separate(self):
        card=dict(card_id='sv02-064',name='Raichu',local_id='064',set_id='sv02',
                  denominator=193,set_name='Entwicklungen in Paldea',
                  variants=[dict(id='normal-id',type='Normal',legacyVariant='NORMAL'),
                            dict(id='reverse-id',type='Reverse',legacyVariant='REVERSE')])
        explicit=self.row('reverse',url='test',title='Raichu 064/193 Entwicklungen in Paldea Reverse Holo Deutsch NM')
        unmarked=self.row('unmarked',url='test',condition='unknown',title='Raichu 064/193 Entwicklungen in Paldea Deutsch')
        report=dict(pages=[dict(status='OK')],rows=[explicit,unmarked])
        def fake_db(query):
            if query.startswith('SELECT variants'):return json.dumps(card['variants'])
            if query.startswith('SELECT COALESCE'):return '[]'
            return ''
        today=date.today().isoformat()
        def fake_history(card_id,variant_id):
            key='reverse' if variant_id=='reverse-id' else 'unmarked'
            return [dict(item_id=key,sold_on=today,sold_eur=1.0,title=key,url='test',condition_assumed=key=='unmarked')]
        with tempfile.TemporaryDirectory() as temp, \
             patch('anniversary_batch.db',side_effect=fake_db) as db, \
             patch('anniversary_batch.save_sales') as save, \
             patch('anniversary_batch.stored_sales',side_effect=fake_history):
            outcome=import_result(report,card,Path(temp))
            self.assertEqual(outcome['status'],'IMPORTED')
            self.assertEqual({v['variant_id'] for v in outcome['variants_imported']},{'reverse-id','normal-id'})
            self.assertEqual(save.call_count,2)
            normal_rows=next(c.args[2] for c in save.call_args_list if c.args[1]=='normal-id')
            self.assertTrue(normal_rows[0]['condition_assumed'])
            self.assertTrue(normal_rows[0]['variant_assumed'])
            inserts=[c.args[0] for c in db.call_args_list if c.args[0].startswith('BEGIN; INSERT')]
            self.assertEqual(len(inserts),2)

    def test_image_identity_can_substitute_number_but_not_condition_or_language(self):
        card=dict(card_id='sv02-064',name='Raichu',local_id='064',set_id='sv02',
                  denominator=193,set_name='Entwicklungen in Paldea',variants=[])
        row=self.row(title='Raichu Entwicklungen in Paldea Deutsch NM',image_identity_verified=True)
        selected,_=select_rows(dict(rows=[row]),card)
        self.assertEqual(len(selected),1)
        for change in (dict(image_identity_verified=False),dict(language='en'),dict(title='Raichu 065/193 Entwicklungen in Paldea Deutsch NM')):
            selected,_=select_rows(dict(rows=[row|change]),card)
            self.assertFalse(selected,change)

    def test_no_matching_sales_is_not_mislabeled_as_variant_error(self):
        with patch('anniversary_batch.db') as db:
            out=import_result(dict(pages=[dict(status='OK')],rows=[]),self.card(),Path('/unused'))
            self.assertEqual(out['status'],'NO_MATCHING_SALES')
            db.assert_not_called()

    def test_unknown_variant_never_writes(self):
        report=dict(pages=[dict(status='OK')],rows=[self.row(str(i)) for i in range(5)])
        with patch('anniversary_batch.db') as db:
            out=import_result(report,self.card(),Path('/unused'))
            self.assertEqual(out['status'],'CATALOG_VARIANT_REVIEW');db.assert_not_called()
    def test_identity_condition_and_duplicate_filters(self):
        r=self.row()
        rows,reasons=select_rows(dict(rows=[r,r,self.row('2',condition='unknown'),self.row('3',title='Owei 001/128 reverse Deutsch NM'),self.row('4',title='Kokowei 001/128 Deutsch NM')]),self.card())
        self.assertEqual(len(rows),2);self.assertEqual(sum(reasons.values()),2)
        self.assertTrue(next(x for x in rows if x['item_id']=='2')['condition_assumed'])
    def test_complete_sets_and_other_card_numbers_rejected(self):
        titles=['Owei 001/128 bis 052/128 Komplettset DE NM','Owei 001/128 030/128 Deutsch NM','Owei 001/128 Deutsch NM']
        rows=[self.row(str(i),title=t) for i,t in enumerate(titles)]
        accepted,reasons=select_rows(dict(rows=rows),self.card())
        self.assertEqual(len(accepted),1)
        self.assertEqual(reasons.get('OTHER_PRINT_OR_SEALED'),2)

    def test_incomplete_report_never_writes(self):
        with patch('anniversary_batch.db') as db:
            self.assertEqual(import_result(dict(pages=[dict(status='SERVICE_ERROR')],rows=[]),self.card(),Path('/unused'))['status'],'FETCH_INCOMPLETE')
            db.assert_not_called()
