import json,sys,subprocess,tempfile,unittest
from pathlib import Path
from test_ebay_sold import fixture

SCRIPT=Path(__file__).with_name('ebay_sold.py')

def html(date_string,number):
 return fixture(sold='Verkauft '+date_string).replace('123456789012',str(number))

class IncrementalPageTests(unittest.TestCase):
 def run_job(self,*pages):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   htmls=[]
   for i,page in enumerate(pages):
    p=root/f'p{i}.html';p.write_text(page,encoding='utf-8');htmls.append(str(p))
   command=[sys.executable,str(SCRIPT),'--query','Machomei','--html',*htmls,
            '--out',str(root/'out'),'--sold-since','2026-11-02','--max-age-days','36500']
   r=subprocess.run(command,capture_output=True,text=True,timeout=15)
   report=json.loads((root/'out/sales.json').read_text())
   return r.returncode,report
 def test_filters_older_sales_and_stops_at_boundary(self):
  page=html('03. Nov 2026','123456789012')+html('01. Nov 2026','123456789013')
  code,report=self.run_job(page)
  self.assertEqual(code,0)
  self.assertEqual([x['item_id'] for x in report['rows']],['123456789012'])
  self.assertTrue(report['incremental_boundary_reached'])
 def test_all_old_results_prove_boundary_without_import(self):
  code,report=self.run_job(html('01. Nov 2026','123456789013'))
  self.assertEqual(code,0)
  self.assertEqual(report['rows'],[])
  self.assertTrue(report['incremental_boundary_reached'])
  self.assertEqual(report['pages'][0]['status'],'OK')
 def test_no_old_date_at_page_limit_is_incomplete(self):
  code,report=self.run_job(html('04. Nov 2026','123456789012'))
  self.assertEqual(code,2)
  self.assertEqual(report['pages'][-1]['status'],'INCREMENTAL_BOUNDARY_NOT_REACHED')
  self.assertFalse(report['incremental_boundary_reached'])
 def test_unsorted_sold_dates_dont_allow_early_cursor_advance(self):
  page=html('01. Nov 2026','123456789013')+html('03. Nov 2026','123456789012')
  code,report=self.run_job(page)
  self.assertEqual(code,2)
  self.assertFalse(report['incremental_boundary_reached'])

if __name__=='__main__':unittest.main()
