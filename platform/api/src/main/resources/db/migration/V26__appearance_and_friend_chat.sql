CREATE TABLE user_appearance_settings (
    user_id UUID PRIMARY KEY
        REFERENCES users(id)
        ON DELETE CASCADE,
    theme VARCHAR(32) NOT NULL
        DEFAULT 'OBSIDIAN_GOLD',
    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),
    CONSTRAINT user_appearance_theme_valid
        CHECK (
            theme IN (
                'OBSIDIAN_GOLD',
                'MIDNIGHT_CYAN',
                'ROYAL_VIOLET',
                'EMERALD_MINT'
            )
        )
);

CREATE TABLE direct_messages (
    id UUID PRIMARY KEY,
    sender_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,
    recipient_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,
    body VARCHAR(2000) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),
    read_at TIMESTAMPTZ,
    CONSTRAINT direct_message_not_to_self
        CHECK (sender_id <> recipient_id),
    CONSTRAINT direct_message_not_blank
        CHECK (LENGTH(BTRIM(body)) > 0)
);

CREATE INDEX direct_messages_pair_created_idx
    ON direct_messages (
        sender_id,
        recipient_id,
        created_at DESC
    );

CREATE INDEX direct_messages_unread_idx
    ON direct_messages (
        recipient_id,
        sender_id,
        created_at DESC
    )
    WHERE read_at IS NULL;
