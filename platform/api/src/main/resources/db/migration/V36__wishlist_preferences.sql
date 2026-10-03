ALTER TABLE wishlist_items
    ADD COLUMN IF NOT EXISTS priority TEXT NOT NULL DEFAULT 'MEDIUM',
    ADD COLUMN IF NOT EXISTS target_price_eur NUMERIC(12, 2);

ALTER TABLE wishlist_items
    DROP CONSTRAINT IF EXISTS wishlist_items_priority_check;

ALTER TABLE wishlist_items
    ADD CONSTRAINT wishlist_items_priority_check
    CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH'));

ALTER TABLE wishlist_items
    DROP CONSTRAINT IF EXISTS wishlist_items_target_price_check;

ALTER TABLE wishlist_items
    ADD CONSTRAINT wishlist_items_target_price_check
    CHECK (target_price_eur IS NULL OR target_price_eur >= 0);
