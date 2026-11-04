-- One shared, auditable source decision per exact catalog print and language.
-- This table NEVER writes prices or substitutes a price from another language.
CREATE TABLE IF NOT EXISTS global_price_source_policy (
 language_code text NOT NULL,
 card_id text NOT NULL,
 variant_id text NOT NULL,
 set_id text NOT NULL,
 rarity text,
 price_class text NOT NULL CHECK(price_class IN ('BULK','SPECIAL','RARITY_UNVERIFIED')),
 preferred_market text NOT NULL CHECK(preferred_market IN ('TCG','EBAY','LOCAL_MARKET')),
 preferred_provider_family text NOT NULL,
 selected_price_source text,
 selected_price_eur numeric(14,4),
 price_status text NOT NULL CHECK(price_status IN ('PRICE_FOUND','MISSING_LOCAL_PRICE','RARITY_REVIEW','NO_EXACT_VARIANT')),
 price_checked_at timestamptz,
 policy_updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(language_code,card_id,variant_id)
);
CREATE INDEX IF NOT EXISTS global_price_policy_gap_idx ON global_price_source_policy(language_code,price_status,price_class);
CREATE INDEX IF NOT EXISTS global_price_policy_set_idx ON global_price_source_policy(language_code,set_id,price_class);
CREATE TABLE IF NOT EXISTS global_price_policy_sync (
 id integer PRIMARY KEY DEFAULT 1 CHECK(id=1),
 last_success_at timestamptz NOT NULL DEFAULT now(),
 total_prints integer NOT NULL,
 bulk_prints integer NOT NULL,
 missing_prints integer NOT NULL,
 summary jsonb NOT NULL DEFAULT '{}'::jsonb
);
