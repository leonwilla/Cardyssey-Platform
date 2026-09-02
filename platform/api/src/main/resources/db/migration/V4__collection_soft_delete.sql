ALTER TABLE collection_items
    ADD COLUMN deleted_at TIMESTAMPTZ;

CREATE INDEX collection_items_user_updated_index
    ON collection_items(user_id, updated_at);

CREATE INDEX collection_items_deleted_index
    ON collection_items(user_id, deleted_at)
    WHERE deleted_at IS NOT NULL;
