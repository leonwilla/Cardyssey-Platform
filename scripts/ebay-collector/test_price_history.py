import unittest
from datetime import date
from price_history import choose_median, windows_for

class RollingEbayPriceTests(unittest.TestCase):
    today=date(2026,11,4)

    def make(self,days,price):
        from datetime import timedelta
        return dict(sold_on=(self.today-timedelta(days=days)).isoformat(),sold_eur=price)

    def test_prefers_30day_median_with_three_sales(self):
        selection=choose_median([self.make(1,9),self.make(3,1),self.make(10,5),self.make(220,100)],self.today)
        self.assertEqual((selection['window_days'],selection['median_eur'],selection['sample_count']),(30,5,3))

    def test_expands_to_90_days_when_30_has_one_sale(self):
        x=choose_median([self.make(1,15),self.make(35,2),self.make(70,4)],self.today)
        self.assertEqual((x['window_days'],x['median_eur']),(90,4))

    def test_expands_six_months_and_additional_years(self):
        x=choose_median([self.make(400,1),self.make(401,2),self.make(600,3)],self.today)
        self.assertEqual((x['window_days'],x['median_eur']),(730,2))

    def test_recent_single_sale_stays_in_30day_window(self):
        result=choose_median([self.make(14,1)],self.today)
        self.assertEqual(result['window_days'],30)
        self.assertTrue(result['low_sample'])

    def test_single_sale_is_kept_when_no_three_exist(self):
        x=choose_median([self.make(2500,10)],self.today)
        self.assertEqual((x['sample_count'],x['median_eur'],x['low_sample']),(1,10,True))
        self.assertGreaterEqual(x['window_days'],2500)

    def test_sold_future_entries_are_not_used(self):
        x=choose_median([self.make(-2,999),self.make(2,6)],self.today)
        self.assertEqual(x['median_eur'],6)

    def test_no_sales_yields_no_price(self):
        self.assertIsNone(choose_median([],self.today))
