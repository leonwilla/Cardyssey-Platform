CREATE TABLE friendships (
    id UUID PRIMARY KEY,
    requester_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    addressee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    responded_at TIMESTAMPTZ,

    CONSTRAINT friendships_not_self
        CHECK (requester_id <> addressee_id),

    CONSTRAINT friendships_status
        CHECK (status IN ('PENDING', 'ACCEPTED'))
);

CREATE UNIQUE INDEX friendships_unique_pair
ON friendships (
    LEAST(requester_id, addressee_id),
    GREATEST(requester_id, addressee_id)
);

CREATE INDEX friendships_requester_idx
ON friendships(requester_id);

CREATE INDEX friendships_addressee_idx
ON friendships(addressee_id);
