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
data class WishlistResponse(
    val id: String,
    val cardId: String,
    val languageCode: String,
    val name: String,
    val setId: String?,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variantId: String?,
    val variantType: String?,
    val variantSubtype: String?,
    val foil: String?,
    val size: String?,
    val stamps: List<String>,
    val priority: String,
    val targetPriceEur: Double?
)

@Serializable
data class CreateWishlistRequest(
    val cardId: String,
    val languageCode: String = "de",
    val name: String,
    val setId: String? = null,
    val setName: String? = null,
    val localId: String? = null,
    val imageBase: String? = null,
    val variantId: String? = null,
    val variantType: String? = null,
    val variantSubtype: String? = null,
    val foil: String? = null,
    val size: String? = null,
    val stamps: List<String> = emptyList(),
    val priority: String = "MEDIUM",
    val targetPriceEur: Double? = null
)

@Serializable
data class UpdateWishlistPreferencesRequest(
    val priority: String = "MEDIUM",
    val targetPriceEur: Double? = null
)

private fun WishlistItem.response() =
    WishlistResponse(
        id.toString(),
        cardId,
        languageCode,
        name,
        setId,
        setName,
        localId,
        imageBase,
        variantId,
        variantType,
        variantSubtype,
        foil,
        size,
        stamps,
        priority,
        targetPriceEur
    )

fun Route.wishlistRoutes(
    repository: WishlistRepository
) {
    authenticate("auth-jwt") {
        route("/api/v1/wishlist") {

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

                val request = call.receive<CreateWishlistRequest>()

                if (
                    request.cardId.isBlank() ||
                    request.name.isBlank()
                ) {
                    return@post call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_wishlist_item")
                    )
                }

                val item = WishlistItem(
                    id = UUID.randomUUID(),
                    cardId = request.cardId,
                    languageCode = request.languageCode,
                    name = request.name,
                    setId = request.setId,
                    setName = request.setName,
                    localId = request.localId,
                    imageBase = request.imageBase,
                    variantId = request.variantId,
                    variantType = request.variantType,
                    variantSubtype = request.variantSubtype,
                    foil = request.foil,
                    size = request.size,
                    stamps = request.stamps,
                    priority =
                        request.priority
                            .trim()
                            .uppercase()
                            .takeIf {
                                it in
                                    setOf(
                                        "LOW",
                                        "MEDIUM",
                                        "HIGH"
                                    )
                            }
                            ?: return@post call.respond(
                                HttpStatusCode.BadRequest,
                                mapOf(
                                    "error" to
                                        "invalid_priority"
                                )
                            ),
                    targetPriceEur =
                        request.targetPriceEur
                            ?.takeIf {
                                it.isFinite() &&
                                    it >= 0.0
                            }
                )

                if (!repository.create(userId, item)) {
                    return@post call.respond(
                        HttpStatusCode.Conflict,
                        mapOf("error" to "already_on_wishlist")
                    )
                }

                call.respond(
                    HttpStatusCode.Created,
                    item.response()
                )
            }

            patch("/{id}") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@patch call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val id =
                    call.parameters["id"]
                        ?.let {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }
                        ?: return@patch call.respond(
                            HttpStatusCode.BadRequest
                        )

                val request =
                    call.receive<UpdateWishlistPreferencesRequest>()

                val item =
                    repository.updatePreferences(
                        userId =
                            userId,
                        id =
                            id,
                        priority =
                            request.priority,
                        targetPriceEur =
                            request.targetPriceEur
                    )
                        ?: return@patch call.respond(
                            HttpStatusCode.BadRequest,
                            mapOf(
                                "error" to
                                    "invalid_wishlist_preferences"
                            )
                        )

                call.respond(
                    item.response()
                )
            }

            delete("/{id}") {
                val userId = call.authenticatedUserId()
                    ?: return@delete call.respond(HttpStatusCode.Unauthorized)

                val id = call.parameters["id"]
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
