ALTER TABLE ebay_price_cache
    ADD COLUMN recent_sales JSONB NOT NULL DEFAULT '[]'::jsonb;
