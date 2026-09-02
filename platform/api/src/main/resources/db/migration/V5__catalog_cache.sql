CREATE TABLE IF NOT EXISTS catalog_cache (
    cache_key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catalog_cache_updated_at
    ON catalog_cache(updated_at);
