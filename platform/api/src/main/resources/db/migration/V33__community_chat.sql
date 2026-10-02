ALTER TABLE chat_groups
    ADD COLUMN image_url TEXT;

ALTER TABLE chat_group_members
    DROP CONSTRAINT chat_group_member_role_valid;

ALTER TABLE chat_group_members
    ADD CONSTRAINT chat_group_member_role_valid
    CHECK (role IN ('OWNER', 'ADMIN', 'MEMBER'));

ALTER TABLE chat_group_messages
    ADD COLUMN object_type VARCHAR(32),
    ADD COLUMN object_payload JSONB;

CREATE TABLE community_rooms (
    id UUID PRIMARY KEY,
    slug VARCHAR(160) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    room_type VARCHAR(16) NOT NULL,
    language_code VARCHAR(8) NOT NULL,
    set_id VARCHAR(120),
    set_name VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT community_room_type_valid CHECK (room_type IN ('TOPIC', 'SET')),
    CONSTRAINT community_room_language_valid CHECK (language_code IN ('de', 'en', 'ja', 'ko', 'zh'))
);

CREATE INDEX community_rooms_language_activity_idx
    ON community_rooms (language_code, last_activity_at DESC);

CREATE INDEX community_rooms_set_idx
    ON community_rooms (set_id, language_code)
    WHERE set_id IS NOT NULL;

CREATE TABLE community_room_reads (
    room_id UUID NOT NULL REFERENCES community_rooms(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_read_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (room_id, user_id)
);

CREATE TABLE community_messages (
    id UUID PRIMARY KEY,
    room_id UUID NOT NULL REFERENCES community_rooms(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body VARCHAR(1200) NOT NULL DEFAULT '',
    object_type VARCHAR(32),
    object_payload JSONB,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT community_message_has_content CHECK (
        LENGTH(BTRIM(body)) > 0 OR object_type IS NOT NULL
    )
);

CREATE INDEX community_messages_room_created_idx
    ON community_messages (room_id, created_at DESC, id DESC);

CREATE TABLE chat_user_blocks (
    blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (blocker_id, blocked_id),
    CONSTRAINT chat_user_block_not_self CHECK (blocker_id <> blocked_id)
);

CREATE TABLE community_message_reports (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES community_messages(id) ON DELETE CASCADE,
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason VARCHAR(300) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (message_id, reporter_id),
    CONSTRAINT community_report_status_valid CHECK (status IN ('OPEN', 'RESOLVED', 'DISMISSED'))
);

CREATE INDEX community_message_reports_status_idx
    ON community_message_reports (status, created_at DESC);

CREATE TABLE chat_moderation_actions (
    id UUID PRIMARY KEY,
    target_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    message_id UUID REFERENCES community_messages(id) ON DELETE SET NULL,
    moderator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(24) NOT NULL,
    reason VARCHAR(500),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chat_moderation_action_valid CHECK (
        action IN ('DELETE_MESSAGE', 'WARN', 'MUTE', 'UNMUTE', 'BAN', 'UNBAN')
    )
);

CREATE INDEX chat_moderation_actions_target_idx
    ON chat_moderation_actions (target_user_id, created_at DESC);

CREATE TABLE chat_user_sanctions (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    muted_until TIMESTAMPTZ,
    banned_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO community_rooms (id, slug, name, room_type, language_code)
SELECT gen_random_uuid(), topic.slug || '-' || lang.code, topic.name, 'TOPIC', lang.code
FROM (
    VALUES
        ('lounge', 'Cardyssey Lounge'),
        ('pulls-hits', 'Pulls & Hits'),
        ('sammlungen', 'Sammlungen'),
        ('karten-varianten', 'Karten & Varianten'),
        ('markt-preise', 'Markt & Preise'),
        ('tauschen', 'Tauschen'),
        ('tcg-decks', 'TCG & Decks'),
        ('neue-sets', 'Neue Sets')
) AS topic(slug, name)
CROSS JOIN (
    VALUES ('de'), ('en'), ('ja'), ('ko'), ('zh')
) AS lang(code)
ON CONFLICT (slug) DO NOTHING;
