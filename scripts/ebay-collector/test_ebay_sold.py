import unittest
from ebay_sold import money, parse, page_state, summary


def fixture(extra='', sold='Verkauft 15. Okt 2026', cls='s-item', title='Machomei 8/102 deutsch holo'):
    return f'<li class="{cls}"><a href="https://www.ebay.de/itm/123456789012"><h3 class="{cls}__title">{title}</h3></a><span>{sold}</span><span class="{cls}__price">EUR 25,50</span>{extra}</li>'


class Tests(unittest.TestCase):
    def test_money(self):
        for raw, want in [('EUR 1.234,56',1234.56),('EUR 1,234.56',1234.56),('25,50 €',25.5),('EUR 1.234',1234),('US $25.50',None),('EUR 5 bis EUR 10',None)]:
            self.assertEqual(money(raw), want)
    def test_sale(self):
        row=parse(fixture(),['8/102','deutsch'])[0]
        self.assertTrue(row['eligible'])
        self.assertIsNone(row['shipping_eur'])
    def test_ended_not_sale(self):
        self.assertFalse(parse(fixture(sold='Beendet 15. Okt 2026'))[0]['eligible'])
        self.assertFalse(parse(fixture(sold='3 verkauft'))[0]['eligible'])
    def test_offer(self):
        self.assertFalse(parse(fixture('Preisvorschlag akzeptiert'))[0]['eligible'])
        self.assertFalse(parse(fixture('<s>EUR 25,50</s>'))[0]['eligible'])
    def test_matching_and_bundle(self):
        self.assertFalse(parse(fixture(),['englisch'])[0]['eligible'])
        self.assertFalse(parse(fixture(title='Machomei PSA 10'))[0]['eligible'])
    def test_new_layout_and_dedupe(self):
        self.assertTrue(parse(fixture(cls='s-card'))[0]['eligible'])
        self.assertEqual(len(parse(fixture()*2)),1)
    def test_blocks(self):
        self.assertEqual(page_state('<title>Pardon Our Interruption</title>'),'BLOCKED')
        self.assertEqual(page_state('<input type="password">'),'LOGIN_REQUIRED')
        self.assertEqual(page_state('',status=429),'BLOCKED')
        self.assertEqual(page_state(fixture(title='Robot Pokemon')),'OK')
    def test_german_challenge(self):
        self.assertEqual(page_state('<title>Sicherheitsmaßnahme | eBay</title>'), 'BLOCKED')
        self.assertEqual(page_state('<form id="captcha_form"></form>'), 'BLOCKED')

    def test_listing_thumbnail_capture_and_rejection(self):
        img='<img src="https://i.ebayimg.com/images/g/sample/s-l160.jpg">'
        row=parse(fixture(extra=img))[0]
        self.assertEqual(row['image_url'],'https://i.ebayimg.com/images/g/sample/s-l160.jpg')
        self.assertFalse(row['image_verified'])
        self.assertIsNone(parse(fixture(extra='<img src="https://example.com/evil.jpg">'))[0]['image_url'])
        self.assertIsNone(parse(fixture(extra='<img src="http://i.ebayimg.com/img.jpg">'))[0]['image_url'])
        self.assertIsNone(parse(fixture(extra='<img src="https://i.ebayimg.com.evil.com/img.jpg">'))[0]['image_url'])

    def test_small_sample(self):
        self.assertIsNone(summary(parse(fixture()),5)['estimated_market_value_eur'])

if __name__ == '__main__': unittest.main()

