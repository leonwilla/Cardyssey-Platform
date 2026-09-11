CREATE TABLE ebay_price_refresh_state (
    card_id TEXT NOT NULL,
    language_code VARCHAR(16) NOT NULL,
    variant_id TEXT NOT NULL,
    failure_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_failure_at TIMESTAMPTZ,
    PRIMARY KEY (card_id, language_code, variant_id)
);

CREATE INDEX idx_ebay_price_refresh_state_next_attempt
    ON ebay_price_refresh_state (next_attempt_at);
