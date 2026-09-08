package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.route
import kotlinx.serialization.Serializable

@Serializable
data class CardPriceQuoteResponse(
    val cardId: String,
    val languageCode: String,
    val variantId: String?,
    val variantType: String?,
    val condition: String,
    val market: String,
    val source: String?,
    val baseEur: Double?,
    val conditionFactor: Double,
    val eur: Double?,
    val exactLanguageMatch: Boolean,
    val exactVariantMatch: Boolean
)

private enum class PricingCondition(
    val factor: Double
) {
    MINT(1.00),
    NEAR_MINT(0.92),
    EXCELLENT(0.80),
    GOOD(0.65),
    PLAYED(0.45)
}

fun Route.pricingRoutes(
    catalog: CardCatalogService
) {
    authenticate("auth-jwt") {
        route("/api/v1/pricing") {
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

                val condition =
                    call.request
                        .queryParameters["condition"]
                        ?.trim()
                        ?.uppercase()
                        ?.let {
                            runCatching {
                                PricingCondition.valueOf(it)
                            }.getOrNull()
                        }
                        ?: PricingCondition.NEAR_MINT

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

                val details =
                    catalog.details(
                        cardId = cardId,
                        language = language
                    )

                if (details == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf("error" to "card_not_found")
                    )
                    return@get
                }

                val selected =
                    when {
                        requestedVariantId != null ->
                            details.variants
                                .firstOrNull {
                                    it.id == requestedVariantId
                                }

                        requestedLegacyVariant != null -> {
                            val candidates =
                                details.variants.filter {
                                    it.legacyVariant ==
                                        requestedLegacyVariant
                                }

                            candidates
                                .singleOrNull()
                        }

                        details.variants.size == 1 ->
                            details.variants.first()

                        else ->
                            null
                    }

                val exactVariantMatch =
                    selected != null

                val baseEur =
                    selected
                        ?.tcgDexEur
                        ?.takeIf {
                            it.isFinite() &&
                                it > 0.0
                        }

                val conditioned =
                    baseEur?.times(
                        condition.factor
                    )

                call.respond(
                    CardPriceQuoteResponse(
                        cardId = details.id,
                        languageCode = details.languageCode,
                        variantId = selected?.id,
                        variantType = selected?.type,
                        condition = condition.name,
                        market = "TCG",
                        source =
                            if (baseEur != null) {
                                "TCGDEX"
                            } else {
                                null
                            },
                        baseEur = baseEur,
                        conditionFactor = condition.factor,
                        eur = conditioned,
                        exactLanguageMatch =
                            details.languageCode == language,
                        exactVariantMatch = exactVariantMatch
                    )
                )
            }
        }
    }
}
