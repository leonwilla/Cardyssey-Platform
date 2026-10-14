CREATE TABLE IF NOT EXISTS price_manual_review_audit (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 operator_id uuid NOT NULL,
 language_code text NOT NULL,
 card_id text NOT NULL,
 variant_id text NOT NULL,
 source_url text NOT NULL,
 entered_price_eur numeric(15,4) NOT NULL,
 entered_condition text NOT NULL,
 stored_base_eur numeric(15,4) NOT NULL,
 previous_base_eur numeric(15,4),
 previous_status text,
 previous_source text,
 note text,
 reviewed_at timestamptz NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS price_manual_review_audit_card_idx
 ON price_manual_review_audit(language_code,card_id,variant_id,reviewed_at DESC);
