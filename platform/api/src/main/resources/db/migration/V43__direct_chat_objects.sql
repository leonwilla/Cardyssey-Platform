ALTER TABLE direct_messages
    ADD COLUMN IF NOT EXISTS object_type TEXT,
    ADD COLUMN IF NOT EXISTS object_payload JSONB;

ALTER TABLE direct_messages
    DROP CONSTRAINT IF EXISTS direct_messages_object_type_check;

ALTER TABLE direct_messages
    ADD CONSTRAINT direct_messages_object_type_check
        CHECK (
            object_type IS NULL
            OR object_type IN (
                'CARD',
                'SET',
                'WISHLIST_CARD',
                'SHOWCASE',
                'TRADE_OFFER'
            )
        );
