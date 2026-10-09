package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable
import java.sql.ResultSet

@Serializable
data class AdminPriceCoverageGroup(
    val setId: String, val setName: String, val languageCode: String,
    val affectedCards: Long, val missingPrices: Long, val deferredPrices: Long,
    val providerErrors: Long, val missingCache: Long, val missingVariantCards: Long
)

@Serializable
data class AdminPriceCoverageResponse(val groups: List<AdminPriceCoverageGroup>)

@Serializable
data class AdminPriceCoverageCard(
    val cardId: String, val cardName: String, val cardNumber: String,
    val variantId: String?, val variant: String?, val reason: String,
    val failureDetail: String?, val nextAttemptAt: String?
)

@Serializable
data class AdminPriceCoverageCardsResponse(
    val total: Long, val offset: Int, val items: List<AdminPriceCoverageCard>
)

/** Full physical catalogue coverage, including entries omitted by the variant-only monitor. */
class AdminPriceCoverageRepository(private val dataSource: HikariDataSource) {
    companion object {
        val languages = setOf("de", "en", "ja", "ko", "zh-cn", "zh-tw")
        const val PAGE_SIZE = 100
        // No history lookup: an old but valid cached price is not a missing price.
        val coverageCte = """
WITH physical AS (
 SELECT c.*, COALESCE(NULLIF(sd.name,''),NULLIF(se.name,''),NULLIF(s.name,''),c.set_id) AS set_name
 FROM catalog_cards_mirror c
 LEFT JOIN catalog_sets_mirror s ON s.language_code=c.language_code AND s.set_id=c.set_id
 LEFT JOIN catalog_sets_mirror sd ON sd.language_code='de' AND sd.set_id=c.set_id
 LEFT JOIN catalog_sets_mirror se ON se.language_code='en' AND se.set_id=c.set_id
 WHERE c.language_code IN ('de','en','ja','ko','zh-cn','zh-tw')
 AND c.set_id !~ '^(A[0-9]|B[0-9]|P-A)'
), missing AS (
 SELECT c.card_id,c.language_code,c.set_id,c.set_name,c.name AS card_name,c.local_id,
 v.value->>'id' AS variant_id,
 COALESCE(NULLIF(v.value->>'name',''),NULLIF(v.value->>'label',''),NULLIF(v.value->>'legacyVariant',''),v.value->>'id') AS variant_label,
 CASE WHEN p.card_id IS NULL THEN 'MISSING_CACHE'
      WHEN p.resolution_status='NO_PUBLIC_PRICE' THEN 'NO_PUBLIC_PRICE'
      WHEN p.resolution_status='PROVIDER_ERROR' THEN 'PROVIDER_ERROR'
      ELSE 'NO_PRICE' END AS reason,
 p.failure_detail,p.next_attempt_at::text AS next_attempt_at
 FROM physical c CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
 LEFT JOIN tcg_price_cache p ON p.card_id=c.card_id AND p.language_code=c.language_code AND p.variant_id=v.value->>'id'
 WHERE COALESCE(v.value->>'id','')<>''
 AND NOT (COALESCE(p.resolution_status,'')='PRICE_FOUND'
          AND COALESCE(p.base_eur,0)>0 AND p.base_eur::text NOT IN ('NaN','Infinity','-Infinity'))
 UNION ALL
 SELECT c.card_id,c.language_code,c.set_id,c.set_name,c.name,c.local_id,
 NULL::text,NULL::text,'MISSING_VARIANTS',
 'Keine verwertbaren Variantendaten im Katalog. Eintrag kann ein Duplikat sein.',NULL::text
 FROM physical c
 WHERE NOT EXISTS (SELECT 1 FROM jsonb_array_elements(c.variants) v(value) WHERE COALESCE(v.value->>'id','')<>'')
)
"""
    }

    fun overview(language: String?): AdminPriceCoverageResponse = dataSource.connection.use { connection ->
        val sql = coverageCte + """
SELECT set_id,set_name,language_code,COUNT(DISTINCT card_id) AS affected_cards,
 COUNT(*) FILTER(WHERE reason<>'MISSING_VARIANTS') AS missing_prices,
 COUNT(*) FILTER(WHERE reason='NO_PUBLIC_PRICE') AS deferred_prices,
 COUNT(*) FILTER(WHERE reason='PROVIDER_ERROR') AS provider_errors,
 COUNT(*) FILTER(WHERE reason='MISSING_CACHE') AS missing_cache,
 COUNT(*) FILTER(WHERE reason='MISSING_VARIANTS') AS missing_variant_cards
FROM missing ${if (language != null) "WHERE language_code=?" else ""}
GROUP BY set_id,set_name,language_code
ORDER BY COUNT(*) FILTER(WHERE reason<>'MISSING_VARIANTS') DESC,affected_cards DESC,set_name,set_id,language_code
"""
        connection.prepareStatement(sql).use { statement ->
            statement.queryTimeout = 15
            if (language != null) statement.setString(1, language)
            statement.executeQuery().use { rows ->
                AdminPriceCoverageResponse(buildList { while (rows.next()) add(group(rows)) })
            }
        }
    }

    fun cards(language: String, setId: String, offset: Int): AdminPriceCoverageCardsResponse =
        dataSource.connection.use { connection ->
            // One statement keeps the count and the page consistent, including empty pages.
            val sql = coverageCte + """
, selected AS (SELECT * FROM missing WHERE language_code=? AND set_id=?),
page AS (SELECT * FROM selected ORDER BY local_id,card_name,card_id,variant_id NULLS FIRST LIMIT $PAGE_SIZE OFFSET ?)
SELECT totals.total,page.* FROM (SELECT COUNT(*) AS total FROM selected) totals LEFT JOIN page ON TRUE
ORDER BY page.local_id,page.card_name,page.card_id,page.variant_id NULLS FIRST
"""
            connection.prepareStatement(sql).use { statement ->
                statement.queryTimeout = 15
                statement.setString(1, language)
                statement.setString(2, setId)
                statement.setInt(3, offset)
                statement.executeQuery().use { rows ->
                    var total = 0L
                    val items = buildList {
                        while (rows.next()) {
                            total = rows.getLong("total")
                            if (rows.getString("card_id") != null) add(AdminPriceCoverageCard(
                                rows.getString("card_id"), rows.getString("card_name"), rows.getString("local_id"),
                                rows.getString("variant_id"), rows.getString("variant_label"), rows.getString("reason"),
                                rows.getString("failure_detail"), rows.getString("next_attempt_at")
                            ))
                        }
                    }
                    AdminPriceCoverageCardsResponse(total, offset, items)
                }
            }
        }

    private fun group(rows: ResultSet) = AdminPriceCoverageGroup(
        rows.getString("set_id"), rows.getString("set_name"), rows.getString("language_code"),
        rows.getLong("affected_cards"), rows.getLong("missing_prices"), rows.getLong("deferred_prices"),
        rows.getLong("provider_errors"), rows.getLong("missing_cache"), rows.getLong("missing_variant_cards")
    )
}
