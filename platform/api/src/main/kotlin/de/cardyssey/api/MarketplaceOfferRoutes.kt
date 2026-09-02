package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.route
import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
data class CreateMarketplaceOfferRequest(
    val listingId: String,
    val quantity: Int = 1,
    val priceEur: Double,
    val message: String? = null
)

@Serializable
data class MarketplaceOfferResponse(
    val id: String,
    val listingId: String,

    val buyerFriendCode: String,
    val buyerDisplayName: String?,

    val sellerFriendCode: String,
    val sellerDisplayName: String?,

    val cardId: String,
    val languageCode: String,
    val name: String,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variant: String,
    val condition: String,

    val quantity: Int,
    val offerPriceEur: Double,
    val listingPriceEur: Double?,
    val message: String?,
    val status: String,

    val createdAt: String,
    val updatedAt: String
)

fun Route.marketplaceOfferRoutes(
    repository: MarketplaceOfferRepository
) {
    authenticate("auth-jwt") {

        route("/api/v1/offers") {

            get("/incoming") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    repository
                        .incoming(userId)
                        .map(::offerResponse)
                )
            }

            get("/outgoing") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    repository
                        .outgoing(userId)
                        .map(::offerResponse)
                )
            }

            post {
                val userId =
                    call.authenticatedUserId()
                        ?: return@post call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val request =
                    call.receive<
                        CreateMarketplaceOfferRequest
                    >()

                val listingId =
                    runCatching {
                        UUID.fromString(
                            request.listingId
                        )
                    }.getOrNull()
                        ?: return@post call.respond(
                            HttpStatusCode.BadRequest,
                            mapOf(
                                "error" to
                                    "invalid_listing_id"
                            )
                        )

                if (
                    request.quantity < 1 ||
                    request.priceEur <= 0.0 ||
                    !request.priceEur.isFinite() ||
                    (
                        request.message
                            ?.length
                            ?: 0
                    ) > 1000
                ) {
                    return@post call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf(
                            "error" to
                                "invalid_offer"
                        )
                    )
                }

                val result =
                    repository.create(
                        buyerUserId =
                            userId,

                        listingId =
                            listingId,

                        quantity =
                            request.quantity,

                        priceEur =
                            request.priceEur,

                        message =
                            request.message
                                ?.trim()
                                ?.takeIf {
                                    it.isNotEmpty()
                                }
                    )

                val offer =
                    result.offer

                if (offer == null) {
                    val status =
                        when (
                            result.error
                        ) {
                            "pending_offer_exists" ->
                                HttpStatusCode.Conflict

                            "listing_not_found" ->
                                HttpStatusCode.NotFound

                            else ->
                                HttpStatusCode.BadRequest
                        }

                    return@post call.respond(
                        status,
                        mapOf(
                            "error" to
                                (
                                    result.error
                                        ?: "offer_failed"
                                )
                        )
                    )
                }

                call.respond(
                    HttpStatusCode.Created,
                    offerResponse(offer)
                )
            }

            post("/{id}/accept") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@post call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val id =
                    call.offerId()
                        ?: return@post call.respond(
                            HttpStatusCode.BadRequest,
                            mapOf(
                                "error" to
                                    "invalid_offer_id"
                            )
                        )

                val offer =
                    repository.accept(
                        userId,
                        id
                    )
                        ?: return@post call.respond(
                            HttpStatusCode.NotFound,
                            mapOf(
                                "error" to
                                    "pending_offer_not_found"
                            )
                        )

                call.respond(
                    offerResponse(offer)
                )
            }

            post("/{id}/reject") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@post call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val id =
                    call.offerId()
                        ?: return@post call.respond(
                            HttpStatusCode.BadRequest,
                            mapOf(
                                "error" to
                                    "invalid_offer_id"
                            )
                        )

                val offer =
                    repository.reject(
                        userId,
                        id
                    )
                        ?: return@post call.respond(
                            HttpStatusCode.NotFound,
                            mapOf(
                                "error" to
                                    "pending_offer_not_found"
                            )
                        )

                call.respond(
                    offerResponse(offer)
                )
            }

            delete("/{id}") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@delete call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val id =
                    call.offerId()
                        ?: return@delete call.respond(
                            HttpStatusCode.BadRequest,
                            mapOf(
                                "error" to
                                    "invalid_offer_id"
                            )
                        )

                if (
                    !repository.withdraw(
                        userId,
                        id
                    )
                ) {
                    return@delete call.respond(
                        HttpStatusCode.NotFound,
                        mapOf(
                            "error" to
                                "pending_offer_not_found"
                        )
                    )
                }

                call.respond(
                    HttpStatusCode.NoContent
                )
            }
        }
    }
}

private fun io.ktor.server.application.ApplicationCall.offerId():
    UUID? =
    parameters["id"]
        ?.let {
            runCatching {
                UUID.fromString(it)
            }.getOrNull()
        }

private fun offerResponse(
    item: MarketplaceOffer
) =
    MarketplaceOfferResponse(
        id =
            item.id.toString(),

        listingId =
            item.listingId.toString(),

        buyerFriendCode =
            item.buyerFriendCode,

        buyerDisplayName =
            item.buyerDisplayName,

        sellerFriendCode =
            item.sellerFriendCode,

        sellerDisplayName =
            item.sellerDisplayName,

        cardId =
            item.cardId,

        languageCode =
            item.languageCode,

        name =
            item.name,

        setName =
            item.setName,

        localId =
            item.localId,

        imageBase =
            item.imageBase,

        variant =
            item.variant,

        condition =
            item.condition,

        quantity =
            item.quantity,

        offerPriceEur =
            item.offerPriceEur,

        listingPriceEur =
            item.listingPriceEur,

        message =
            item.message,

        status =
            item.status,

        createdAt =
            item.createdAt,

        updatedAt =
            item.updatedAt
    )
