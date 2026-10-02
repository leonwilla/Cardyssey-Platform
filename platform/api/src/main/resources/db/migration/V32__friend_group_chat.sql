CREATE TABLE chat_groups (
    id UUID PRIMARY KEY,
    name VARCHAR(60) NOT NULL,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chat_group_name_not_blank CHECK (LENGTH(BTRIM(name)) >= 2)
);

CREATE TABLE chat_group_members (
    group_id UUID NOT NULL REFERENCES chat_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL DEFAULT 'MEMBER',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_read_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, user_id),
    CONSTRAINT chat_group_member_role_valid CHECK (role IN ('OWNER', 'MEMBER'))
);

CREATE INDEX chat_group_members_user_idx ON chat_group_members (user_id, joined_at DESC);

CREATE TABLE chat_group_messages (
    id UUID PRIMARY KEY,
    group_id UUID NOT NULL REFERENCES chat_groups(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body VARCHAR(2000) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chat_group_message_not_blank CHECK (LENGTH(BTRIM(body)) > 0)
);

CREATE INDEX chat_group_messages_group_created_idx ON chat_group_messages (group_id, created_at DESC);
