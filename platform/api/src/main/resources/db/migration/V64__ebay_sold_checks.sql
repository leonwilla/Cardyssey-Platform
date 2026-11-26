-- Wann der eBay-Verkaufsscanner eine Karte zuletzt geprüft hat (Planung der Reihenfolge).
CREATE TABLE IF NOT EXISTS ebay_sold_checks (
    language_code text NOT NULL,
    card_id text NOT NULL,
    checked_at timestamptz NOT NULL DEFAULT now(),
    items_seen integer NOT NULL DEFAULT 0,
    sales_matched integer NOT NULL DEFAULT 0,
    PRIMARY KEY (language_code, card_id)
);
