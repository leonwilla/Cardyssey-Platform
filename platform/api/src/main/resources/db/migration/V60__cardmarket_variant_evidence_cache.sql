-- Evidence cache, not a market price source.
-- User-approved print identities are kept distinct from unverified product
-- candidates and from listing-level asking-price diagnostics.
CREATE TABLE IF NOT EXISTS cardmarket_variant_mappings (
    language_code text NOT NULL CHECK (language_code IN ('de','en','ja','ko','zh-cn','zh-tw')),
    card_id text NOT NULL,
    variant_id text NOT NULL,
    product_id text NOT NULL CHECK (product_id ~ '^[0-9]{4,12}$'),
    print_type text NOT NULL DEFAULT 'unknown',
    set_slug text,
    product_url text,
    is_reverse_holo boolean,
    required_comment_pattern text,
    mapping_status text NOT NULL DEFAULT 'PENDING_REVIEW'
      CHECK (mapping_status IN ('PENDING_REVIEW','HUMAN_CONFIRMED','REJECTED')),
    confidence text NOT NULL DEFAULT 'LOW'
      CHECK (confidence IN ('LOW','MEDIUM','HIGH')),
    evidence_type text NOT NULL DEFAULT 'VERSION_FAMILY_CANDIDATE',
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    confirmed_by text,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    PRIMARY KEY (language_code,card_id,variant_id,product_id),
    CONSTRAINT only_human_confirmation_is_verified CHECK (
      (mapping_status <> 'HUMAN_CONFIRMED'
       AND verified_at IS NULL
       AND confirmed_by IS NULL)
      OR (mapping_status='HUMAN_CONFIRMED'
          AND confidence='HIGH'
          AND verified_at IS NOT NULL
          AND confirmed_by IS NOT NULL)
    )
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cardmarket_variant_confirmed
 ON cardmarket_variant_mappings (language_code,card_id,variant_id)
 WHERE mapping_status='HUMAN_CONFIRMED';
CREATE INDEX IF NOT EXISTS ix_cardmarket_variant_mapping_product
 ON cardmarket_variant_mappings (product_id,language_code);
CREATE INDEX IF NOT EXISTS ix_cardmarket_variant_mapping_review
 ON cardmarket_variant_mappings (mapping_status,language_code,updated_at DESC);

CREATE TABLE IF NOT EXISTS cardmarket_variant_offer_diagnostics (
    id bigserial PRIMARY KEY,
    language_code text NOT NULL CHECK (language_code IN ('de','en','ja','ko','zh-cn','zh-tw')),
    card_id text NOT NULL,
    variant_id text NOT NULL,
    product_id text NOT NULL CHECK (product_id ~ '^[0-9]{4,12}$'),
    observed_at timestamptz NOT NULL DEFAULT NOW(),
    total_offer_rows integer NOT NULL CHECK (total_offer_rows>=0),
    accepted_offer_rows integer NOT NULL CHECK (accepted_offer_rows>=0),
    excluded_reasons jsonb NOT NULL DEFAULT '{}'::jsonb,
    all_pages_complete boolean NOT NULL DEFAULT false,
    exact_print_verified boolean NOT NULL DEFAULT false,
    asking_median_eur numeric(14,4),
    iqr_median_diagnostic_eur numeric(14,4),
    guide_ratio numeric(12,4),
    price_basis text NOT NULL DEFAULT 'ACTIVE_ASKING_NOT_SOLD'
      CHECK (price_basis='ACTIVE_ASKING_NOT_SOLD'),
    published_to_price_cache boolean NOT NULL DEFAULT false
      CHECK (published_to_price_cache=false),
    details jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_cardmarket_variant_offer_diagnostics_recent
 ON cardmarket_variant_offer_diagnostics (language_code,card_id,variant_id,observed_at DESC);
COMMENT ON TABLE cardmarket_variant_mappings IS
 'Cardmarket page candidates, with independently human-confirmed print mappings only. No implied V1/V2 or price mapping.';
COMMENT ON TABLE cardmarket_variant_offer_diagnostics IS
 'Read-only evidence for active asking offers; never directly publishes to Cardyssey price caches.';
