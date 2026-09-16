-- Rebuild derived eBay prices with the verified Cardyssey collector.
-- Collection entries and all user data remain untouched.
DELETE FROM ebay_price_refresh_state;
DELETE FROM ebay_price_cache;
