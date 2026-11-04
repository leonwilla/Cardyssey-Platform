-- Keep full eBay sold-item observations independently from the current rolling median.
-- A new quote must never delete observations previously collected for the chart.
CREATE TABLE IF NOT EXISTS ebay_sold_history (
 card_id TEXT NOT NULL,
 language_code VARCHAR(16) NOT NULL,
 variant_id TEXT NOT NULL,
 ebay_item_id TEXT NOT NULL,
 sold_on DATE NOT NULL,
 sold_eur NUMERIC(12,4) NOT NULL CHECK(sold_eur > 0),
 condition_label TEXT NOT NULL,
 condition_assumed BOOLEAN NOT NULL DEFAULT FALSE,
 variant_assumed BOOLEAN NOT NULL DEFAULT FALSE,
 title TEXT NOT NULL,
 listing_url TEXT NOT NULL,
 image_url TEXT,
 identity_basis TEXT NOT NULL,
 first_collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 last_collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(card_id,language_code,variant_id,ebay_item_id)
);
CREATE INDEX IF NOT EXISTS ebay_sold_history_timeline_idx
 ON ebay_sold_history(card_id,language_code,variant_id,sold_on DESC);

ALTER TABLE ebay_price_cache ADD COLUMN IF NOT EXISTS price_window_days INTEGER NOT NULL DEFAULT 30;
ALTER TABLE ebay_price_cache ADD COLUMN IF NOT EXISTS price_window_label TEXT NOT NULL DEFAULT '30 Tage';
ALTER TABLE ebay_price_cache ADD COLUMN IF NOT EXISTS low_sample BOOLEAN NOT NULL DEFAULT FALSE;
