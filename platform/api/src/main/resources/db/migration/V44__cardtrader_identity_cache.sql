CREATE TABLE IF NOT EXISTS cardtrader_identity_cache (
    card_id TEXT NOT NULL,
    language_code VARCHAR(16) NOT NULL,
    cardmarket_product_id BIGINT,
    blueprint_id BIGINT,
    expansion_id BIGINT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (card_id, language_code)
);

CREATE INDEX IF NOT EXISTS idx_cardtrader_identity_product
    ON cardtrader_identity_cache (cardmarket_product_id);

CREATE INDEX IF NOT EXISTS idx_cardtrader_identity_blueprint
    ON cardtrader_identity_cache (blueprint_id)
    WHERE blueprint_id IS NOT NULL;
