-- Browser test mode must retry variants that failed on the old HTTP collector.
-- Cached sales and all user collection data remain untouched.
DELETE FROM ebay_price_refresh_state;
