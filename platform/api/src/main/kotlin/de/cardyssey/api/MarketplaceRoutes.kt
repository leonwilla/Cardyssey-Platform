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
data class MarketplaceListingResponse(
    val id: String,
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
    val priceEur: Double?,
    val negotiable: Boolean
)

fun Route.marketplaceRoutes(
    repository: SellingRepository
) {
    authenticate("auth-jwt") {
        route("/api/v1/marketplace") {

            get {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    repository
                        .marketplace(userId)
                        .map {
                            MarketplaceListingResponse(
                                id =
                                    it.id.toString(),

                                sellerFriendCode =
                                    it.sellerFriendCode,

                                sellerDisplayName =
                                    it.sellerDisplayName,

                                cardId =
                                    it.cardId,

                                languageCode =
                                    it.languageCode,

                                name =
                                    it.name,

                                setName =
                                    it.setName,

                                localId =
                                    it.localId,

                                imageBase =
                                    it.imageBase,

                                variant =
                                    it.variant,

                                condition =
                                    it.condition,

                                quantity =
                                    it.quantity,

                                priceEur =
                                    it.priceEur,

                                negotiable =
                                    it.negotiable
                            )
                        }
                )
            }
        }
    }
}
