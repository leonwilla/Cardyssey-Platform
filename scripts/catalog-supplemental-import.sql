-- Appended to a transaction containing source_rows(payload JSONB).
-- Identity uses language + set + printed number + original name, never artwork alone.
CREATE TEMP TABLE resolved_rows ON COMMIT DROP AS
SELECT p || jsonb_build_object(
    'canonicalId', COALESCE(existing.canonical_card_id, matched.card_id, p->>'sourceId'),
    'details', (p->'details') || jsonb_build_object(
        'id', COALESCE(existing.canonical_card_id, matched.card_id, p->>'sourceId'),
        'setId', COALESCE(matched.set_id, known_set.set_id, p->'details'->>'setId')
    )
) AS payload
FROM (SELECT payload AS p FROM source_rows) input
LEFT JOIN catalog_supplemental_cards existing
    ON existing.language_code = p->'details'->>'languageCode' AND existing.source_id = p->>'sourceId'
LEFT JOIN LATERAL (
    SELECT MIN(card_id) AS card_id, MIN(set_id) AS set_id
    FROM catalog_cards_mirror
    WHERE language_code = p->'details'->>'languageCode'
      AND UPPER(set_id) = UPPER(p->'details'->>'setId')
      AND COALESCE(NULLIF(LTRIM(local_id, '0'), ''), '0') =
          COALESCE(NULLIF(LTRIM(p->'details'->>'localId', '0'), ''), '0')
      -- Set + printed collector number is the stable print identity here.
      -- Localized names can differ between catalog sources (spacing, forms,
      -- punctuation and translations), so require the name only when the
      -- number is not unique inside the set.
      AND (
          name = p->'details'->>'name'
          OR (
              SELECT COUNT(*)
              FROM catalog_cards_mirror same_print
              WHERE same_print.language_code = p->'details'->>'languageCode'
                AND UPPER(same_print.set_id) = UPPER(p->'details'->>'setId')
                AND COALESCE(NULLIF(LTRIM(same_print.local_id, '0'), ''), '0') =
                    COALESCE(NULLIF(LTRIM(p->'details'->>'localId', '0'), ''), '0')
                AND LEFT(same_print.card_id, 9) <> 'official_'
          ) = 1
      )
      AND (p->>'allowMatch')::boolean
      AND LEFT(card_id, 9) <> 'official_'
    HAVING COUNT(*) = 1
) matched ON TRUE
LEFT JOIN LATERAL (
    SELECT MIN(set_id) AS set_id FROM catalog_sets_mirror
    WHERE language_code = p->'details'->>'languageCode'
      AND UPPER(set_id) = UPPER(p->'details'->>'setId')
    HAVING COUNT(*) = 1
) known_set ON TRUE;

INSERT INTO catalog_supplemental_cards (
    language_code, source_id, canonical_card_id, details, source_url,
    source_revision, german_species_name, updated_at
)
SELECT payload->'details'->>'languageCode', payload->>'sourceId',
       payload->>'canonicalId', payload->'details', payload->>'sourceUrl',
       payload->>'revision', payload->>'germanSpecies', NOW()
FROM resolved_rows
ON CONFLICT (language_code, source_id) DO UPDATE SET
    details = EXCLUDED.details, source_url = EXCLUDED.source_url,
    source_revision = EXCLUDED.source_revision,
    german_species_name = EXCLUDED.german_species_name, updated_at = NOW();

INSERT INTO catalog_sets_mirror (
    language_code, set_id, name, official_count, total_count, raw_payload, last_seen_at
)
SELECT DISTINCT ON (payload->'details'->>'languageCode', payload->'details'->>'setId')
    payload->'details'->>'languageCode', payload->'details'->>'setId',
    payload->'details'->>'setName', (payload->'details'->>'officialCount')::integer,
    0, '{}'::jsonb, NOW()
FROM resolved_rows
ON CONFLICT (language_code, set_id) DO NOTHING;

INSERT INTO catalog_set_code_aliases(language_code, printed_code, set_id, source)
SELECT DISTINCT payload->'details'->>'languageCode', UPPER(payload->'details'->>'setId'),
    payload->'details'->>'setId', 'official-supplement'
FROM resolved_rows ON CONFLICT DO NOTHING;

-- Invalidate derived prices when their audited official identity changes.
CREATE TEMP TABLE invalidated_price_prints ON COMMIT DROP AS
SELECT DISTINCT c.card_id,c.language_code,c.raw_payload->>'_cardyssey_verified_variant_source' AS twin_source
FROM resolved_rows r JOIN catalog_cards_mirror c
  ON c.card_id=r.payload->>'canonicalId' AND c.language_code=r.payload->'details'->>'languageCode'
WHERE LEFT(c.card_id,9)='official_'
 AND (NULLIF(c.raw_payload->>'_cardyssey_verified_variant_source','') IS NOT NULL
      OR c.raw_payload->>'_cardyssey_retail_variant_source' IN ('WEB_UTURI_KO','WEB_MEWTWO_KO','WEB_LAKE_KO','WEB_MANA_KO','WEB_LEVELUP_KO','WEB_SHINY_KO','CARDTRADER_KO_NM'))
 AND NOT COALESCE((c.set_id=r.payload->'details'->>'setId'
   AND c.local_id=r.payload->'details'->>'localId'
   AND c.raw_payload->>'name'=r.payload->'details'->>'name'
   AND c.image_source_url=r.payload->'details'->>'imageBase'),FALSE);

