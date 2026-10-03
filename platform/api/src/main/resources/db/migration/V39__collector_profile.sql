ALTER TABLE users
    ADD COLUMN IF NOT EXISTS favorite_pokemon TEXT,
    ADD COLUMN IF NOT EXISTS favorite_set TEXT,
    ADD COLUMN IF NOT EXISTS collecting_focus TEXT;

ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_favorite_pokemon_length;

ALTER TABLE users
    ADD CONSTRAINT users_favorite_pokemon_length
    CHECK (favorite_pokemon IS NULL OR char_length(favorite_pokemon) <= 80);

ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_favorite_set_length;

ALTER TABLE users
    ADD CONSTRAINT users_favorite_set_length
    CHECK (favorite_set IS NULL OR char_length(favorite_set) <= 120);

ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_collecting_focus_length;

ALTER TABLE users
    ADD CONSTRAINT users_collecting_focus_length
    CHECK (collecting_focus IS NULL OR char_length(collecting_focus) <= 240);
