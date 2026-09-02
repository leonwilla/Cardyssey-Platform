package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.*
import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
data class SaleListingResponse(
    val id: String,
    val collectionItemId: String,
    val cardId: String,
    val name: String,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variant: String,
    val condition: String,
    val ownedQuantity: Int,
    val quantity: Int,
    val priceEur: Double?,
    val negotiable: Boolean,
    val status: String
)

@Serializable
data class CreateSaleListingRequest(
    val collectionItemId: String,
    val quantity: Int = 1,
    val priceEur: Double? = null,
    val negotiable: Boolean = true
)

@Serializable
data class UpdateSaleListingRequest(
    val collectionItemId: String,
    val quantity: Int,
    val priceEur: Double? = null,
    val negotiable: Boolean,
    val status: String
)

private fun SaleListing.response() =
    SaleListingResponse(
        id.toString(),
        collectionItemId.toString(),
        cardId,
        name,
        setName,
        localId,
        imageBase,
        variant,
        condition,
        ownedQuantity,
        quantity,
        priceEur,
        negotiable,
        status
    )

fun Route.sellingRoutes(
    repository: SellingRepository
) {
    authenticate("auth-jwt") {

        route("/api/v1/selling") {

            get {
                val userId = call.authenticatedUserId()
                    ?: return@get call.respond(HttpStatusCode.Unauthorized)

                call.respond(
                    repository.list(userId).map { it.response() }
                )
            }

            post {
                val userId = call.authenticatedUserId()
                    ?: return@post call.respond(HttpStatusCode.Unauthorized)

                val request = call.receive<CreateSaleListingRequest>()

                val collectionId =
                    runCatching {
                        UUID.fromString(request.collectionItemId)
                    }.getOrNull()
                        ?: return@post call.respond(HttpStatusCode.BadRequest)

                if (
                    request.quantity < 1 ||
                    request.priceEur?.let { it < 0 } == true
                ) {
                    return@post call.respond(HttpStatusCode.BadRequest)
                }

                if (
                    !repository.create(
                        userId,
                        collectionId,
                        request.quantity,
                        request.priceEur,
                        request.negotiable
                    )
                ) {
                    return@post call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_sale_listing")
                    )
                }

                call.respond(HttpStatusCode.Created)
            }

            put("/{id}") {
                val userId = call.authenticatedUserId()
                    ?: return@put call.respond(HttpStatusCode.Unauthorized)

                val listingId =
                    call.parameters["id"]
                        ?.let {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }
                        ?: return@put call.respond(HttpStatusCode.BadRequest)

                val request = call.receive<UpdateSaleListingRequest>()

                val collectionId =
                    runCatching {
                        UUID.fromString(request.collectionItemId)
                    }.getOrNull()
                        ?: return@put call.respond(HttpStatusCode.BadRequest)

                if (
                    request.status !in
                    setOf("ACTIVE", "PAUSED", "SOLD") ||
                    request.quantity < 1 ||
                    request.priceEur?.let { it < 0 } == true
                ) {
                    return@put call.respond(HttpStatusCode.BadRequest)
                }

                if (
                    !repository.update(
                        userId,
                        listingId,
                        collectionId,
                        request.quantity,
                        request.priceEur,
                        request.negotiable,
                        request.status
                    )
                ) {
                    return@put call.respond(HttpStatusCode.BadRequest)
                }

                call.respond(HttpStatusCode.NoContent)
            }

            delete("/{id}") {
                val userId = call.authenticatedUserId()
                    ?: return@delete call.respond(HttpStatusCode.Unauthorized)

                val id =
                    call.parameters["id"]
                        ?.let {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }
                        ?: return@delete call.respond(HttpStatusCode.BadRequest)

                if (!repository.delete(userId, id)) {
                    return@delete call.respond(HttpStatusCode.NotFound)
                }

                call.respond(HttpStatusCode.NoContent)
            }
        }
    }
}
