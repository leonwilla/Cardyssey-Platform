CREATE TABLE IF NOT EXISTS cardmarket_language_offer_samples (
  product_id text NOT NULL CHECK (product_id ~ '^[0-9]+$'),
  language_code text NOT NULL CHECK (language_code IN ('de','en')),
  minimum_condition text NOT NULL DEFAULT 'NM_OR_BETTER'
    CHECK (minimum_condition='NM_OR_BETTER'),
  sample_date date NOT NULL DEFAULT CURRENT_DATE,
  captured_at timestamptz NOT NULL DEFAULT NOW(),
  lowest_ask_eur numeric(14,4) NOT NULL CHECK (lowest_ask_eur>0),
  entry_five_median_eur numeric(14,4) NOT NULL CHECK (entry_five_median_eur>0),
  verified_preview_rows integer NOT NULL CHECK (verified_preview_rows>=5),
  visible_offers integer NOT NULL CHECK (visible_offers>=verified_preview_rows),
  print_scope text NOT NULL DEFAULT 'UNVERIFIED_PRINT_VARIANTS'
    CHECK (print_scope='UNVERIFIED_PRINT_VARIANTS'),
  price_basis text NOT NULL DEFAULT 'ACTIVE_ASKING_NOT_SOLD'
    CHECK (price_basis='ACTIVE_ASKING_NOT_SOLD'),
  source text NOT NULL DEFAULT 'CARDMARKET_BROWSER_PROBE',
  source_note text,
  PRIMARY KEY(product_id,language_code,minimum_condition,sample_date)
);
COMMENT ON TABLE cardmarket_language_offer_samples IS
 'Offer samples from browser filter with explicit language and at least NM; NOT sold prices or verified print variants; never auto-publish.';
