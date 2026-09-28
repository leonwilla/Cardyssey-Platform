-- Read-only audit. Counts cover stored source records, not every printed card.
SELECT s.language_code, s.status, s.phase,
       s.last_completed_at, s.next_sync_at, s.last_error,
       COUNT(c.card_id) AS cards,
       COUNT(*) FILTER (WHERE c.details_complete) AS details_complete,
       COUNT(*) FILTER (WHERE c.image_complete AND c.image_dhash IS NOT NULL) AS indexed_images,
       COUNT(*) FILTER (WHERE c.card_id IS NOT NULL AND c.image_source_url IS NULL) AS missing_image_source,
       COUNT(*) FILTER (WHERE c.image_source_url IS NOT NULL AND NOT c.image_complete) AS pending_images,
       COUNT(*) FILTER (WHERE c.details_complete AND c.raw_payload->>'languageCode' IS NOT NULL AND c.raw_payload->>'languageCode' <> c.language_code) AS detail_language_mismatches,
       COUNT(*) FILTER (WHERE c.details_complete AND c.raw_payload->>'languageCode' IS NULL) AS missing_detail_language_metadata
FROM catalog_sync_state s
LEFT JOIN catalog_cards_mirror c ON c.language_code = s.language_code
GROUP BY s.language_code, s.status, s.phase, s.last_completed_at, s.next_sync_at, s.last_error
ORDER BY s.language_code;

-- Up to ten concrete gaps per language (not the first sixty from one language).
WITH gaps AS (
    SELECT language_code, set_id, card_id, local_id, name, image_source_url,
           details_complete, image_complete,
           ROW_NUMBER() OVER (PARTITION BY language_code ORDER BY set_id, card_id) AS n
    FROM catalog_cards_mirror
    WHERE language_code IN ('ja', 'ko', 'zh-cn', 'zh-tw', 'th', 'id')
      AND NOT image_complete
)
SELECT * FROM gaps WHERE n <= 10 ORDER BY language_code, n;

SELECT source, status, card_count, last_error, updated_at
FROM catalog_supplemental_sync ORDER BY source;
