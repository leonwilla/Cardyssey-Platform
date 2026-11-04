-- Audited public sold-item purchase history; no buyer names are stored.
CREATE TABLE IF NOT EXISTS ebay_purchase_history_check (
 ebay_item_id text PRIMARY KEY,
 checked_at timestamptz NOT NULL DEFAULT now(),
 status text NOT NULL,
 transactions jsonb NOT NULL DEFAULT '[]'::jsonb,
 reason text,
 CONSTRAINT ebay_purchase_history_status CHECK(status IN ('VERIFIED_ROWS','NO_PURCHASE_ROWS','NO_VISIBLE_PRICE','BLOCKED','LOGIN_REQUIRED','UNAVAILABLE','UNSAFE_LAYOUT'))
);
CREATE INDEX IF NOT EXISTS ebay_purchase_history_checked_idx ON ebay_purchase_history_check(checked_at);
ALTER TABLE ebay_sold_history ADD COLUMN IF NOT EXISTS evidence_type text NOT NULL DEFAULT 'SOLD_SEARCH';
ALTER TABLE ebay_sold_history ADD COLUMN IF NOT EXISTS quantity int NOT NULL DEFAULT 1;
