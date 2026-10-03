ALTER TABLE direct_messages
    ADD COLUMN IF NOT EXISTS reply_to_message_id UUID
        REFERENCES direct_messages(id)
        ON DELETE SET NULL;

ALTER TABLE chat_message_reactions
    DROP CONSTRAINT IF EXISTS chat_message_reaction_scope_valid;

ALTER TABLE chat_message_reactions
    ADD CONSTRAINT chat_message_reaction_scope_valid
        CHECK (scope IN ('DIRECT', 'GROUP', 'COMMUNITY'));
