-- Per-card scan cursor is advanced only after a complete successful sold search.
CREATE TABLE IF NOT EXISTS ebay_scan_checkpoint(
 card_id TEXT NOT NULL,
 language_code VARCHAR(16) NOT NULL,
 search_query TEXT NOT NULL,
 last_success_at TIMESTAMPTZ NOT NULL,
 PRIMARY KEY(card_id,language_code)
);
CREATE INDEX IF NOT EXISTS ebay_scan_checkpoint_updated_idx ON ebay_scan_checkpoint(last_success_at);
