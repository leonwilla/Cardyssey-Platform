
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX users_email_unique
    ON users (LOWER(email));


CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY,

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    token_hash TEXT NOT NULL,

    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX refresh_tokens_user_index
    ON refresh_tokens(user_id);


CREATE TABLE collection_items (
    id UUID PRIMARY KEY,

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    client_key VARCHAR(100),

    card_id VARCHAR(100) NOT NULL,
    language_code VARCHAR(20) NOT NULL,

    name TEXT NOT NULL,

    set_id VARCHAR(100),
    set_name TEXT,

    local_id VARCHAR(100),

    image_base TEXT,
    image_language VARCHAR(20),

    legacy_variant VARCHAR(40) NOT NULL,

    variant_identity VARCHAR(200) NOT NULL,

    variant_id VARCHAR(200),
    variant_type VARCHAR(100),
    variant_subtype VARCHAR(150),
    variant_foil VARCHAR(150),
    variant_size VARCHAR(100),

    variant_stamps JSONB NOT NULL DEFAULT '[]'::jsonb,

    condition VARCHAR(50) NOT NULL,

    quantity INTEGER NOT NULL DEFAULT 1
        CHECK (quantity > 0),

    unit_eur NUMERIC(14,4),
    unit_usd NUMERIC(14,4),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE INDEX collection_items_user_index
    ON collection_items(user_id);

CREATE INDEX collection_items_card_index
    ON collection_items(card_id);

CREATE INDEX collection_items_variant_index
    ON collection_items(
        user_id,
        card_id,
        language_code,
        variant_identity,
        condition
    );


CREATE TABLE market_prices (
    id UUID PRIMARY KEY,

    collection_item_id UUID NOT NULL
        REFERENCES collection_items(id)
        ON DELETE CASCADE,

    market VARCHAR(50) NOT NULL,

    value_eur NUMERIC(14,4),

    sample_count INTEGER,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (
        collection_item_id,
        market
    )
);


CREATE INDEX market_prices_item_index
    ON market_prices(collection_item_id);

