CREATE TABLE IF NOT EXISTS cardtrader_variant_identity_cache (
    card_id TEXT NOT NULL,
    language_code VARCHAR(16) NOT NULL,
    variant_id TEXT NOT NULL,
    cardmarket_product_id BIGINT,
    blueprint_id BIGINT NOT NULL,
    expansion_id BIGINT,
    method VARCHAR(64) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (card_id, language_code, variant_id)
);

CREATE INDEX IF NOT EXISTS idx_cardtrader_variant_identity_product
    ON cardtrader_variant_identity_cache (cardmarket_product_id)
    WHERE cardmarket_product_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cardtrader_variant_identity_blueprint
    ON cardtrader_variant_identity_cache (blueprint_id);
