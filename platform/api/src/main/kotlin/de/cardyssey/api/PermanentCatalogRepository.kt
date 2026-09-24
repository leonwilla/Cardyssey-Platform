package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable
import java.nio.file.Files
import java.nio.file.Path

data class MirrorImageWork(
    val language: String,
    val cardId: String,
    val setId: String,
    val localId: String,
    val name: String,
    val sourceUrl: String?
)

@Serializable
data class CatalogVisualMatch(
    val card: CatalogCardSearchResult,
    val distance: Int
)

@Serializable
data class CatalogMirrorStatus(
    val language: String,
    val status: String,
    val phase: String,
    val setCount: Int,
    val cardCount: Int,
    val imageCount: Int,
    val lastError: String?
)

class PermanentCatalogRepository(
    private val dataSource: HikariDataSource,
    private val catalogDir: Path,
    private val publicBaseUrl: String
) {
    init {
        Files.createDirectories(catalogDir.resolve("cards"))
    }

    fun imagePath(language: String, cardId: String): Path =
        catalogDir
            .resolve("cards")
            .resolve(safe(language))
            .resolve("${safe(cardId)}.jpg")

    fun imageBase(language: String, cardId: String): String =
        publicBaseUrl.removeSuffix("/") +
            "/api/v1/catalog/assets/${safe(language)}/${safe(cardId)}"

    fun storedImage(language: String, cardId: String): Path? =
        imagePath(language, cardId).takeIf(Files::isRegularFile)

    fun upsertSet(
        language: String,
        set: CatalogSetSummary,
        rawPayload: String
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO catalog_sets_mirror (
                    language_code, set_id, name, official_count,
                    total_count, logo_source_url, symbol_source_url,
                    raw_payload, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
                ON CONFLICT (language_code, set_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    official_count = EXCLUDED.official_count,
                    total_count = EXCLUDED.total_count,
                    logo_source_url = EXCLUDED.logo_source_url,
                    symbol_source_url = EXCLUDED.symbol_source_url,
                    raw_payload = EXCLUDED.raw_payload,
                    last_seen_at = NOW()
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, language)
                statement.setString(2, set.id)
                statement.setString(3, set.name)
                statement.setInt(4, set.officialCount)
                statement.setInt(5, set.totalCount)
                statement.setString(6, set.logo)
                statement.setString(7, set.symbol)
                statement.setString(8, rawPayload)
                statement.executeUpdate()
            }

            connection.prepareStatement(
                """
                INSERT INTO catalog_set_code_aliases (
                    language_code, printed_code, set_id, source
                ) VALUES (?, ?, ?, 'catalog-id')
                ON CONFLICT DO NOTHING
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, language)
                statement.setString(2, set.id.uppercase())
                statement.setString(3, set.id)
                statement.executeUpdate()
            }
        }
    }

    fun upsertCard(
        language: String,
        card: CatalogCardSearchResult,
        rawPayload: String,
        rarity: String? = null,
        variantsJson: String = "[]",
        detailsComplete: Boolean = false
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO catalog_cards_mirror (
                    language_code, card_id, set_id, local_id, name,
                    rarity, image_source_url, variants, raw_payload,
                    details_complete, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, ?, NOW())
                ON CONFLICT (language_code, card_id)
                DO UPDATE SET
                    set_id = EXCLUDED.set_id,
                    local_id = EXCLUDED.local_id,
                    name = EXCLUDED.name,
                    rarity = COALESCE(EXCLUDED.rarity, catalog_cards_mirror.rarity),
                    image_source_url = COALESCE(EXCLUDED.image_source_url, catalog_cards_mirror.image_source_url),
                    variants = CASE
                        WHEN EXCLUDED.details_complete THEN EXCLUDED.variants
                        ELSE catalog_cards_mirror.variants
                    END,
                    raw_payload = EXCLUDED.raw_payload,
                    details_complete = catalog_cards_mirror.details_complete OR EXCLUDED.details_complete,
                    source_updated_at = CASE
                        WHEN EXCLUDED.details_complete THEN NOW()
                        ELSE catalog_cards_mirror.source_updated_at
                    END,
                    last_seen_at = NOW()
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, language)
                statement.setString(2, card.id)
                statement.setString(3, card.setId)
                statement.setString(4, card.localId)
                statement.setString(5, card.name)
                statement.setString(6, rarity)
                statement.setString(7, card.imageBase)
                statement.setString(8, variantsJson)
                statement.setString(9, rawPayload)
                statement.setBoolean(10, detailsComplete)
                statement.executeUpdate()
            }
        }
    }

    fun pendingImages(language: String, limit: Int): List<MirrorImageWork> =
        pendingWork(
            language = language,
            predicate =
                "image_complete = FALSE " +
                    "AND image_source_url IS NOT NULL",
            limit = limit
        )

    fun pendingDetails(language: String, limit: Int): List<MirrorImageWork> =
        pendingWork(
            language = language,
            predicate =
                "details_complete = FALSE OR " +
                    "source_updated_at < NOW() - INTERVAL '30 days'",
            limit = limit
        )

    private fun pendingWork(
        language: String,
        predicate: String,
        limit: Int
    ): List<MirrorImageWork> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT language_code, card_id, set_id, local_id, name, image_source_url
                FROM catalog_cards_mirror
                WHERE language_code = ?
                  AND $predicate
                ORDER BY first_seen_at, card_id
                LIMIT ?
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, language)
                statement.setInt(2, limit.coerceIn(1, 5000))
                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            add(
                                MirrorImageWork(
                                    language = result.getString("language_code"),
                                    cardId = result.getString("card_id"),
                                    setId = result.getString("set_id"),
                                    localId = result.getString("local_id"),
                                    name = result.getString("name"),
                                    sourceUrl = result.getString("image_source_url")
                                )
                            )
                        }
                    }
                }
            }
        }

    fun completeImage(
        language: String,
        cardId: String,
        path: Path,
        hash: Long,
        byteCount: Long
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE catalog_cards_mirror
                SET image_local_path = ?, image_dhash = ?, image_bytes = ?,
                    image_complete = TRUE, last_seen_at = NOW()
                WHERE language_code = ? AND card_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, catalogDir.relativize(path).toString())
                statement.setLong(2, hash)
                statement.setLong(3, byteCount)
                statement.setString(4, language)
                statement.setString(5, cardId)
                statement.executeUpdate()
            }
        }
    }

    fun visualMatches(
        language: String,
        hash: Long,
        number: String?,
        setCode: String? = null,
        limit: Int
    ): List<CatalogVisualMatch> {
        val normalizedNumber = normalizeNumber(number)
        val resolvedSetId = resolveSetId(language, setCode)

        val rows = dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT c.card_id, c.local_id, c.name, c.set_id,
                       s.name AS set_name, c.image_dhash
                FROM catalog_cards_mirror c
                LEFT JOIN catalog_sets_mirror s
                  ON s.language_code = c.language_code AND s.set_id = c.set_id
                WHERE c.language_code = ? AND c.image_dhash IS NOT NULL
                  AND (
                    ? IS NULL OR
                    CASE
                      WHEN REGEXP_REPLACE(UPPER(c.local_id), '[^A-Z0-9]', '', 'g') ~ '^[0-9]+$'
                        THEN COALESCE(NULLIF(LTRIM(REGEXP_REPLACE(UPPER(c.local_id), '[^A-Z0-9]', '', 'g'), '0'), ''), '0')
                      ELSE REGEXP_REPLACE(
                        REGEXP_REPLACE(UPPER(c.local_id), '[^A-Z0-9]', '', 'g'),
                        '^([A-Z]+)0+([0-9])',
                        '\\1\\2'
                      )
                    END = ?
                  )
                  AND (? IS NULL OR c.set_id = ?)
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, language)
                statement.setString(2, normalizedNumber)
                statement.setString(3, normalizedNumber)
                statement.setString(4, resolvedSetId)
                statement.setString(5, resolvedSetId)
                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            val id = result.getString("card_id")
                            add(
                                CatalogCardSearchResult(
                                    id = id,
                                    localId = result.getString("local_id"),
                                    name = result.getString("name"),
                                    setId = result.getString("set_id"),
                                    setName = result.getString("set_name"),
                                    imageBase = imageBase(language, id)
                                ) to result.getLong("image_dhash")
                            )
                        }
                    }
                }
            }
        }

        return rows
            .asSequence()
            .map { (card, storedHash) ->
                CatalogVisualMatch(
                    card = card,
                    distance = java.lang.Long.bitCount(storedHash xor hash)
                )
            }
            .sortedBy(CatalogVisualMatch::distance)
            .take(limit.coerceIn(1, 50))
            .toList()
    }

    fun updateStatus(
        language: String,
        status: String,
        phase: String,
        error: String? = null,
        nextSyncHours: Long? = null
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO catalog_sync_state (
                    language_code, status, phase, last_started_at,
                    last_completed_at, next_sync_at, set_count,
                    card_count, image_count, last_error
                ) VALUES (
                    ?, ?, ?,
                    CASE WHEN ? = 'running' THEN NOW() ELSE NULL END,
                    CASE WHEN ? = 'ready' THEN NOW() ELSE NULL END,
                    CASE WHEN ? IS NULL THEN NULL ELSE NOW() + (? * INTERVAL '1 hour') END,
                    (SELECT COUNT(*) FROM catalog_sets_mirror WHERE language_code = ?),
                    (SELECT COUNT(*) FROM catalog_cards_mirror WHERE language_code = ?),
                    (SELECT COUNT(*) FROM catalog_cards_mirror WHERE language_code = ? AND image_complete),
                    ?
                )
                ON CONFLICT (language_code)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    phase = EXCLUDED.phase,
                    last_started_at = COALESCE(EXCLUDED.last_started_at, catalog_sync_state.last_started_at),
                    last_completed_at = COALESCE(EXCLUDED.last_completed_at, catalog_sync_state.last_completed_at),
                    next_sync_at = EXCLUDED.next_sync_at,
                    set_count = EXCLUDED.set_count,
                    card_count = EXCLUDED.card_count,
                    image_count = EXCLUDED.image_count,
                    last_error = EXCLUDED.last_error
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, language)
                statement.setString(2, status)
                statement.setString(3, phase)
                statement.setString(4, status)
                statement.setString(5, status)
                statement.setObject(6, nextSyncHours)
                statement.setObject(7, nextSyncHours)
                statement.setString(8, language)
                statement.setString(9, language)
                statement.setString(10, language)
                statement.setString(11, error)
                statement.executeUpdate()
            }
        }
    }

    fun statuses(): List<CatalogMirrorStatus> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT language_code, status, phase, set_count,
                       card_count, image_count, last_error
                FROM catalog_sync_state
                ORDER BY language_code
                """.trimIndent()
            ).use { statement ->
                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            add(
                                CatalogMirrorStatus(
                                    language = result.getString("language_code"),
                                    status = result.getString("status"),
                                    phase = result.getString("phase"),
                                    setCount = result.getInt("set_count"),
                                    cardCount = result.getInt("card_count"),
                                    imageCount = result.getInt("image_count"),
                                    lastError = result.getString("last_error")
                                )
                            )
                        }
                    }
                }
            }
        }

    private fun normalizeNumber(value: String?): String? =
        value
            ?.substringBefore('/')
            ?.uppercase()
            ?.replace(Regex("[^A-Z0-9]"), "")
            ?.let { cleaned ->
                if (cleaned.all(Char::isDigit)) {
                    cleaned.trimStart('0').ifBlank { "0" }
                } else {
                    cleaned.replace(
                        Regex("^([A-Z]+)0+([0-9])"),
                        "${'    private fun safe(value: String): String =
        value.replace(Regex("[^A-Za-z0-9._-]"), "_")
}
}1${'    private fun safe(value: String): String =
        value.replace(Regex("[^A-Za-z0-9._-]"), "_")
}
}2"
                    )
                }
            }

    private fun resolveSetId(
        language: String,
        setCode: String?
    ): String? {
        val normalized =
            setCode
                ?.trim()
                ?.uppercase()
                ?.replace(Regex("[^A-Z0-9-]"), "")
                ?.takeIf(String::isNotBlank)
                ?: return null

        return dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT set_id
                FROM catalog_set_code_aliases
                WHERE language_code = ? AND printed_code = ?
                UNION ALL
                SELECT set_id
                FROM catalog_sets_mirror
                WHERE language_code = ? AND UPPER(set_id) = ?
                LIMIT 1
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, language)
                statement.setString(2, normalized)
                statement.setString(3, language)
                statement.setString(4, normalized)
                statement.executeQuery().use { result ->
                    if (result.next()) result.getString("set_id") else null
                }
            }
        }
    }

    private fun safe(value: String): String =
        value.replace(Regex("[^A-Za-z0-9._-]"), "_")
}
