CREATE TABLE sale_listings (
    id UUID PRIMARY KEY,

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    collection_item_id UUID NOT NULL
        REFERENCES collection_items(id)
        ON DELETE CASCADE,

    quantity INTEGER NOT NULL DEFAULT 1,

    price_eur NUMERIC(12,2),

    negotiable BOOLEAN NOT NULL DEFAULT TRUE,

    status TEXT NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (quantity > 0),

    CHECK (
        price_eur IS NULL
        OR price_eur >= 0
    ),

    CHECK (
        status IN (
            'ACTIVE',
            'PAUSED',
            'SOLD'
        )
    ),

    UNIQUE (
        user_id,
        collection_item_id
    )
);

CREATE INDEX sale_listings_status_idx
ON sale_listings(status);

CREATE INDEX sale_listings_user_idx
ON sale_listings(user_id);