class HardenedTests(unittest.TestCase):
    def test_css_hidden_price(self):
        h=fixture().replace('s-item__price','s-item__price strikethrough')
        self.assertFalse(parse(h)[0]['eligible'])
    def test_shipping_new_layout(self):
        h=fixture('<div class="s-card__attribute-row">+EUR 1,10 · 2-3 Tage Lieferung</div>',cls='s-card')
        self.assertEqual(parse(h)[0]['shipping_eur'],1.1)
        self.assertEqual(parse(fixture('<div class="s-card__attribute-row">Gratis Lieferung</div>'))[0]['shipping_eur'],0)
    def test_accessibility_text(self):
        h=fixture().replace('</h3>','<span class="clipped">Wird in neuem Fenster geöffnet</span></h3>')
        self.assertEqual(parse(h)[0]['title'],'Machomei 8/102 deutsch holo')
    def test_exact_date(self):
        from ebay_sold import sold_date
        self.assertEqual(sold_date('Verkauft 20. Okt 2026 Machomei')[0],'2026-10-20')
        self.assertIsNone(sold_date('Verkauft 31. Feb 2026')[0])
        self.assertEqual(sold_date('Sold Oct 20, 2026')[0],'2026-10-20')
    def test_identity(self):
        from ebay_sold import classify
        t=classify('Machomei 008/102 Deutsch 1. Edition Reverse Holo Near Mint')
        self.assertEqual((t['card_number'],t['language'],t['edition'],t['variant'],t['condition']),('8/102','de','first','reverse','nm'))
        self.assertEqual(classify('Machomei holo')['edition'],'unknown')
        self.assertEqual(classify('Machomei LP / MP')['condition'],'conflict')
        self.assertEqual(classify('Charizard EX')['condition'],'unknown')
        self.assertEqual(classify('Deutsch English')['language'],'conflict')
    def test_policy(self):
        from ebay_sold import apply_policy
        from types import SimpleNamespace
        rows=parse(fixture())
        a=SimpleNamespace(language='de',edition='first',variant='holo',condition='nm',card_number='8/102',max_age_days=3650)
        apply_policy(rows,a)
        self.assertFalse(rows[0]['eligible'])
        self.assertIn('EDITION_MISMATCH_OR_UNKNOWN',rows[0]['exclusions'])
    def test_endpoint_security(self):
        from ebay_sold import WebDriver
        for u in ['http://example.com:4444','http://user:pass@127.0.0.1:4444','file:///etc/passwd']:
            with self.assertRaises(ValueError): WebDriver(u)
    def test_more_graders(self):
        for grader in ['AOG','PGS','GSG','SGC']:
            self.assertFalse(parse(fixture(title=f'Machomei {grader} 9'))[0]['eligible'])

class IntegrationTests(unittest.TestCase):
    def test_resume_and_atomic_exports(self):
        import tempfile, subprocess, sys, json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); h=d/'page.html'; h.write_text(fixture(),encoding='utf-8')
            cmd=[sys.executable,str(Path(__file__).with_name('ebay_sold.py')),'--query','Machomei','--html',str(h),'--out',str(d/'out'),'--profile',str(d/'profile')]
            a=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(a.returncode,0,a.stderr)
            r=json.loads((d/'out/sales.json').read_text()); self.assertEqual(len(r['rows']),1)
            self.assertIsNone(r['summary']['estimated_market_value_eur'])
            b=subprocess.run(cmd+['--resume','--require','OTHER'],capture_output=True,text=True)
            self.assertEqual(b.returncode,2)
            self.assertIn('Checkpoint filters differ',b.stderr)
            self.assertEqual(len(json.loads((d/'out/sales.json').read_text())['rows']),1)
    def test_service_error(self):
        self.assertEqual(page_state('<title>Error Page | eBay</title>Something went wrong on our end'),'SERVICE_ERROR')

class SessionTests(unittest.TestCase):
    def test_create_uses_persistent_profile(self):
        from ebay_sold import WebDriver
        from unittest.mock import patch
        with patch.object(WebDriver,'call',side_effect=[{'nodes':[]},{'sessionId':'abc','capabilities':{'chrome':{'userDataDir':'/data/profile'}}}]) as call:
            d=WebDriver('http://127.0.0.1:4444',profile='/data/profile')
            args=call.call_args_list[1].args[2]['capabilities']['alwaysMatch']['goog:chromeOptions']['args']
            self.assertIn('--user-data-dir=/data/profile',args)
            self.assertEqual(d.session,'/session/abc')
    def test_temporary_profile_fails_explicitly(self):
        from ebay_sold import WebDriver, ProfileMismatch
        from unittest.mock import patch
        status={'nodes':[{'slots':[{'session':{'sessionId':'abc','capabilities':{'chrome':{'userDataDir':'/tmp/empty'}}}}]}]}
        with patch.object(WebDriver,'call',return_value=status) as call:
            with self.assertRaises(ProfileMismatch): WebDriver('http://127.0.0.1:4444')
            self.assertEqual(call.call_count,1)  # no session deletion or cookie manipulation
    def test_existing_profile_reused(self):
        from ebay_sold import WebDriver
        from unittest.mock import patch
        status={'nodes':[{'slots':[{'session':{'sessionId':'abc','capabilities':{'chrome':{'userDataDir':'/data/profile'}}}}]}]}
        with patch.object(WebDriver,'call',return_value=status) as call:
            WebDriver('http://127.0.0.1:4444',profile='/data/profile')
            self.assertEqual(call.call_count,1)


def test_pokemon_ex_never_conflicts_with_nm():
    from ebay_sold import classify
    assert classify('Quajutsu ex MEP 099 Deutsch NM')['condition'] == 'nm'
    assert classify('Quajutsu EX MEP 099 Deutsch Near Mint')['condition'] == 'nm'
    assert classify('Quajutsu ex MEP 099 Deutsch')['condition'] == 'unknown'
