CREATE TABLE IF NOT EXISTS cardmarket_print_identity_review (
 language_code text NOT NULL CHECK(language_code IN ('de','en')),
 card_id text NOT NULL,
 variant_id text NOT NULL,
 set_id text NOT NULL,
 card_name text,
 printed_number text,
 print_type text,
 foil text,
 subtype text,
 stamps text,
 candidate_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
 matched_set_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
 provider_expansion_id text,
 classification text NOT NULL,
 product_names text,
 status text NOT NULL DEFAULT 'PENDING_REVIEW'
   CHECK(status IN ('PENDING_REVIEW','CONFIRMED_PRINT','NO_MATCH','DEFERRED')),
 selected_product_id text,
 reviewer_note text,
 checked_at timestamptz NOT NULL DEFAULT NOW(),
 reviewed_at timestamptz,
 PRIMARY KEY(language_code,card_id,variant_id),
 CONSTRAINT review_selected_product_must_be_listed CHECK (
   selected_product_id IS NULL OR candidate_ids ? selected_product_id
 )
);
CREATE INDEX IF NOT EXISTS idx_cardmarket_print_identity_review_status
 ON cardmarket_print_identity_review(status,language_code,checked_at DESC);
COMMENT ON TABLE cardmarket_print_identity_review IS
 'Human review evidence; DOES NOT authorize publishing language-specific Cardmarket guide prices.';
