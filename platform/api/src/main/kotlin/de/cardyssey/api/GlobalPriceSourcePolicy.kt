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
    val status: String,
    val providerUrl: String? = null
)

internal class GlobalPriceSourceRepository(private val dataSource: HikariDataSource) {
    suspend fun read(cardId: String, language: String, variantId: String): GlobalPrintPricePolicy? =
        withContext(Dispatchers.IO) {
            dataSource.connection.use { connection ->
                connection.prepareStatement("""
                    SELECT p.price_class, p.preferred_market, p.preferred_provider_family,
                           p.selected_price_source, p.selected_price_eur, p.price_status, t.provider_url
                    FROM global_price_source_policy p
                    LEFT JOIN tcg_price_cache t
                      ON t.card_id = p.card_id AND t.language_code = p.language_code AND t.variant_id = p.variant_id
                    WHERE p.card_id=? AND p.language_code=? AND p.variant_id=?
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
                            status = row.getString("price_status"),
                            providerUrl = row.getString("provider_url")
                        )
                    }
                }
            }
        }

    /** Matching eBay offers of one variant (scripts/ebay/ebay_listing_fallback.py). */
    suspend fun ebayOffers(cardId: String, language: String, variantId: String): Pair<Int, List<EbayOfferResponse>>? =
        withContext(Dispatchers.IO) {
            dataSource.connection.use { connection ->
                connection.prepareStatement("""
                    SELECT offer_count, listings::text AS listings FROM ebay_listing_offers
                    WHERE card_id=? AND language_code=? AND variant_id=? AND match_status='OK' AND offer_count>0
                      AND checked_at > now() - interval '30 days'
                """.trimIndent()).use { statement ->
                    statement.setString(1, cardId)
                    statement.setString(2, language)
                    statement.setString(3, variantId)
                    statement.executeQuery().use { row ->
                        if (!row.next()) return@use null
                        val offers = runCatching {
                            kotlinx.serialization.json.Json.parseToJsonElement(row.getString("listings"))
                                .let { it as kotlinx.serialization.json.JsonArray }
                                .mapNotNull { element ->
                                    val o = element as? kotlinx.serialization.json.JsonObject ?: return@mapNotNull null
                                    val url = (o["url"] as? kotlinx.serialization.json.JsonPrimitive)?.content
                                    val title = (o["title"] as? kotlinx.serialization.json.JsonPrimitive)?.content
                                    val eur = (o["eur"] as? kotlinx.serialization.json.JsonPrimitive)?.content?.toDoubleOrNull()
                                    if (url == null || title == null || eur == null ||
                                        !url.startsWith("https://www.ebay.")) null
                                    else EbayOfferResponse(title = title, eur = eur, url = url)
                                }
                        }.getOrDefault(emptyList())
                        row.getInt("offer_count") to offers
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
            preferredMarket = policy.preferredMarket,
            providerUrl = policy.providerUrl
        )
    }
}
