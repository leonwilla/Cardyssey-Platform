"""Regression for Quappo base1-13 copyright-edition false set mismatch."""
import csv,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SCANNER=(ROOT/'cardmarket-language-browser-collector.ps1').read_text(encoding='utf-8-sig')
class ProductCardVsPrintEvidence(unittest.TestCase):
 def test_quappo_variant_has_card_candidates_not_fake_print_id(self):
  path=Path('/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector/queue-de.csv')
  with path.open(encoding='utf-8-sig') as f:
   row=next(r for r in csv.DictReader(f) if r['cardyssey_karte']=='base1-13' and r['variante_id'].startswith('zqq5g2u9'))
  self.assertEqual(row['cardmarket_ids'],'')
  self.assertEqual(set(row['set_card_candidate_ids'].split(',')),{'273708','660215'})
 def test_print_uncertainty_never_confirms_identity_or_price(self):
  assert "'PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED'" in SCANNER
  branch=SCANNER.split("$out.status = 'PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED'",1)[1].split('} else {',1)[0]
  self.assertNotIn('identity_confirmed = $true',branch)
  self.assertNotIn('sample_median_eur',branch)
 def test_page_collector_number_matches_card_number(self):
  pattern=r'(?i)-[A-Z]{1,8}([0-9]{1,4})$'
  self.assertEqual(int(re.search(pattern,'https://www.cardmarket.com/de/Pokemon/Products/Singles/Base-Set/Poliwrath-V1-BS13').group(1)),13)
  self.assertNotEqual(int(re.search(pattern,'https://www.cardmarket.com/de/Pokemon/Products/Singles/Undaunted/Houndoom-V1-UD82').group(1)),5)
  self.assertIn('$out.card_number_url_verified=$numberEvidence',SCANNER)
 def test_invalid_set_is_never_accepted_as_print_candidate(self):
  self.assertIn('$setSlugGuards.ContainsKey([string]$case.set_id)',SCANNER)
  self.assertIn('$candidateId -in $cardCandidates',SCANNER)
  self.assertIn('$numberEvidence',SCANNER)
if __name__=='__main__':unittest.main()
