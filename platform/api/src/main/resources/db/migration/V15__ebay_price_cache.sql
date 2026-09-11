CREATE TABLE ebay_price_cache (
    card_id TEXT NOT NULL,
    language_code VARCHAR(16) NOT NULL,
    variant_id TEXT NOT NULL,
    source VARCHAR(64) NOT NULL,
    base_eur NUMERIC(12, 4) NOT NULL CHECK (base_eur > 0),
    range_low_eur NUMERIC(12, 4) NOT NULL CHECK (range_low_eur > 0),
    range_high_eur NUMERIC(12, 4) NOT NULL CHECK (range_high_eur > 0),
    sample_count INTEGER NOT NULL CHECK (sample_count > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (card_id, language_code, variant_id),
    CHECK (range_low_eur <= range_high_eur)
);

CREATE INDEX idx_ebay_price_cache_updated_at
    ON ebay_price_cache (updated_at);
