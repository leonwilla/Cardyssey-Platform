CREATE TABLE IF NOT EXISTS tcg_price_history (
    card_id TEXT NOT NULL,
    language_code VARCHAR(16) NOT NULL,
    variant_id TEXT NOT NULL,
    source VARCHAR(64),
    base_eur NUMERIC(12, 4) NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (base_eur > 0)
);

CREATE INDEX IF NOT EXISTS idx_tcg_price_history_lookup
    ON tcg_price_history (
        card_id,
        language_code,
        variant_id,
        captured_at DESC
    );

INSERT INTO tcg_price_history (
    card_id,
    language_code,
    variant_id,
    source,
    base_eur,
    captured_at
)
SELECT
    card_id,
    language_code,
    variant_id,
    source,
    base_eur,
    updated_at
FROM tcg_price_cache
WHERE base_eur IS NOT NULL
  AND base_eur > 0
  AND NOT EXISTS (
      SELECT 1
      FROM tcg_price_history h
      WHERE h.card_id = tcg_price_cache.card_id
        AND h.language_code = tcg_price_cache.language_code
        AND h.variant_id = tcg_price_cache.variant_id
  );