INSERT INTO catalog_cards_mirror (
    language_code, card_id, set_id, local_id, name, rarity,
    image_source_url, variants, raw_payload, details_complete, source_updated_at, last_seen_at
)
SELECT DISTINCT ON (payload->'details'->>'languageCode', payload->>'canonicalId')
    payload->'details'->>'languageCode', payload->>'canonicalId',
    payload->'details'->>'setId', payload->'details'->>'localId',
    payload->'details'->>'name' ||
        CASE WHEN NULLIF(payload->>'germanSpecies', '') IS NULL THEN ''
             ELSE ' (' || (payload->>'germanSpecies') || ')' END,
    payload->'details'->>'rarity', payload->'details'->>'imageBase',
    '[]'::jsonb, payload->'details', TRUE, NOW(), NOW()
FROM resolved_rows
ON CONFLICT (language_code, card_id) DO UPDATE SET
    image_complete = CASE
        WHEN (LEFT(EXCLUDED.card_id, 9) = 'official_' OR catalog_cards_mirror.image_source_url IS NULL)
          AND EXCLUDED.image_source_url IS DISTINCT FROM catalog_cards_mirror.image_source_url
        THEN FALSE ELSE catalog_cards_mirror.image_complete END,
    image_dhash = CASE
        WHEN (LEFT(EXCLUDED.card_id, 9) = 'official_' OR catalog_cards_mirror.image_source_url IS NULL)
          AND EXCLUDED.image_source_url IS DISTINCT FROM catalog_cards_mirror.image_source_url
        THEN NULL ELSE catalog_cards_mirror.image_dhash END,
    image_source_url = CASE WHEN LEFT(EXCLUDED.card_id, 9) = 'official_'
        THEN EXCLUDED.image_source_url
        ELSE COALESCE(catalog_cards_mirror.image_source_url, EXCLUDED.image_source_url) END,
    name = CASE WHEN LEFT(EXCLUDED.card_id, 9) = 'official_' THEN EXCLUDED.name ELSE catalog_cards_mirror.name END,
    -- Preserve audited variant provenance only while the official print identity is unchanged.
    raw_payload = CASE WHEN LEFT(EXCLUDED.card_id, 9) = 'official_' THEN
        EXCLUDED.raw_payload || CASE WHEN catalog_cards_mirror.set_id=EXCLUDED.set_id
          AND catalog_cards_mirror.local_id=EXCLUDED.local_id
          AND catalog_cards_mirror.raw_payload->>'name'=EXCLUDED.raw_payload->>'name'
          AND catalog_cards_mirror.image_source_url=EXCLUDED.image_source_url THEN
          jsonb_strip_nulls(jsonb_build_object(
            '_cardyssey_verified_variant_source',catalog_cards_mirror.raw_payload->'_cardyssey_verified_variant_source',
            '_cardyssey_retail_variant_source',catalog_cards_mirror.raw_payload->'_cardyssey_retail_variant_source'))
          ELSE '{}'::jsonb END
        ELSE catalog_cards_mirror.raw_payload END,
    variants = CASE WHEN LEFT(EXCLUDED.card_id, 9) = 'official_'
        AND (NULLIF(catalog_cards_mirror.raw_payload->>'_cardyssey_verified_variant_source','') IS NOT NULL
          OR catalog_cards_mirror.raw_payload->>'_cardyssey_retail_variant_source' IN ('WEB_UTURI_KO','WEB_MEWTWO_KO','WEB_LAKE_KO','WEB_MANA_KO','WEB_LEVELUP_KO','WEB_SHINY_KO','CARDTRADER_KO_NM'))
        AND NOT COALESCE((catalog_cards_mirror.set_id=EXCLUDED.set_id
          AND catalog_cards_mirror.local_id=EXCLUDED.local_id
          AND catalog_cards_mirror.raw_payload->>'name'=EXCLUDED.raw_payload->>'name'
          AND catalog_cards_mirror.image_source_url=EXCLUDED.image_source_url),FALSE)
        THEN '[]'::jsonb ELSE catalog_cards_mirror.variants END,
    last_seen_at = NOW();

UPDATE tcg_price_cache p SET resolution_status='NO_PRICE',base_eur=NULL,updated_at=NOW(),next_attempt_at=NOW(),
 failure_detail='Audited supplemental print identity changed; derived price requires verification again'
FROM invalidated_price_prints c WHERE p.card_id=c.card_id AND p.language_code=c.language_code
 AND (p.source IN ('WEB_UTURI_KO','WEB_MEWTWO_KO','WEB_LAKE_KO','WEB_MANA_KO','WEB_LEVELUP_KO','WEB_SHINY_KO','CARDTRADER_KO_NM') OR (c.twin_source IS NOT NULL AND
      p.failure_detail LIKE '%Exact catalogue duplicate of ' || c.twin_source || ';%'));
