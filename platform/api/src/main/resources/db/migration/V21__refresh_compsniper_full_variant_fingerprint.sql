-- eBay matching now validates the complete TCGdex physical variant fingerprint:
-- raw type, subtype, foil pattern, stamps, size and language availability.
-- Existing CompSniper cache rows may therefore contain sales from a sibling
-- printing and must be refreshed lazily on their next requested quote.
UPDATE ebay_price_cache
SET updated_at = to_timestamp(0)
WHERE source = 'COMPSNIPER';
