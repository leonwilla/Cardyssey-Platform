ALTER TABLE tcg_price_cache
    ADD COLUMN IF NOT EXISTS resolution_status VARCHAR(32),
    ADD COLUMN IF NOT EXISTS failure_detail TEXT,
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ;

UPDATE tcg_price_cache
SET
    resolution_status =
        CASE
            WHEN base_eur IS NOT NULL THEN 'PRICE_FOUND'
            ELSE 'NO_PRICE'
        END,
    next_attempt_at =
        CASE
            WHEN base_eur IS NOT NULL
                THEN updated_at + INTERVAL '168 hours'
            ELSE NOW()
        END
WHERE resolution_status IS NULL
   OR next_attempt_at IS NULL;

ALTER TABLE tcg_price_cache
    ALTER COLUMN resolution_status
        SET DEFAULT 'NO_PRICE';

CREATE INDEX IF NOT EXISTS
    idx_tcg_price_cache_next_attempt
    ON tcg_price_cache (next_attempt_at);
