import unittest
from unittest.mock import patch
from datetime import date
from pathlib import Path
from anniversary_batch import exact_number,select_rows,import_result,search_query

class AnniversaryTests(unittest.TestCase):
    def card(self,set_id='30th'):
        return dict(card_id='30th-001',name='Owei',local_id='001',set_id=set_id,variants=[dict(id='generated',type='normal')])
    def row(self,i='1',**changes):
        return dict(dict(item_id=i,title='Owei 001/128 Deutsch NM',eligible=True,language='de',condition='nm',sold_date=date.today().isoformat(),price_eur=1.0),**changes)
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

    def test_no_matching_sales_is_not_mislabeled_as_variant_error(self):
        with patch('anniversary_batch.db') as db:
            out=import_result(dict(pages=[dict(status='OK')],rows=[]),self.card(),Path('/unused'))
            self.assertEqual(out['status'],'NO_MATCHING_SALES_30D')
            db.assert_not_called()

    def test_unknown_variant_never_writes(self):
        report=dict(pages=[dict(status='OK')],rows=[self.row(str(i)) for i in range(5)])
        with patch('anniversary_batch.db') as db:
            out=import_result(report,self.card(),Path('/unused'))
            self.assertEqual(out['status'],'CATALOG_VARIANT_REVIEW');db.assert_not_called()
    def test_identity_condition_and_duplicate_filters(self):
        r=self.row()
        rows,reasons=select_rows(dict(rows=[r,r,self.row('2',condition='unknown'),self.row('3',title='Owei 001/128 reverse Deutsch NM'),self.row('4',title='Kokowei 001/128 Deutsch NM')]),self.card())
        self.assertEqual(len(rows),1);self.assertEqual(sum(reasons.values()),3)
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
