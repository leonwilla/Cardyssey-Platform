-- CompSniper matching now validates the complete physical variant fingerprint
-- (edition, shadowless/unlimited, special stamps and multi-card listings).
-- Existing cached values may contain sales from a different physical variant,
-- so mark them stale once and refresh lazily on the next requested quote.
UPDATE ebay_price_cache
SET updated_at = to_timestamp(0)
WHERE source = 'COMPSNIPER';
