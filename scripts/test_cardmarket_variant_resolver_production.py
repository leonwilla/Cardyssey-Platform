"""Safety regressions for user-supplied variant-resolver design."""
import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
p=ROOT/'scripts/cardmarket_variant_resolver.py'
s=importlib.util.spec_from_file_location('resolver_prod',p)
m=importlib.util.module_from_spec(s)
import sys;sys.modules[s.name]=m;s.loader.exec_module(m)

class ResolverTests(unittest.TestCase):
    def product(self,**extra):
        args=dict(product_id='836551',set_slug='White-Flare-Additionals',
          product_url='https://www.cardmarket.com/de/Pokemon/Products/Singles/White-Flare-Additionals/Joltik-V2-xWHT033',
          number='033',title='Wattzapf [Surprise Attack]',
          version='V2',price_trend=7.58,confirmed_product_page=True)
        args.update(extra);return m.Product(**args)
    def test_v2_and_high_price_not_masterball_proof(self):
        p=self.product()
        x=m.classify_product(p,valid_set_slugs={'White-Flare-Additionals'},matched_number='033')
        self.assertEqual(x.print_type,'unknown')
        self.assertEqual(x.confidence,'LOW')
        self.assertTrue(x.review_required)
    def test_hard_wrong_set_number_or_host(self):
        for props,slugs,number in [
            ({'set_slug':'White-Flare'}, {'White-Flare-Additionals'}, '033'),
            ({}, {'White-Flare-Additionals'}, '133'),
            ({'product_url':'https://evil.example/x'}, {'White-Flare-Additionals'}, '033'),
            ({'confirmed_product_page':False},{'White-Flare-Additionals'},'033')]:
            x=m.classify_product(self.product(**props),valid_set_slugs=slugs,matched_number=number)
            self.assertEqual(x.print_type,'unknown')
    def test_unambiguous_title_and_human_verified_roi(self):
        x=m.classify_product(self.product(version='Master Ball Foil'),valid_set_slugs={'White-Flare-Additionals'},matched_number='033')
        self.assertEqual((x.print_type,x.confidence),('masterball','HIGH'))
        x=m.classify_product(self.product(),valid_set_slugs={'White-Flare-Additionals'},matched_number='033',
            foil_image_evidence={'method':'phash','print':'masterball','subjectProductId':'836551','reviewer':'bot'})
        self.assertEqual(x.print_type,'unknown')
        x=m.classify_product(self.product(),valid_set_slugs={'White-Flare-Additionals'},matched_number='033',
            foil_image_evidence={'method':'human_verified_roi','print':'masterball','subjectProductId':'836551','reviewer':'human'})
        self.assertEqual(x.print_type,'masterball')
    def test_master_ball_trainer_name_is_not_masterball_foil(self):
        x=m.classify_product(self.product(name='Master Ball',title='Master Ball',version='V2'),
            valid_set_slugs={'White-Flare-Additionals'},matched_number='033')
        self.assertEqual(x.print_type,'unknown')
    def test_price_heuristic_does_not_classify(self):
        x=m.price_hint([self.product(product_id='111',price_trend=.21),
                        self.product(product_id='222',price_trend=7.58)])
        self.assertTrue(x['reviewSuggestion'])
        self.assertFalse(x['printVerified'])
        self.assertFalse(x['safeToAutoPublish'])
    def test_comment_regex_and_negations(self):
        self.assertEqual(m.classified_comment('Masterball near mint','masterball'),'positive')
        self.assertEqual(m.classified_comment('nur Pokéball','masterball'),'contradiction')
        self.assertEqual(m.classified_comment('no master ball','masterball'),'ambiguous')
        self.assertEqual(m.classified_comment('Pokeball / Masterball','masterball'),'contradiction')
        self.assertEqual(m.classified_comment('MB','masterball'),'shorthand_hint')
        self.assertEqual(m.classified_comment('PB','pokeball'),'shorthand_hint')
        self.assertEqual(m.classified_comment('no MB','masterball'),'ambiguous')
        self.assertEqual(m.classified_comment('PB / MB','masterball'),'contradiction')
        self.assertEqual(m.classified_comment('','masterball'),'missing')
        self.assertEqual(m.classified_comment('play mat new','stamp:play-pokemon'),'missing')
    def offer(self,oid,price,**kw):
        x=dict(offer_id=oid,product_id='836551',language='de',
               condition='NM',signed=False,altered=False,graded=False,
               bundle=False,is_reverse=True,comment='Master Ball',price_eur=price)
        x.update(kw);return x
    def price(self,offers,**kw):
        x=dict(operation='price',expected=dict(language='de',product_id='836551',
                 print='masterball',confirmed_print_identity=False),offers=offers,
                 pagination=dict(all_pages_fetched=True,capped=False,total_offers=len(offers)))
        x.update(kw);return x
    def test_unconfirmed_not_published_even_complete(self):
        x=m.price_diagnostic(self.price([self.offer('1',5),self.offer('2',8)]))
        self.assertEqual(x['accepted_offers'],2)
        self.assertFalse(x['safe_to_publish'])
    def test_complete_verified_exclusions_and_iqr(self):
        p=self.price([self.offer(str(i),v) for i,v in
                      enumerate([5.6,5.7,5.8,5.9,6,6.1,6.2,6.3,.02],1)])
        p['expected']['confirmed_print_identity']=True
        p['product_wide_trend']=7.4
        x=m.price_diagnostic(p)
        self.assertEqual(x['accepted_offers'],9)
        self.assertEqual(x['iqr_removed'],1)
        self.assertEqual(x['median_iqr_diagnostic_eur'],'5.95')
        self.assertTrue(x['safe_to_publish'])
    def test_incomplete_blocks_publication(self):
        p=self.price([self.offer('a',7),self.offer('b',7.8)])
        p['expected']['confirmed_print_identity']=True
        p['pagination']['all_pages_fetched']=False
        x=m.price_diagnostic(p)
        self.assertFalse(x['safe_to_publish'])
    def test_japanese_masterball_without_explicit_comment_unknown(self):
        p=self.price([self.offer('a',8,language='ja',comment=''),
                      self.offer('b',9,language='ja',comment='masterball holo')],
                     expected={'language':'ja','product_id':'836551','print':'masterball',
                               'confirmed_print_identity':True})
        x=m.price_diagnostic(p)
        self.assertEqual(x['accepted_offers'],1)
        self.assertEqual(x['rejected'].get('PRINT_COMMENT_MISSING'),1)
    def test_shorthand_only_usable_with_independent_print_confirmation(self):
        row=self.offer('a',7.0,comment='NM, MB')
        self.assertEqual(m.price_diagnostic(self.price([row]))['accepted_offers'],0)
        doc=self.price([row])
        doc['expected']['confirmed_print_identity']=True
        out=m.price_diagnostic(doc)
        self.assertEqual(out['accepted_offers'],1)
        self.assertTrue(out['safe_to_publish'])
    def test_negative_listing_on_masterball_page(self):
        p=self.price([self.offer('a',.5,comment='only Pokeball reverse'),
                      self.offer('b',6.4)])
        x=m.price_diagnostic(p)
        self.assertEqual(x['accepted_offers'],1)
        self.assertEqual(x['rejected']['PRINT_COMMENT_CONTRADICTION'],1)
    def test_stamps_not_prematurely_accepted(self):
        p=self.price([self.offer('a',3,comment='play!')],expected={
           'language':'de','product_id':'836551','print':'stamp','confirmed_print_identity':False})
        self.assertEqual(m.price_diagnostic(p)['accepted_offers'],0)

if __name__=='__main__':unittest.main()
