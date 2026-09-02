CREATE TABLE showcase_items (
    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    collection_item_id UUID NOT NULL
        REFERENCES collection_items(id)
        ON DELETE CASCADE,

    position INTEGER NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (user_id, collection_item_id),

    CONSTRAINT showcase_position_positive
        CHECK (position BETWEEN 1 AND 10)
);

CREATE UNIQUE INDEX showcase_unique_position
ON showcase_items(user_id, position);
