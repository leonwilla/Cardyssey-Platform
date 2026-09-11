package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.route

fun Route.pricingRoutes(
    catalog: CardCatalogService,
    pricing: CardPricingService,
    ebayPricing: CachedEbayPricingService
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

                call.respond(quote)
            }
        }
    }
}
