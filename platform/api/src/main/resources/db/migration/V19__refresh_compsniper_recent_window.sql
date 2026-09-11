-- eBay pricing now prefers a 30-day market window, expands to 60/90 days
-- only when fewer than 10 cleaned sales remain, and caps the calculation at
-- the 30 newest cleaned sales. Invalidate old CompSniper cache rows once so
-- demand-driven refreshes recalculate them with the new strategy.
DELETE FROM ebay_price_refresh_state AS refresh
USING ebay_price_cache AS cache
WHERE cache.source = 'COMPSNIPER'
  AND refresh.card_id = cache.card_id
  AND refresh.language_code = cache.language_code
  AND refresh.variant_id = cache.variant_id;

UPDATE ebay_price_cache
SET updated_at = to_timestamp(0)
WHERE source = 'COMPSNIPER';
