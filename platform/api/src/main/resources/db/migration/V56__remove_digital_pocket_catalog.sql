-- Digital Pokemon TCG Pocket is not a physical collectible card product.
-- Deliberately remove the legacy digital catalog and any user entries by request.
-- The source importer guards are implemented in CardCatalog/PermanentCatalogRepository.
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT table_name FROM information_schema.columns
    WHERE table_schema='public' AND column_name='card_id'
      AND table_name IN (
        'cardtrader_identity_cache','cardtrader_variant_identity_cache',
        'catalog_variant_reconstruction_queue','collection_items','wishlist_items',
        'ebay_card_review','ebay_listing_feedback','ebay_offer_reference',
        'ebay_price_cache','ebay_price_refresh_state','ebay_scan_checkpoint',
        'ebay_sold_history','global_price_source_policy','price_manual_review_audit',
        'price_reference_candidates','price_review_cases','price_source_routing',
        'tcg_price_cache','tcg_price_history')
  LOOP
    EXECUTE format('DELETE FROM public.%I WHERE card_id ~* %L',r.table_name,'^(A[0-9]|B[0-9]|P-A)-');
  END LOOP;
END $$;
DELETE FROM catalog_cards_mirror WHERE set_id ~* '^(A[0-9]|B[0-9]|P-A)';
DELETE FROM catalog_set_code_aliases WHERE set_id ~* '^(A[0-9]|B[0-9]|P-A)';
DELETE FROM catalog_sets_mirror WHERE set_id ~* '^(A[0-9]|B[0-9]|P-A)';
DELETE FROM catalog_cache WHERE cache_key ~* '/(cards|sets)/(A[0-9]|B[0-9]|P-A)(-|$|/)';
-- General /cards and /sets index caches may contain Pocket; remove to force fresh filtered reads.
DELETE FROM catalog_cache WHERE cache_key ~* '/(cards|sets)$';
