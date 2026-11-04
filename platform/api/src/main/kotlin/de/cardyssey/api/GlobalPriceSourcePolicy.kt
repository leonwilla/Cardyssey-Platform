package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.Locale

/** Central across all supported catalog sets and languages; exact print only. */
internal object GlobalPriceSourceRules {
    val supportedLanguages = setOf("de", "en", "ja", "ko", "zh-cn", "zh-tw")
    private val bulkRarities = setOf(
        "häufig", "ungewöhnlich", "common", "uncommon", "c", "u",
        "rare_c", "rare_u", "rare_c_c", "rare_u_c",
        "one diamond", "two diamond", "une diamant", "deux diamant"
    )

    fun priceClass(rarity: String?): String = when {
        rarity.isNullOrBlank() || rarity.trim().lowercase(Locale.ROOT) in setOf("none","keine","unknown","n/a","unbekannt") -> "RARITY_UNVERIFIED"
        rarity.trim().lowercase(Locale.ROOT) in bulkRarities -> "BULK"
        else -> "SPECIAL"
    }

    fun preferredMarket(language: String, rarity: String?): String = when {
        priceClass(rarity) == "BULK" -> "TCG"
        priceClass(rarity) == "SPECIAL" && language in setOf("de", "en") -> "EBAY"
        else -> "LOCAL_MARKET"
    }
}

internal data class GlobalPrintPricePolicy(
    val priceClass: String,
    val preferredMarket: String,
    val providerFamily: String,
    val source: String?,
    val baseEur: Double?,
    val status: String
)

internal class GlobalPriceSourceRepository(private val dataSource: HikariDataSource) {
    suspend fun read(cardId: String, language: String, variantId: String): GlobalPrintPricePolicy? =
        withContext(Dispatchers.IO) {
            dataSource.connection.use { connection ->
                connection.prepareStatement("""
                    SELECT price_class, preferred_market, preferred_provider_family,
                           selected_price_source,selected_price_eur,price_status
                    FROM global_price_source_policy
                    WHERE card_id=? AND language_code=? AND variant_id=?
                """.trimIndent()).use { statement ->
                    statement.setString(1, cardId)
                    statement.setString(2, language)
                    statement.setString(3, variantId)
                    statement.executeQuery().use { row ->
                        if (!row.next()) null else GlobalPrintPricePolicy(
                            priceClass = row.getString("price_class"),
                            preferredMarket = row.getString("preferred_market"),
                            providerFamily = row.getString("preferred_provider_family"),
                            source = row.getString("selected_price_source"),
                            baseEur = row.getBigDecimal("selected_price_eur")?.toDouble(),
                            status = row.getString("price_status")
                        )
                    }
                }
            }
        }

    /** A confirmed eBay transaction allows rare DE/EN AUTO to prefer sold evidence. */
    suspend fun hasVerifiedEbaySale(cardId: String, language: String, variantId: String): Boolean =
        withContext(Dispatchers.IO) {
            dataSource.connection.use { connection ->
                connection.prepareStatement("""
                    SELECT EXISTS(SELECT 1 FROM ebay_price_cache
                        WHERE card_id=? AND language_code=? AND variant_id=?
                          AND sample_count>0 AND base_eur>0)
                """.trimIndent()).use { statement ->
                    statement.setString(1, cardId)
                    statement.setString(2, language)
                    statement.setString(3, variantId)
                    statement.executeQuery().use { rs -> rs.next() && rs.getBoolean(1) }
                }
            }
        }

    fun tcgResponse(details: CatalogCardDetails, variant: CatalogVariant,
                    condition: PricingCondition, policy: GlobalPrintPricePolicy): CardPriceQuoteResponse {
        val base = policy.baseEur?.takeIf { it.isFinite() && it > 0.0 }
        return CardPriceQuoteResponse(
            cardId = details.id, languageCode = details.languageCode,
            variantId = variant.id, variantType = variant.type,
            condition = condition.name, market = "TCG", source = policy.source,
            baseEur = base, conditionFactor = condition.factor,
            eur = base?.let { kotlin.math.round(it * condition.factor * 100.0) / 100.0 },
            exactLanguageMatch = true, exactVariantMatch = true,
            policyClass = policy.priceClass,
            policyStatus = policy.status,
            policyProviderFamily = policy.providerFamily,
            preferredMarket = policy.preferredMarket
        )
    }
}
