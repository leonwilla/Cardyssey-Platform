CREATE TABLE IF NOT EXISTS price_review_cases (
 language_code text NOT NULL,
 card_id text NOT NULL,
 variant_id text NOT NULL,
 search_status text NOT NULL,
 search_query text,
 search_steps jsonb NOT NULL DEFAULT '[]'::jsonb,
 candidates jsonb NOT NULL DEFAULT '[]'::jsonb,
 failure_reason text,
 checked_at timestamptz NOT NULL DEFAULT NOW(),
 PRIMARY KEY (language_code,card_id,variant_id)
);
CREATE INDEX IF NOT EXISTS idx_price_review_cases_status ON price_review_cases(search_status,checked_at DESC);
