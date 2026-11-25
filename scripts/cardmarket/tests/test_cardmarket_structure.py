"""Canonical script directories remain deployable across desktop, cron and web."""
from __future__ import annotations
import csv,subprocess,unittest
from pathlib import Path
from _paths import CATEGORY_BY_NAME, source_path

REPO=Path(__file__).resolve().parents[3]
CORE=REPO/'scripts/cardmarket/core'
ADMIN=REPO/'scripts/cardmarket/admin'

class CardmarketStructureTests(unittest.TestCase):
    def test_all_versioned_cardmarket_scripts_have_canonical_locations(self):
        self.assertGreaterEqual(len(CATEGORY_BY_NAME),80)
        for name in CATEGORY_BY_NAME:
            with self.subTest(name=name):
                self.assertTrue(source_path(name).is_file())
        self.assertFalse((REPO/'scripts/cardmarket_delta_scan.py').exists())
        self.assertFalse((REPO/'scripts/cardmarket_scan_monitor.py').exists())
    def test_admin_routes_only_use_admin_scripts(self):
        routes={
            'cardmarket-print-review':'cardmarket-print-review-admin.py',
            'cardmarket-manual-product':'cardmarket-manual-product-review.py',
            'cardmarket-scan':'cardmarket_scan_monitor.py',
            'cardmarket-scan-failures':'cardmarket-live-failures.py',
        }
        for route,name in routes.items():
            text=(REPO/'web/app/api/admin'/route/'route.ts').read_text()
            self.assertIn('/scripts/cardmarket/admin/'+name,text)
        control=(REPO/'web/app/api/admin/cardmarket-scan-control/route.ts').read_text()
        for name in ('cardmarket-reset-rescan.py','cardmarket-retry-one.py'):
            self.assertIn('/scripts/cardmarket/admin/'+name,control)
    def test_weekly_cron_and_github_workflow_sources_exist(self):
        job=(CORE/'run-cardmarket-identity-weekly.py').read_text()
        for name in ('export-cardmarket-full-queue.py',
                     'prioritize-cardmarket-scan-queue.py',
                     'cardmarket_delta_scan.py','cardmarket-set-identity-audit.py'):
            self.assertIn('scripts/cardmarket/core/'+name,job)
        workflow=(REPO/'.github/workflows/tcgcsv-price-refresh.yml').read_text()
        self.assertIn('scripts/cardmarket/core/refresh-cardmarket-price-cache.py',workflow)
        self.assertIn('scripts/cardmarket/core/resolve-cardmarket-cardtrader-bridge.py',workflow)
    def test_windows_modules_keep_flat_install_target_and_no_price_mutation(self):
        deploy=(CORE/'deploy-windows-modules.py').read_text()
        self.assertIn('CardmarketCollector',deploy)
        self.assertIn('scanner_idle()',deploy)
        self.assertNotIn('queue-de.csv',deploy)
        self.assertNotIn('browser-observations-de.jsonl',deploy)
        self.assertNotIn('cf_clearance',deploy)
        launch=(CORE/'Cardmarket-Collector-Launcher.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('Cardmarket-Session-Warmup.ps1',launch)
        self.assertIn('CARDMARKET_COOLDOWN',launch)

if __name__=='__main__':unittest.main()
