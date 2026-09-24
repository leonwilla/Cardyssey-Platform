/*
 * Permanent multilingual catalog mirror.
 *
 * Catalog metadata and media fingerprints are immutable history: syncs only
 * upsert newer source data. Prices intentionally stay in the existing
 * time-limited pricing caches.
 */
CREATE TABLE catalog_sets_mirror (
    language_code TEXT NOT NULL,
    set_id TEXT NOT NULL,
    name TEXT NOT NULL,
    printed_code TEXT,
    official_count INTEGER NOT NULL DEFAULT 0,
    total_count INTEGER NOT NULL DEFAULT 0,
    logo_source_url TEXT,
    symbol_source_url TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_updated_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (language_code, set_id)
);

CREATE INDEX catalog_sets_mirror_name_idx
    ON catalog_sets_mirror (
        language_code,
        LOWER(name)
    );

CREATE TABLE catalog_set_code_aliases (
    language_code TEXT NOT NULL,
    printed_code TEXT NOT NULL,
    set_id TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'catalog',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (language_code, printed_code)
);

CREATE INDEX catalog_set_code_aliases_set_idx
    ON catalog_set_code_aliases (
        language_code,
        set_id
    );

CREATE TABLE catalog_cards_mirror (
    language_code TEXT NOT NULL,
    card_id TEXT NOT NULL,
    set_id TEXT NOT NULL,
    local_id TEXT NOT NULL,
    name TEXT NOT NULL,
    rarity TEXT,
    image_source_url TEXT,
    image_local_path TEXT,
    image_dhash BIGINT,
    image_bytes BIGINT,
    variants JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_updated_at TIMESTAMPTZ,
    details_complete BOOLEAN NOT NULL DEFAULT FALSE,
    image_complete BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (language_code, card_id)
);

CREATE INDEX catalog_cards_mirror_number_idx
    ON catalog_cards_mirror (
        language_code,
        local_id
    );

CREATE INDEX catalog_cards_mirror_set_idx
    ON catalog_cards_mirror (
        language_code,
        set_id,
        local_id
    );

CREATE INDEX catalog_cards_mirror_name_idx
    ON catalog_cards_mirror (
        language_code,
        LOWER(name)
    );

CREATE INDEX catalog_cards_mirror_visual_idx
    ON catalog_cards_mirror (
        language_code,
        image_dhash
    )
    WHERE image_dhash IS NOT NULL;

CREATE TABLE catalog_sync_state (
    language_code TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    phase TEXT NOT NULL DEFAULT 'waiting',
    last_started_at TIMESTAMPTZ,
    last_completed_at TIMESTAMPTZ,
    next_sync_at TIMESTAMPTZ,
    set_count INTEGER NOT NULL DEFAULT 0,
    card_count INTEGER NOT NULL DEFAULT 0,
    image_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);

/*
 * Known printed set codes which are not guaranteed to be present in the
 * upstream set object. Sync-discovered aliases are added without overwriting
 * these curated values.
 */
INSERT INTO catalog_set_code_aliases (
    language_code,
    printed_code,
    set_id,
    source
)
VALUES
    ('de', 'PAL', 'sv02', 'curated'),
    ('de', 'JTG', 'sv09', 'curated'),
    ('de', 'CR1', 'me04', 'curated'),
    ('de', 'CRI', 'me04', 'curated'),
    ('de', 'M3', 'm3', 'curated'),
    ('ja', 'M1S', 'M1S', 'curated'),
    ('de', 'MEP', 'mep', 'curated'),
    ('en', 'PBL', 'me04', 'curated'),
    ('zh-tw', 'CBB1C', 'csv1c', 'curated'),
    ('zh-tw', 'CBB4C', 'cbb4c', 'curated')
ON CONFLICT DO NOTHING;
