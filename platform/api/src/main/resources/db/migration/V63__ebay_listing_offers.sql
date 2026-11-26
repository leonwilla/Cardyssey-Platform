-- eBay-Angebote je Kartenvariante (Ersatzpreis, wenn Cardmarket keinen Preis hat).
-- listings: bis zu 5 günstigste passende Angebote {title, eur, url, itemId}.
CREATE TABLE IF NOT EXISTS ebay_listing_offers (
    language_code text NOT NULL,
    card_id text NOT NULL,
    variant_id text NOT NULL,
    price_eur numeric,
    offer_count integer NOT NULL DEFAULT 0,
    match_status text NOT NULL,
    listings jsonb NOT NULL DEFAULT '[]'::jsonb,
    query text,
    checked_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (language_code, card_id, variant_id)
);
CREATE INDEX IF NOT EXISTS ebay_listing_offers_checked ON ebay_listing_offers (checked_at);
