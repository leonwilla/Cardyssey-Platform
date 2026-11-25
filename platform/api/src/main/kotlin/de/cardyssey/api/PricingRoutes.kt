package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.route

fun Route.pricingRoutes(
    catalog: CardCatalogService,
    pricing: CachedTcgPricingService,
    ebayPricing: CachedEbayPricingService,
    referenceCache: TcgPriceCacheRepository,
    dataSource: HikariDataSource
) {
    val sourcePolicy = GlobalPriceSourceRepository(dataSource)
    authenticate("auth-jwt") {
        route("/api/v1/pricing") {
            get("/history/{id}") {
                val id = call.parameters["id"]?.trim().orEmpty()
                val language = call.request.queryParameters["language"]?.trim()?.lowercase() ?: "de"
                val variantId = call.request.queryParameters["variantId"]?.trim().orEmpty()
                if (!id.matches(Regex("[a-zA-Z0-9_-]{2,90}")) ||
                    !catalog.validLanguage(language) || !variantId.matches(Regex("[a-zA-Z0-9_:-]{2,100}"))) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_history_query"))
                    return@get
                }
                val history = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                    dataSource.connection.use { connection ->
                        connection.prepareStatement("""
                            SELECT sold_on, sold_eur, condition_label, condition_assumed, variant_assumed
                            FROM ebay_sold_history
                            WHERE card_id=? AND language_code=? AND variant_id=?
                            ORDER BY sold_on ASC, ebay_item_id ASC LIMIT 5000
                        """.trimIndent()).use { query ->
                            query.setString(1,id)
                            query.setString(2,language)
                            query.setString(3,variantId)
                            query.executeQuery().use { results ->
                                buildList {
                                    while(results.next()) add(EbayHistoryPoint(
                                        soldOn=results.getDate("sold_on").toString(),
                                        eur=results.getDouble("sold_eur"),
                                        condition=results.getString("condition_label"),
                                        conditionAssumed=results.getBoolean("condition_assumed"),
                                        variantAssumed=results.getBoolean("variant_assumed")
                                    ))
                                }
                            }
                        }
                    }
                }
                call.respond(EbayHistoryResponse(id,language,variantId,history))
            }
            // Shown TCG price over time (DE/EN: Cardmarket only), one value per
            // day (last change of that day), plus the value before the range
            // start so the line starts at the left edge.
            get("/tcg-history/{id}") {
                val id = call.parameters["id"]?.trim().orEmpty()
                val language = call.request.queryParameters["language"]?.trim()?.lowercase() ?: "de"
                val variantId = call.request.queryParameters["variantId"]?.trim().orEmpty()
                val days = tcgHistoryDays(call.request.queryParameters["days"])
                if (!id.matches(Regex("[a-zA-Z0-9_-]{2,90}")) || days == null ||
                    !catalog.validLanguage(language) || !variantId.matches(Regex("[a-zA-Z0-9_:-]{2,100}"))) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_history_query"))
                    return@get
                }
                val result = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                    dataSource.connection.use { connection ->
                        connection.prepareStatement("""
                            WITH rows AS (
                                SELECT (captured_at AT TIME ZONE 'Europe/Berlin')::date AS day, captured_at, base_eur
                                FROM tcg_price_history
                                WHERE card_id=? AND language_code=? AND variant_id=? AND base_eur > 0
                                  AND upper(COALESCE(source,'')) NOT LIKE 'TCGDEX%'
                                  AND (language_code NOT IN ('de','en')
                                       OR upper(COALESCE(source,'')) LIKE 'CARDMARKET%'
                                       OR upper(COALESCE(source,'')) LIKE 'MANUAL%'
                                       OR upper(COALESCE(source,'')) LIKE 'ADMIN%')
                            ), daily AS (
                                SELECT DISTINCT ON (day) day, base_eur FROM rows ORDER BY day, captured_at DESC
                            )
                            SELECT day, base_eur, (SELECT MIN(day) FROM daily) AS first_day FROM daily
                            WHERE ? = 0 OR day >= (NOW() AT TIME ZONE 'Europe/Berlin')::date - ?
                               OR day = (SELECT MAX(day) FROM daily
                                         WHERE day < (NOW() AT TIME ZONE 'Europe/Berlin')::date - ?)
                            ORDER BY day
                        """.trimIndent()).use { query ->
                            query.setString(1, id)
                            query.setString(2, language)
                            query.setString(3, variantId)
                            query.setInt(4, days)
                            query.setInt(5, days)
                            query.setInt(6, days)
                            query.executeQuery().use { results ->
                                var firstDay: String? = null
                                val points = buildList {
                                    while (results.next()) {
                                        firstDay = results.getDate("first_day")?.toString()
                                        add(TcgHistoryPoint(results.getDate("day").toString(), results.getDouble("base_eur")))
                                    }
                                }
                                points to firstDay
                            }
                        }
                    }
                }
                call.respond(TcgHistoryResponse(id, language, variantId, days, result.second, result.first))
            }
            get("/cards/{id}") {
                val cardId =
                    call.parameters["id"]
                        ?.trim()
                        ?.takeIf(String::isNotBlank)

                if (cardId == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_card_id")
                    )
                    return@get
                }

                val language =
                    call.request
                        .queryParameters["language"]
                        ?.trim()
                        ?.lowercase()
                        ?: "de"

                if (!catalog.validLanguage(language)) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_language")
                    )
                    return@get
                }

                val rawCondition =
                    call.request
                        .queryParameters["condition"]

                val condition =
                    PricingCondition.parse(
                        rawCondition
                    )

                if (condition == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_condition")
                    )
                    return@get
                }

                val requestedVariantId =
                    call.request
                        .queryParameters["variantId"]
                        ?.trim()
                        ?.takeIf(String::isNotBlank)

                val requestedLegacyVariant =
                    call.request
                        .queryParameters["variant"]
                        ?.trim()
                        ?.uppercase()
                        ?.takeIf(String::isNotBlank)

                val market =
                    call.request
                        .queryParameters["market"]
                        ?.trim()
                        ?.uppercase()
                        ?: "AUTO"

                if (market !in setOf("AUTO", "TCG", "EBAY")) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_market")
                    )
                    return@get
                }

                // The same print-specific policy governs Android, web and all
                // other callers; never silently borrow a different language's
                // market price. An explicit eBay request for bulk is routed to
                // its appropriate local TCG/Cardmarket-family reference.
                val details = catalog.details(cardId, language)
                val selectedVariant = details?.variants?.let { variants ->
                    if (requestedVariantId != null)
                        variants.firstOrNull { it.id == requestedVariantId }
                    else if (requestedLegacyVariant != null)
                        variants.filter { it.legacyVariant == requestedLegacyVariant }.singleOrNull()
                    else variants.singleOrNull()
                }
                val policy = if (details?.languageCode == language && selectedVariant != null &&
                    language in GlobalPriceSourceRules.supportedLanguages)
                    sourcePolicy.read(cardId, language, selectedVariant.id)
                else null
                val bulk = policy?.priceClass == "BULK" ||
                    (policy == null && GlobalPriceSourceRules.priceClass(details?.rarity) == "BULK")
                val useEbay = when {
                    bulk -> false
                    market == "EBAY" -> true
                    market == "TCG" -> false
                    policy?.preferredMarket != "EBAY" -> false
                    selectedVariant == null -> false
                    else -> sourcePolicy.hasVerifiedEbaySale(cardId, language, selectedVariant.id)
                }
                val quote = when {
                    useEbay -> {
                        val ebay = ebayPricing.quote(
                            cardId = cardId, language = language,
                            variantId = requestedVariantId,
                            legacyVariant = requestedLegacyVariant,
                            condition = condition
                        )
                        if (market == "AUTO" && ebay?.eur == null) {
                            if (policy != null && details != null && selectedVariant != null)
                                sourcePolicy.tcgResponse(details,selectedVariant,condition,policy)
                            else pricing.quote(cardId,language,requestedVariantId,requestedLegacyVariant,condition)
                        } else ebay?.copy(
                            policyClass = policy?.priceClass,
                            policyStatus = policy?.status,
                            policyProviderFamily = policy?.providerFamily,
                            preferredMarket = policy?.preferredMarket
                        )
                    }
                    policy != null && details != null && selectedVariant != null ->
                        sourcePolicy.tcgResponse(details,selectedVariant,condition,policy)
                    else -> pricing.quote(
                        cardId = cardId, language = language,
                        variantId = requestedVariantId,
                        legacyVariant = requestedLegacyVariant,
                        condition = condition
                    )
                }

                if (quote == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf("error" to "card_not_found")
                    )
                    return@get
                }

                // Never replace an exact quote with a reference. An unavailable
                // quote may carry a separately labeled card-level approximation.
                val reference = if (quote.market == "TCG" && quote.eur == null && requestedVariantId != null) {
                    referenceCache.reference(cardId,language,requestedVariantId)
                } else null
                call.respond(if (reference != null) quote.copy(
                    referenceEur = reference.first,
                    referenceNote = "Englischer Karten-Richtwert; Druckvariante und Zustand ungeprüft. Kein bestätigter Marktpreis.",
                    referenceUpdatedAtMs = reference.second
                ) else quote)
            }
        }
    }
}

@Serializable
data class EbayHistoryPoint(
    val soldOn: String,
    val eur: Double,
    val condition: String,
    val conditionAssumed: Boolean,
    val variantAssumed: Boolean
)

@Serializable
data class EbayHistoryResponse(
    val cardId: String,
    val languageCode: String,
    val variantId: String,
    val points: List<EbayHistoryPoint>
)

/** Allowed chart ranges in days; 0 = everything recorded. */
internal val TCG_HISTORY_RANGES = setOf(0, 7, 30, 90, 365)

internal fun tcgHistoryDays(raw: String?): Int? {
    val value = raw?.trim().orEmpty()
    if (value.isEmpty()) return 30
    return value.toIntOrNull()?.takeIf { it in TCG_HISTORY_RANGES }
}

@Serializable
data class TcgHistoryPoint(
    val date: String,
    val eur: Double
)

@Serializable
data class TcgHistoryResponse(
    val cardId: String,
    val languageCode: String,
    val variantId: String,
    val days: Int,
    val recordedSince: String?,
    val points: List<TcgHistoryPoint>
)
