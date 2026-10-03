CREATE TABLE IF NOT EXISTS showcase_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Mein Showcase',
    theme TEXT NOT NULL DEFAULT 'OBSIDIAN',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT showcase_profile_title_length
        CHECK (char_length(title) BETWEEN 1 AND 80),
    CONSTRAINT showcase_profile_theme_check
        CHECK (theme IN ('OBSIDIAN', 'HOLO', 'GOLD', 'CYAN'))
);

CREATE TABLE IF NOT EXISTS showcase_likes (
    showcase_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (showcase_user_id, user_id),
    CONSTRAINT showcase_like_not_self
        CHECK (showcase_user_id <> user_id)
);

CREATE INDEX IF NOT EXISTS idx_showcase_likes_showcase
    ON showcase_likes(showcase_user_id);
