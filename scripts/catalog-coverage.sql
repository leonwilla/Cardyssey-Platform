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
WHERE s.language_code IN ('de', 'en', 'ko', 'ja', 'zh-tw', 'zh-cn')
GROUP BY s.language_code, s.status, s.phase, s.last_completed_at, s.next_sync_at, s.last_error
ORDER BY s.language_code;

-- Up to ten concrete gaps per language (not the first sixty from one language).
WITH gaps AS (
    SELECT language_code, set_id, card_id, local_id, name, image_source_url,
           details_complete, image_complete,
           ROW_NUMBER() OVER (PARTITION BY language_code ORDER BY set_id, card_id) AS n
    FROM catalog_cards_mirror
    WHERE language_code IN ('ja', 'ko', 'zh-cn', 'zh-tw')
      AND NOT image_complete
)
SELECT * FROM gaps WHERE n <= 10 ORDER BY language_code, n;

SELECT source, status, card_count, last_error, updated_at
FROM catalog_supplemental_sync
WHERE source IN ('type-null/ko', 'type-null/ja', 'type-null/zh-tw') ORDER BY source;


-- Set artwork audit for every app language. A set is considered visually
-- covered when either a logo or a symbol is known. Card artwork can still be
-- used by Android as a fallback, but missing branding remains visible here.
SELECT
    language_code,
    COUNT(*) AS sets,
    COUNT(*) FILTER (
        WHERE NULLIF(TRIM(COALESCE(logo_base, '')), '') IS NOT NULL
           OR NULLIF(TRIM(COALESCE(symbol_base, '')), '') IS NOT NULL
    ) AS sets_with_branding,
    COUNT(*) FILTER (
        WHERE NULLIF(TRIM(COALESCE(logo_base, '')), '') IS NULL
          AND NULLIF(TRIM(COALESCE(symbol_base, '')), '') IS NULL
    ) AS sets_without_branding
FROM catalog_sets_mirror
WHERE language_code IN ('de', 'en', 'ko', 'ja', 'zh-tw', 'zh-cn')
GROUP BY language_code
ORDER BY language_code;

-- Concrete sets without logo/symbol, capped per language so this stays useful
-- in terminal output instead of flooding the audit.
WITH set_gaps AS (
    SELECT
        language_code,
        set_id,
        name,
        ROW_NUMBER() OVER (
            PARTITION BY language_code
            ORDER BY set_id
        ) AS n
    FROM catalog_sets_mirror
    WHERE language_code IN ('de', 'en', 'ko', 'ja', 'zh-tw', 'zh-cn')
      AND NULLIF(TRIM(COALESCE(logo_base, '')), '') IS NULL
      AND NULLIF(TRIM(COALESCE(symbol_base, '')), '') IS NULL
)
SELECT language_code, set_id, name
FROM set_gaps
WHERE n <= 20
ORDER BY language_code, n;

-- Image failures worth repairing first: a source URL exists, but the mirror
-- still has no completed local image/hash. These are actionable download or
-- decode gaps rather than cards for which no source is known at all.
WITH actionable_image_gaps AS (
    SELECT
        language_code,
        set_id,
        card_id,
        local_id,
        name,
        image_source_url,
        ROW_NUMBER() OVER (
            PARTITION BY language_code
            ORDER BY set_id, card_id
        ) AS n
    FROM catalog_cards_mirror
    WHERE language_code IN ('de', 'en', 'ko', 'ja', 'zh-tw', 'zh-cn')
      AND image_source_url IS NOT NULL
      AND (
          NOT image_complete
          OR image_dhash IS NULL
      )
)
SELECT
    language_code,
    set_id,
    card_id,
    local_id,
    name,
    image_source_url
FROM actionable_image_gaps
WHERE n <= 25
ORDER BY language_code, n;

-- Cards with no known source at all. These need a source/backfill strategy,
-- not merely another mirror retry.
SELECT
    language_code,
    COUNT(*) AS cards_without_image_source
FROM catalog_cards_mirror
WHERE language_code IN ('de', 'en', 'ko', 'ja', 'zh-tw', 'zh-cn')
  AND image_source_url IS NULL
GROUP BY language_code
ORDER BY language_code;
