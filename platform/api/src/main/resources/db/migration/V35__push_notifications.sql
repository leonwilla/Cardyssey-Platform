CREATE TABLE IF NOT EXISTS push_devices (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'ANDROID',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, token)
);

CREATE UNIQUE INDEX IF NOT EXISTS push_devices_token_unique
    ON push_devices(token);

CREATE TABLE IF NOT EXISTS push_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    direct_messages BOOLEAN NOT NULL DEFAULT TRUE,
    group_messages BOOLEAN NOT NULL DEFAULT TRUE,
    community_messages BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
