CREATE TABLE message_reports (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL
        REFERENCES direct_messages(id)
        ON DELETE CASCADE,
    reporter_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,
    reason VARCHAR(500),
    status VARCHAR(24) NOT NULL
        DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),
    CONSTRAINT message_report_status_valid
        CHECK (
            status IN (
                'OPEN',
                'REVIEWED',
                'DISMISSED',
                'ACTION_TAKEN'
            )
        ),
    CONSTRAINT message_report_unique
        UNIQUE (message_id, reporter_id)
);

CREATE INDEX message_reports_status_created_idx
    ON message_reports (
        status,
        created_at DESC
    );

CREATE TABLE admin_chat_audit (
    id UUID PRIMARY KEY,
    actor_user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,
    action VARCHAR(40) NOT NULL,
    query VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW()
);

CREATE INDEX admin_chat_audit_actor_created_idx
    ON admin_chat_audit (
        actor_user_id,
        created_at DESC
    );
