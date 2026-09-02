ALTER TABLE users
    ADD COLUMN email_verified_at TIMESTAMPTZ;

ALTER TABLE users
    ADD COLUMN disabled_at TIMESTAMPTZ;

ALTER TABLE refresh_tokens
    ADD COLUMN revoked_at TIMESTAMPTZ;

CREATE UNIQUE INDEX refresh_tokens_token_hash_unique
    ON refresh_tokens(token_hash);

CREATE INDEX refresh_tokens_active_user_index
    ON refresh_tokens(user_id, expires_at)
    WHERE revoked_at IS NULL;
