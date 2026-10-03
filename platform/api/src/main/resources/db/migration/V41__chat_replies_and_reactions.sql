ALTER TABLE chat_group_messages
    ADD COLUMN IF NOT EXISTS reply_to_message_id UUID
        REFERENCES chat_group_messages(id)
        ON DELETE SET NULL;

ALTER TABLE community_messages
    ADD COLUMN IF NOT EXISTS reply_to_message_id UUID
        REFERENCES community_messages(id)
        ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS chat_message_reactions (
    scope VARCHAR(16) NOT NULL,
    message_id UUID NOT NULL,
    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,
    emoji VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (
        scope,
        message_id,
        user_id,
        emoji
    ),
    CONSTRAINT chat_message_reaction_scope_valid
        CHECK (scope IN ('GROUP', 'COMMUNITY')),
    CONSTRAINT chat_message_reaction_emoji_valid
        CHECK (emoji IN ('❤️', '👍', '🔥', '😂', '😮'))
);

CREATE INDEX IF NOT EXISTS chat_message_reactions_message_idx
    ON chat_message_reactions (
        scope,
        message_id
    );
