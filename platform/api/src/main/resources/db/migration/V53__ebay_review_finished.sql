-- Durable review decisions; finished cards are queued again after 7d,
-- cards without verified sales after 30d. All historical rows stay intact.
ALTER TABLE ebay_card_review DROP CONSTRAINT IF EXISTS ebay_review_status_valid;
ALTER TABLE ebay_card_review ADD CONSTRAINT ebay_review_status_valid
 CHECK (review_status IN ('AUTO','NO_VERIFIED_SALE','OFFER_REVIEW','VERIFIED'));
