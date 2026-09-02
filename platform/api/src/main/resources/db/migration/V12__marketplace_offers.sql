CREATE TABLE marketplace_offers (
    id UUID PRIMARY KEY,

    listing_id UUID NOT NULL
        REFERENCES sale_listings(id)
        ON DELETE CASCADE,

    buyer_user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    quantity INTEGER NOT NULL
        CHECK (quantity > 0),

    price_eur NUMERIC(12,2) NOT NULL
        CHECK (price_eur > 0),

    message TEXT NULL
        CHECK (
            message IS NULL
            OR char_length(message) <= 1000
        ),

    status VARCHAR(20) NOT NULL
        DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'ACCEPTED',
                'REJECTED',
                'WITHDRAWN'
            )
        ),

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW()
);

CREATE INDEX marketplace_offers_listing_idx
ON marketplace_offers(listing_id);

CREATE INDEX marketplace_offers_buyer_idx
ON marketplace_offers(buyer_user_id);

CREATE INDEX marketplace_offers_status_idx
ON marketplace_offers(status);

CREATE UNIQUE INDEX marketplace_offers_pending_unique
ON marketplace_offers(
    listing_id,
    buyer_user_id
)
WHERE status = 'PENDING';
