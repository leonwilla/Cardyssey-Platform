CREATE TABLE IF NOT EXISTS price_reference_candidates (
 language_code text NOT NULL,
 card_id text NOT NULL,
 variant_id text NOT NULL,
 provider text NOT NULL,
 price_eur numeric(15,4) NOT NULL CHECK (price_eur>0),
 currency text NOT NULL DEFAULT 'EUR',
 evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
 verification_status text NOT NULL DEFAULT 'UNVERIFIED_PRINT',
 observed_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(language_code,card_id,variant_id,provider)
);
CREATE INDEX IF NOT EXISTS idx_price_reference_candidates_review ON price_reference_candidates(verification_status,observed_at DESC);
