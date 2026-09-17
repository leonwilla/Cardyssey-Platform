-- Retry variants that were backed off after eBay rejected the old collector user agent.
-- Cached prices and user collection data remain untouched.
DELETE FROM ebay_price_refresh_state;
