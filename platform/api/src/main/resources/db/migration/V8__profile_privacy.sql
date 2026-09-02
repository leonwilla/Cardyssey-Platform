CREATE TABLE user_privacy_settings (
    user_id UUID PRIMARY KEY
        REFERENCES users(id)
        ON DELETE CASCADE,

    profile_visibility TEXT NOT NULL DEFAULT 'PUBLIC',
    showcase_visibility TEXT NOT NULL DEFAULT 'PUBLIC',
    collection_visibility TEXT NOT NULL DEFAULT 'FRIENDS',
    collection_value_visibility TEXT NOT NULL DEFAULT 'PRIVATE',
    quantity_visibility TEXT NOT NULL DEFAULT 'PRIVATE',
    sets_visibility TEXT NOT NULL DEFAULT 'PUBLIC',
    wishlist_visibility TEXT NOT NULL DEFAULT 'FRIENDS',

    showcase_size INTEGER NOT NULL DEFAULT 5,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT privacy_profile_visibility
        CHECK (profile_visibility IN ('PRIVATE','FRIENDS','PUBLIC')),

    CONSTRAINT privacy_showcase_visibility
        CHECK (showcase_visibility IN ('PRIVATE','FRIENDS','PUBLIC')),

    CONSTRAINT privacy_collection_visibility
        CHECK (collection_visibility IN ('PRIVATE','FRIENDS','PUBLIC')),

    CONSTRAINT privacy_collection_value_visibility
        CHECK (collection_value_visibility IN ('PRIVATE','FRIENDS','PUBLIC')),

    CONSTRAINT privacy_quantity_visibility
        CHECK (quantity_visibility IN ('PRIVATE','FRIENDS','PUBLIC')),

    CONSTRAINT privacy_sets_visibility
        CHECK (sets_visibility IN ('PRIVATE','FRIENDS','PUBLIC')),

    CONSTRAINT privacy_wishlist_visibility
        CHECK (wishlist_visibility IN ('PRIVATE','FRIENDS','PUBLIC')),

    CONSTRAINT privacy_showcase_size
        CHECK (showcase_size IN (5,10))
);

INSERT INTO user_privacy_settings (user_id)
SELECT id
FROM users
ON CONFLICT (user_id) DO NOTHING;
