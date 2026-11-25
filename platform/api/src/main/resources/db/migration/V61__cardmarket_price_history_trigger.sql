-- Price chart: record every change of a shown DE/EN Cardmarket price.
-- All writers (2-hourly Cardmarket guide, browser scan import, admin) update
-- tcg_price_cache; a trigger keeps one history row per real change, so the
-- chart needs no change in each writer. Unchanged re-publishes add nothing.
CREATE OR REPLACE FUNCTION record_cardmarket_price_history() RETURNS trigger AS $$
BEGIN
    IF NEW.base_eur IS NULL OR NEW.base_eur <= 0 OR NEW.language_code NOT IN ('de', 'en') THEN
        RETURN NULL;
    END IF;
    IF NOT (upper(COALESCE(NEW.source, '')) LIKE 'CARDMARKET%'
            OR upper(COALESCE(NEW.source, '')) LIKE 'MANUAL%'
            OR upper(COALESCE(NEW.source, '')) LIKE 'ADMIN%') THEN
        RETURN NULL;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.base_eur IS NOT DISTINCT FROM NEW.base_eur
       AND OLD.source IS NOT DISTINCT FROM NEW.source THEN
        RETURN NULL;
    END IF;
    INSERT INTO tcg_price_history (card_id, language_code, variant_id, source, base_eur, captured_at)
    VALUES (NEW.card_id, NEW.language_code, NEW.variant_id, NEW.source, NEW.base_eur, NOW());
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tcg_price_cache_cardmarket_history ON tcg_price_cache;
CREATE TRIGGER tcg_price_cache_cardmarket_history
    AFTER INSERT OR UPDATE OF base_eur, source ON tcg_price_cache
    FOR EACH ROW EXECUTE FUNCTION record_cardmarket_price_history();

-- Starting point: today's shown Cardmarket price, unless the latest history
-- row of that variant already has the same value.
INSERT INTO tcg_price_history (card_id, language_code, variant_id, source, base_eur, captured_at)
SELECT c.card_id, c.language_code, c.variant_id, c.source, c.base_eur, c.updated_at
FROM tcg_price_cache c
WHERE c.language_code IN ('de', 'en')
  AND c.base_eur > 0
  AND (upper(COALESCE(c.source, '')) LIKE 'CARDMARKET%'
       OR upper(COALESCE(c.source, '')) LIKE 'MANUAL%'
       OR upper(COALESCE(c.source, '')) LIKE 'ADMIN%')
  AND NOT EXISTS (
      SELECT 1 FROM tcg_price_history h
      WHERE h.card_id = c.card_id AND h.language_code = c.language_code AND h.variant_id = c.variant_id
        AND h.captured_at >= c.updated_at - INTERVAL '1 minute'
  );
