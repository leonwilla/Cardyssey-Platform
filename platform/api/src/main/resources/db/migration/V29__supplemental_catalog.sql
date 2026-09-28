CREATE TABLE catalog_supplemental_cards (
    language_code TEXT NOT NULL,
    source_id TEXT NOT NULL,
    canonical_card_id TEXT NOT NULL,
    details JSONB NOT NULL,
    source_url TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    german_species_name TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (language_code, source_id)
);
CREATE INDEX catalog_supplemental_canonical_idx
    ON catalog_supplemental_cards(language_code, canonical_card_id);

CREATE INDEX catalog_cards_exact_source_identity_idx ON catalog_cards_mirror (
    language_code, UPPER(set_id),
    (COALESCE(NULLIF(LTRIM(local_id, '0'), ''), '0')), name
);

CREATE TABLE catalog_supplemental_sync (
    source TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    card_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
