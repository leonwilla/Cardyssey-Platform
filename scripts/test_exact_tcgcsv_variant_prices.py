import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("audit",Path(__file__).with_name("audit-tcgcsv-exact-variant-prices.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ExactAuditTests(unittest.TestCase):
    def setUp(self):
        self.row=dict(set_code="np",exact_variant_provider_ids={"tcgplayer":87231})
        self.feed={1423:dict(products=[dict(productId=87231,name="Marshtomp Winner")],
                             prices=[dict(productId=87231,subTypeName="Normal",marketPrice=42.0)])}
    def test_exact_product_and_price(self):
        self.assertEqual("EXACT_PRODUCT_MARKET_PRICE_AVAILABLE",module.audit(self.row,self.feed)["status"])
    def test_no_price_not_no_product(self):
        self.feed[1423]["prices"]=[]
        self.assertEqual("EXACT_PRODUCT_HAS_NO_PUBLIC_MARKET_PRICE",module.audit(self.row,self.feed)["status"])
    def test_no_wrong_product_inference(self):
        self.row["exact_variant_provider_ids"]["tcgplayer"]=707229
        self.assertEqual("PRODUCT_NOT_IN_GROUP",module.audit(self.row,self.feed)["status"])
    def test_missing_identity(self):
        self.row["exact_variant_provider_ids"]={}
        self.assertEqual("NO_TCGPLAYER_PRODUCT_ID",module.audit(self.row,self.feed)["status"])
if __name__=="__main__":unittest.main()
