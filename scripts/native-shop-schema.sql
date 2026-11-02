-- Cardyssey native shop schema v1. PostgreSQL 17.
-- Run only after backup and staging review; does not touch WordPress.
BEGIN;
CREATE SCHEMA IF NOT EXISTS cardyssey_shop;
CREATE TABLE IF NOT EXISTS cardyssey_shop.products (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 type TEXT NOT NULL CHECK(type IN ('card','sealed','accessory','other')),
 card_id TEXT, set_id TEXT, language TEXT CHECK (language IN ('de','en','ja','ko','zh-cn','zh-tw')),
 title TEXT NOT NULL CHECK(length(trim(title)) > 0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE (card_id,set_id,language),
 CHECK ((type='card' AND card_id IS NOT NULL AND set_id IS NOT NULL AND language IS NOT NULL)
 OR (type <> 'card' AND card_id IS NULL AND set_id IS NULL AND language IS NULL))
);
-- Sealed products (booster, display, ETB) can belong to a set without a card ID.
ALTER TABLE cardyssey_shop.products ADD COLUMN IF NOT EXISTS associated_set_id TEXT;
ALTER TABLE cardyssey_shop.products ADD COLUMN IF NOT EXISTS associated_language TEXT;
CREATE TABLE IF NOT EXISTS cardyssey_shop.categories (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 parent_id BIGINT REFERENCES cardyssey_shop.categories(id) ON DELETE RESTRICT,
 slug TEXT NOT NULL UNIQUE,
 name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cardyssey_shop.product_categories (
 product_id BIGINT NOT NULL REFERENCES cardyssey_shop.products(id) ON DELETE CASCADE,
 category_id BIGINT NOT NULL REFERENCES cardyssey_shop.categories(id) ON DELETE CASCADE,
 PRIMARY KEY(product_id,category_id)
);
CREATE TABLE IF NOT EXISTS cardyssey_shop.offers (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 product_id BIGINT NOT NULL REFERENCES cardyssey_shop.products(id) ON DELETE RESTRICT,
 sku TEXT NOT NULL UNIQUE,
 variant TEXT NOT NULL,
 condition TEXT NOT NULL,
 price_minor BIGINT CHECK(price_minor >= 0),
 currency CHAR(3) NOT NULL DEFAULT 'EUR',
 stock_quantity INT NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
 reserved_quantity INT NOT NULL DEFAULT 0 CHECK(reserved_quantity >= 0 AND reserved_quantity <= stock_quantity),
 status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','archived')),
 version BIGINT NOT NULL DEFAULT 1,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(status <> 'published' OR (price_minor IS NOT NULL AND price_minor > 0 AND stock_quantity > reserved_quantity))
);
CREATE TABLE IF NOT EXISTS cardyssey_shop.offer_media (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 offer_id BIGINT NOT NULL REFERENCES cardyssey_shop.offers(id) ON DELETE CASCADE,
 media_url TEXT NOT NULL,
 is_owned_photo BOOLEAN NOT NULL DEFAULT FALSE,
 rights_verified BOOLEAN NOT NULL DEFAULT FALSE,
 position INT NOT NULL DEFAULT 0,
 CHECK(length(media_url) < 2048)
);
CREATE TABLE IF NOT EXISTS cardyssey_shop.orders (
 id UUID PRIMARY KEY,
 buyer_user_id TEXT,
 buyer_email TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('pending','awaiting_payment','paid','fulfilling','shipped','completed','cancelled','refunded','partially_refunded')),
 currency CHAR(3) NOT NULL DEFAULT 'EUR',
 subtotal_minor BIGINT NOT NULL CHECK(subtotal_minor >= 0),
 shipping_minor BIGINT NOT NULL CHECK(shipping_minor >= 0),
 tax_minor BIGINT NOT NULL CHECK(tax_minor >= 0),
 total_minor BIGINT NOT NULL CHECK(total_minor >= 0),
 idempotency_key TEXT NOT NULL UNIQUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS cardyssey_shop.order_items (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 order_id UUID NOT NULL REFERENCES cardyssey_shop.orders(id) ON DELETE RESTRICT,
 offer_id BIGINT NOT NULL REFERENCES cardyssey_shop.offers(id) ON DELETE RESTRICT,
 sku_snapshot TEXT NOT NULL,
 title_snapshot TEXT NOT NULL,
 variant_snapshot TEXT NOT NULL,
 condition_snapshot TEXT NOT NULL,
 quantity INT NOT NULL CHECK(quantity > 0),
 unit_price_minor BIGINT NOT NULL CHECK(unit_price_minor >= 0),
 UNIQUE(order_id,offer_id)
);
CREATE TABLE IF NOT EXISTS cardyssey_shop.payment_events (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 order_id UUID NOT NULL REFERENCES cardyssey_shop.orders(id),
 provider TEXT NOT NULL,
 provider_event_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(provider,provider_event_id)
);
CREATE TABLE IF NOT EXISTS cardyssey_shop.stock_movements (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 offer_id BIGINT NOT NULL REFERENCES cardyssey_shop.offers(id),
 order_id UUID REFERENCES cardyssey_shop.orders(id),
 delta INT NOT NULL CHECK(delta <> 0),
 reason TEXT NOT NULL,
 idempotency_key TEXT NOT NULL UNIQUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS cardyssey_shop.audit_events (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 actor_user_id TEXT,
 action TEXT NOT NULL,
 entity_type TEXT NOT NULL,
 entity_id TEXT NOT NULL,
 details JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS shop_offer_visibility_idx ON cardyssey_shop.offers(status,product_id);
CREATE INDEX IF NOT EXISTS shop_orders_created_idx ON cardyssey_shop.orders(created_at DESC);
CREATE INDEX IF NOT EXISTS shop_stock_history_idx ON cardyssey_shop.stock_movements(offer_id,created_at DESC);
-- No DB permissions granted to unauthenticated clients; backend must authorize.
COMMIT;
