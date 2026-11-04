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
                        ?: "TCG"

                if (market != "TCG" && market != "EBAY") {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_market")
                    )
                    return@get
                }

                val quote =
                    if (market == "EBAY") {
                        ebayPricing.quote(
                            cardId = cardId,
                            language = language,
                            variantId = requestedVariantId,
                            legacyVariant = requestedLegacyVariant,
                            condition = condition
                        )
                    } else {
                        pricing.quote(
                            cardId = cardId,
                            language = language,
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
                val reference = if (market == "TCG" && quote.eur == null && requestedVariantId != null) {
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
