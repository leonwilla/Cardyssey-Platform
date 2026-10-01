/*
 * Persistent central TCG price cache.
 *
 * App/web requests only read this table. External providers are contacted by
 * the server-side worker, so user activity never consumes provider quota.
 * A NULL base_eur is a cached "no price available" result and is retried
 * after the normal refresh TTL.
 */
CREATE TABLE tcg_price_cache (
    card_id TEXT NOT NULL,
    language_code VARCHAR(16) NOT NULL,
    variant_id TEXT NOT NULL,
    legacy_variant VARCHAR(32) NOT NULL,
    source VARCHAR(64),
    base_eur NUMERIC(12, 4),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (card_id, language_code, variant_id),
    CHECK (base_eur IS NULL OR base_eur > 0)
);

CREATE INDEX idx_tcg_price_cache_updated_at
    ON tcg_price_cache (updated_at);

CREATE INDEX idx_tcg_price_cache_language_updated
    ON tcg_price_cache (language_code, updated_at);
