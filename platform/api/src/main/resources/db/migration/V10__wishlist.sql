CREATE TABLE wishlist_items (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    card_id TEXT NOT NULL,
    language_code TEXT NOT NULL DEFAULT 'de',

    name TEXT NOT NULL,
    set_id TEXT,
    set_name TEXT,
    local_id TEXT,
    image_base TEXT,

    variant_id TEXT,
    variant_type TEXT,
    variant_subtype TEXT,
    foil TEXT,
    size TEXT,
    stamps TEXT[] NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (
        user_id,
        card_id,
        language_code,
        variant_id
    )
);

CREATE INDEX wishlist_user_idx
ON wishlist_items(user_id);
