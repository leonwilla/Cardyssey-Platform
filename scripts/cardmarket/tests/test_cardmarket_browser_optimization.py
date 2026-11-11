"""Production policy tests for safe offline bulk, fast-search fallback, no price promotion."""
import sys as _cm_sys
from pathlib import Path as _cm_Path
_cm_scriptroot=_cm_Path(__file__).resolve().parents[2]
for _cm_base in (_cm_scriptroot.parent, _cm_scriptroot, _cm_scriptroot/"cardmarket/core", _cm_scriptroot/"cardmarket/admin", _cm_scriptroot/"cardmarket/archive"):
    if str(_cm_base) not in _cm_sys.path:_cm_sys.path.append(str(_cm_base))
from _paths import source_path
import csv,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REPO=ROOT.parent
BASE=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector')
class BrowserOptimizationTests(unittest.TestCase):
    def source(self,name):
        return (source_path(name)).read_text(encoding='utf-8-sig')
    def test_bulk_stays_in_csv_not_browser_if_covered(self):
        s=self.source('cardmarket-language-browser-collector.ps1')
        self.assertIn('$bulkFeedOnlyRows=@($allCases | Where-Object',s)
        self.assertIn("[string]$_.needs_price -eq 'NO'",s)
        self.assertIn("[string]$_.manual_scan_requested_at -eq ''",s)
        self.assertIn("[string]$_.existing_source -ne ''",s)
        self.assertIn('$browserCases=@($allCases | Where-Object',s)
        self.assertIn('-not $feedOnlyKeys.Contains(',s)
        self.assertIn('bulk_feed_only_variants = $bulkFeedOnly',s)
        for lang in ('de','en'):
            p=BASE/f'queue-{lang}.csv'
            if not p.exists():continue
            with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            self.assertGreater(len(rows),30000)
            self.assertTrue(any(r.get('scan_tier')=='4' and r.get('needs_price')=='YES' for r in rows))
            self.assertEqual(len({(r['cardyssey_karte'],r['variante_id']) for r in rows}),len(rows))
    def test_light_search_falls_back_and_challenge_is_terminal(self):
        s=self.source('cardmarket-language-browser-collector.ps1')
        x=self.source('cardmarket-lightweight-search.ps1')
        self.assertIn('Search-CardmarketSameOrigin',s)
        self.assertIn('if (!(Move-To $searchUrl))',s)
        self.assertIn('FULL_PAGE_SEARCH_FALLBACK',s)
        self.assertIn('SAME_ORIGIN_SEARCH_HTML',s)
        self.assertIn("if([string]$_ -match 'CARDMARKET_PROVIDER_CHALLENGE'){throw}",s)
        self.assertIn('credentials:"same-origin"',x)
        self.assertIn('new DOMParser().parseFromString(html,"text/html")',x)
        self.assertIn("throw 'CARDMARKET_PROVIDER_CHALLENGE'",x)
        self.assertIn('if($links.Count -eq 0){return $null}',x)
    def test_crosslanguage_only_as_lead_with_live_product_recheck(self):
        s=self.source('cardmarket-language-browser-collector.ps1')
        x=self.source('cardmarket-build-cross-language-page-cache.py')
        self.assertIn('OFFICIAL_SINGLETON_AND_LIVE_NUMBER_CONFIRMED_CANDIDATE_ONLY',s)
        self.assertIn('candidateId -eq [string]$case.catalog_singleton_id',s)
        self.assertIn('candidateId -in $allowedIds',s)
        self.assertIn('$out.cross_language_print_verified=$false',s)
        self.assertIn('if (!(Move-To $initialUrl))',s)
        self.assertIn('candidateId =',s)
        self.assertIn('candidateId =',s)
        self.assertIn('targetProductValidated',x)
    def test_same_comment_rules_live_and_offline(self):
        p=REPO/'config/cardmarket-comment-rules.json'
        data=json.loads(p.read_text())
        self.assertEqual(data['source'],'CARDYSSEY_DIAGNOSTIC_ONLY')
        ps=self.source('cardmarket-offer-comments.ps1')
        py=self.source('cardmarket_variant_resolver.py')
        self.assertIn("$rulePath=Join-Path $PSScriptRoot 'cardmarket-comment-rules.json'",ps)
        self.assertIn("COMMENT_RULES_PATH=",py)
        self.assertIn("return 'SHORTHAND_HINT'",ps)
        self.assertIn('return "shorthand_hint"',py)
    def test_no_modification_of_pricing_cache_and_job_refresh(self):
        runner=self.source('Cardmarket-Queue-Runner.ps1')
        weekly=self.source('run-cardmarket-identity-weekly.py')
        self.assertIn('Update-CrossLanguagePageCache',runner)
        self.assertIn('cardmarket-build-cross-language-page-cache.py',runner)
        self.assertIn('cardmarket-build-cross-language-page-cache.py',weekly)
        self.assertIn("'--output',BASE/'cardmarket-cross-language-page-cache.json'",weekly)
if __name__=='__main__':unittest.main()
