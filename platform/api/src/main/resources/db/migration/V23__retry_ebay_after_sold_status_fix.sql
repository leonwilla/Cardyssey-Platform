-- A failed direct-collector lookup can be backed off for up to 24 hours.
-- Retry all affected card variants once after the sold-status classifier fix.
-- Cached prices and all user collection data remain untouched.
DELETE FROM ebay_price_refresh_state;
