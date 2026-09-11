-- Existing CompSniper cache rows predate the recent-sales payload. Mark them
-- stale once so the next demand-driven lookup refreshes and fills the debug
-- links without globally hammering the provider during deployment.
UPDATE ebay_price_cache
SET updated_at = to_timestamp(0)
WHERE source = 'COMPSNIPER';
