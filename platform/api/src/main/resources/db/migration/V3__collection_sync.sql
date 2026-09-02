CREATE UNIQUE INDEX collection_items_user_client_key_unique
    ON collection_items(user_id, client_key);
