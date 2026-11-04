import json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def query(sql):
    p=subprocess.run(['docker','exec','cardyssey-db','psql','-X','-U','cardyssey','-d','cardyssey','-Atc',sql],capture_output=True,text=True,check=True,timeout=30)
    return p.stdout.strip()

class GlobalPolicyTests(unittest.TestCase):
 def test_complete_supported_catalog_including_missing_variants(self):
  rows=query("""SELECT
    (SELECT count(*) FROM catalog_cards_mirror WHERE language_code IN ('de','en','ja','ko','zh-cn','zh-tw')),
    (SELECT count(*) FROM (SELECT DISTINCT language_code,card_id FROM global_price_source_policy) x),
    (SELECT count(DISTINCT (language_code,set_id)) FROM catalog_cards_mirror WHERE language_code IN ('de','en','ja','ko','zh-cn','zh-tw')),
    (SELECT count(DISTINCT (language_code,set_id)) FROM global_price_source_policy)""").split('|')
  self.assertEqual(int(rows[0]),int(rows[1]))
  self.assertEqual(int(rows[2]),int(rows[3]))
 def test_no_unverified_pricecharting_or_foreign_language_pricing(self):
  bad=query("""SELECT count(*) FROM global_price_source_policy p
    WHERE p.selected_price_source ILIKE '%PRICECHARTING%'
      OR (p.selected_price_eur IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM tcg_price_cache t WHERE t.card_id=p.card_id
        AND t.language_code=p.language_code AND t.variant_id=p.variant_id
        AND t.source=p.selected_price_source AND t.base_eur=p.selected_price_eur))""")
  self.assertEqual(bad,'0')
 def test_bulk_never_prefers_ebay(self):
  bad=query("SELECT count(*) FROM global_price_source_policy WHERE price_class='BULK' AND preferred_market<>'TCG'")
  self.assertEqual(bad,'0')
 def test_no_variant_is_tracked_but_not_priced(self):
  value=query("""SELECT count(*) FROM global_price_source_policy
    WHERE variant_id='__NO_EXACT_PRINT__' AND (selected_price_eur IS NOT NULL OR price_status<>'NO_EXACT_VARIANT')""")
  self.assertEqual(value,'0')
 def test_bulk_german_price_is_exact_normal_variant(self):
  row=query("""SELECT p.selected_price_eur,p.selected_price_source,p.price_class
    FROM global_price_source_policy p JOIN catalog_cards_mirror c
    ON c.card_id=p.card_id AND c.language_code=p.language_code
    WHERE p.card_id='sv01-001' AND p.language_code='de' AND EXISTS(
      SELECT 1 FROM jsonb_array_elements(c.variants) v WHERE v->>'id'=p.variant_id AND v->>'legacyVariant'='NORMAL')""")
  self.assertEqual(row,'0.0300|TCGDEX_CATALOG|BULK')

if __name__=='__main__':unittest.main()
