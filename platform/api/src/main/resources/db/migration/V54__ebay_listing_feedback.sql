-- Human review examples: retained separately from the immutable sold history.
-- Feedback is audit/training input, never an automatic price override.
CREATE TABLE IF NOT EXISTS ebay_listing_feedback (
 card_id TEXT NOT NULL,
 ebay_item_id TEXT NOT NULL,
 language_code VARCHAR(16) NOT NULL DEFAULT 'de',
 decision TEXT NOT NULL,
 note TEXT NOT NULL DEFAULT '',
 listing_title TEXT NOT NULL DEFAULT '',
 last_reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(card_id,ebay_item_id,language_code),
 CONSTRAINT ebay_listing_feedback_decision_check CHECK(decision IN (
  'WRONG_CARD','VALID_SINGLE_SALE','MULTI_SELECTION','WRONG_VARIANT','PAID_PRICE_UNKNOWN','OTHER'))
);
CREATE INDEX IF NOT EXISTS ebay_listing_feedback_reviewed_idx ON ebay_listing_feedback(last_reviewed_at DESC);
