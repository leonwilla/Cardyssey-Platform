package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.json.Json
import java.util.concurrent.ConcurrentHashMap

/** Official print records are independent of TCGdex IDs and prices. */
class SupplementalCatalogRepository(
    private val dataSource: HikariDataSource,
    private val mirror: PermanentCatalogRepository
) {
    private val json = Json { ignoreUnknownKeys = true }
    private data class Cached(val loadedAt: Long, val cards: List<CatalogCardDetails>)
    private val cache = ConcurrentHashMap<String, Cached>()

    @Synchronized
    fun cards(language: String): List<CatalogCardDetails> {
        val now = System.currentTimeMillis()
        cache[language]?.takeIf { now - it.loadedAt < 60_000L }?.let { return it.cards }
        val cards = dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT DISTINCT ON (s.canonical_card_id)
                    s.canonical_card_id, s.details, s.german_species_name,
                    COALESCE(m.image_complete, FALSE) AS image_complete,
                    CASE WHEN NULLIF(m.raw_payload->>'_cardyssey_verified_variant_source','') IS NOT NULL
                           OR (m.language_code='ko' AND m.raw_payload->>'_cardyssey_retail_variant_source' IN ('WEB_UTURI_KO','WEB_MEWTWO_KO','WEB_LAKE_KO','WEB_MANA_KO','WEB_LEVELUP_KO','WEB_SHINY_KO'))
                         THEN m.variants::text END AS recovered_variants
                FROM catalog_supplemental_cards s
                LEFT JOIN catalog_cards_mirror m ON m.language_code = s.language_code
                    AND m.card_id = s.canonical_card_id
                WHERE s.language_code = ?
                ORDER BY s.canonical_card_id, s.source_id
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, language)
                statement.executeQuery().use { rows ->
                    buildList {
                        while (rows.next()) {
                            val card = json.decodeFromString<CatalogCardDetails>(rows.getString("details"))
                            val id = rows.getString("canonical_card_id")
                            val species = rows.getString("german_species_name")
                            add(card.copy(
                                id = id,
                                variants = recoveredSupplementalVariants(card, rows.getString("recovered_variants")),
                                // Keep the original name; the German species is an aid, not a translation of the print.
                                name = if (species.isNullOrBlank()) card.name else "${card.name} ($species)",
                                imageBase = if (rows.getBoolean("image_complete")) mirror.imageBase(language, id) else null,
                                imageLanguage = language
                            ))
                        }
                    }
                }
            }
        }
        cache[language] = Cached(now, cards)
        return cards
    }
}

/** Only called for variants with import provenance; official IDs/names/images remain intact. */
internal fun recoveredSupplementalVariants(card: CatalogCardDetails, recoveredJson: String?): List<CatalogVariant> {
    if (card.variants.isNotEmpty() || recoveredJson.isNullOrBlank()) return card.variants
    val recovered = runCatching {
        Json { ignoreUnknownKeys = true }.decodeFromString<List<CatalogVariant>>(recoveredJson)
    }.getOrNull() ?: return card.variants
    if (recovered.isEmpty() || recovered.any {
        it.id.isBlank() || it.type !in setOf("normal", "holo", "reverse") ||
            it.legacyVariant !in setOf("NORMAL", "HOLO", "REVERSE")
    } || recovered.map { it.id }.distinct().size != recovered.size) return card.variants
    return recovered
}
