-- Admin review is independent of an observed sold price and never deletes observations.
CREATE TABLE IF NOT EXISTS ebay_card_review (
 card_id TEXT NOT NULL,
 language_code VARCHAR(16) NOT NULL DEFAULT 'de',
 review_status TEXT NOT NULL DEFAULT 'AUTO',
 refresh_days INTEGER NOT NULL DEFAULT 7,
 show_offer_references BOOLEAN NOT NULL DEFAULT TRUE,
 note TEXT NOT NULL DEFAULT '',
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(card_id,language_code),
 CONSTRAINT ebay_review_status_valid CHECK(review_status IN ('AUTO','NO_VERIFIED_SALE','OFFER_REVIEW')),
 CONSTRAINT ebay_review_days_valid CHECK(refresh_days IN (7,14,30))
);
CREATE TABLE IF NOT EXISTS ebay_offer_reference (
 card_id TEXT NOT NULL,
 language_code VARCHAR(16) NOT NULL DEFAULT 'de',
 ebay_item_id TEXT NOT NULL,
 title TEXT NOT NULL,
 listing_url TEXT NOT NULL,
 image_url TEXT,
 displayed_price_eur NUMERIC(12,4),
 first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 reference_kind TEXT NOT NULL DEFAULT 'MULTI_SELECT',
 sale_for_card_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
 PRIMARY KEY(card_id,language_code,ebay_item_id)
);
CREATE INDEX IF NOT EXISTS ebay_card_review_updated_idx ON ebay_card_review(updated_at);
CREATE INDEX IF NOT EXISTS ebay_offer_reference_card_idx ON ebay_offer_reference(card_id,language_code);
