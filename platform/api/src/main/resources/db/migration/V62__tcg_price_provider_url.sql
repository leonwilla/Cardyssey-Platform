-- Link zur Cardmarket-Produktseite je Kartenvariante (verifizierte Zuordnung),
-- damit App und Webapp "Auf Cardmarket ansehen" anbieten können.
ALTER TABLE tcg_price_cache ADD COLUMN IF NOT EXISTS provider_url text;
