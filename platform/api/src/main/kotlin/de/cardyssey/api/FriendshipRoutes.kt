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
data class FriendUserResponse(
    val friendCode: String,
    val displayName: String?
)

@Serializable
data class FriendRequestResponse(
    val id: String,
    val user: FriendUserResponse,
    val createdAt: String
)

@Serializable
data class FriendRequestsResponse(
    val incoming: List<FriendRequestResponse>,
    val outgoing: List<FriendRequestResponse>
)

@Serializable
data class SendFriendRequest(
    val friendCode: String
)

fun Route.friendshipRoutes(
    repository: FriendshipRepository,
    privacyRepository: PrivacyRepository,
    showcaseRepository: ShowcaseRepository,
    collectionRepository: FriendCollectionRepository,
    setRepository: FriendSetRepository,
    wishlistRepository: WishlistRepository
) {

    authenticate("auth-jwt") {

        route("/api/v1/friends") {

            get {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    repository
                        .friends(userId)
                        .map {
                            FriendUserResponse(
                                friendCode =
                                    it.user.friendCode,
                                displayName =
                                    it.user.displayName
                            )
                        }
                )
            }

            get("/{friendCode}/profile") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val friendCode =
                    call.parameters["friendCode"]
                        ?.trim()
                        .orEmpty()

                val target =
                    repository.findUserByFriendCode(
                        friendCode
                    )

                if (target == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf("error" to "user_not_found")
                    )
                    return@get
                }

                val targetId = target.first
                val targetUser = target.second

                val isFriend =
                    repository.isFriend(
                        userId,
                        targetId
                    )

                val privacy =
                    privacyRepository.get(
                        targetId
                    )

                if (
                    !visibilityAllowed(
                        privacy.profileVisibility,
                        isFriend
                    )
                ) {
                    call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf("error" to "profile_private")
                    )
                    return@get
                }

                call.respond(
                    FriendProfileResponse(
                        friendCode =
                            targetUser.friendCode,
                        displayName =
                            targetUser.displayName,
                        avatarUrl =
                            avatarUrlFor(
                                repository.avatarPath(
                                    targetId
                                )
                            ),
                        favoritePokemon =
                            targetUser.favoritePokemon,
                        favoriteSet =
                            targetUser.favoriteSet,
                        collectingFocus =
                            targetUser.collectingFocus,
                        isFriend =
                            isFriend,
                        canSeeShowcase =
                            visibilityAllowed(
                                privacy.showcaseVisibility,
                                isFriend
                            ),
                        canSeeCollection =
                            visibilityAllowed(
                                privacy.collectionVisibility,
                                isFriend
                            ),
                        canSeeCollectionValue =
                            visibilityAllowed(
                                privacy.collectionValueVisibility,
                                isFriend
                            ),
                        canSeeQuantity =
                            visibilityAllowed(
                                privacy.quantityVisibility,
                                isFriend
                            ),
                        canSeeSets =
                            visibilityAllowed(
                                privacy.setsVisibility,
                                isFriend
                            ),
                        canSeeWishlist =
                            visibilityAllowed(
                                privacy.wishlistVisibility,
                                isFriend
                            )
                    )
                )
            }

            delete("/{friendCode}") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@delete call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val friendCode =
                    call.parameters["friendCode"]
                        ?.trim()
                        .orEmpty()

                if (
                    !repository.removeFriend(
                        userId,
                        friendCode
                    )
                ) {
                    call.respond(
                        HttpStatusCode.NotFound
                    )
                    return@delete
                }

                call.respond(
                    HttpStatusCode.NoContent
                )
            }

            get("/{friendCode}/showcase/profile") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val friendCode =
                    call.parameters["friendCode"]
                        ?.trim()
                        .orEmpty()

                val target =
                    repository.findUserByFriendCode(
                        friendCode
                    )
                        ?: return@get call.respond(
                            HttpStatusCode.NotFound,
                            mapOf(
                                "error" to
                                    "user_not_found"
                            )
                        )

                val targetId =
                    target.first

                val isFriend =
                    repository.isFriend(
                        userId,
                        targetId
                    )

                val privacy =
                    privacyRepository.get(
                        targetId
                    )

                if (
                    !visibilityAllowed(
                        privacy.showcaseVisibility,
                        isFriend
                    )
                ) {
                    return@get call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf(
                            "error" to
                                "showcase_private"
                        )
                    )
                }

                call.respond(
                    showcaseRepository.profile(
                        showcaseUserId =
                            targetId,
                        viewerId =
                            userId
                    )
                )
            }

            post("/{friendCode}/showcase/like") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@post call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val friendCode =
                    call.parameters["friendCode"]
                        ?.trim()
                        .orEmpty()

                val target =
                    repository.findUserByFriendCode(
                        friendCode
                    )
                        ?: return@post call.respond(
                            HttpStatusCode.NotFound,
                            mapOf(
                                "error" to
                                    "user_not_found"
                            )
                        )

                val targetId =
                    target.first

                val isFriend =
                    repository.isFriend(
                        userId,
                        targetId
                    )

                val privacy =
                    privacyRepository.get(
                        targetId
                    )

                if (
                    !visibilityAllowed(
                        privacy.showcaseVisibility,
                        isFriend
                    )
                ) {
                    return@post call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf(
                            "error" to
                                "showcase_private"
                        )
                    )
                }

                val profile =
                    showcaseRepository.toggleLike(
                        viewerId =
                            userId,
                        showcaseUserId =
                            targetId
                    )
                        ?: return@post call.respond(
                            HttpStatusCode.NotFound,
                            mapOf(
                                "error" to
                                    "showcase_not_found"
                            )
                        )

                call.respond(
                    profile
                )
            }

            get("/{friendCode}/showcase") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val friendCode =
                    call.parameters["friendCode"]
                        ?.trim()
                        .orEmpty()

                val target =
                    repository.findUserByFriendCode(
                        friendCode
                    )

                if (target == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf("error" to "user_not_found")
                    )
                    return@get
                }

                val targetId = target.first

                val isFriend =
                    repository.isFriend(
                        userId,
                        targetId
                    )

                val privacy =
                    privacyRepository.get(
                        targetId
                    )

                if (
                    !visibilityAllowed(
                        privacy.showcaseVisibility,
                        isFriend
                    )
                ) {
                    call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf("error" to "showcase_private")
                    )
                    return@get
                }

                call.respond(
                    showcaseRepository.list(
                        targetId
                    )
                )
            }

            get("/{friendCode}/collection") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val friendCode =
                    call.parameters["friendCode"]
                        ?.trim()
                        .orEmpty()

                val target =
                    repository.findUserByFriendCode(
                        friendCode
                    )

                if (target == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf(
                            "error" to
                                "user_not_found"
                        )
                    )
                    return@get
                }

                val targetId =
                    target.first

                val isFriend =
                    repository.isFriend(
                        userId,
                        targetId
                    )

                val privacy =
                    privacyRepository.get(
                        targetId
                    )

                if (
                    !visibilityAllowed(
                        privacy.collectionVisibility,
                        isFriend
                    )
                ) {
                    call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf(
                            "error" to
                                "collection_private"
                        )
                    )
                    return@get
                }

                val showQuantity =
                    visibilityAllowed(
                        privacy.quantityVisibility,
                        isFriend
                    )

                val showValue =
                    visibilityAllowed(
                        privacy.collectionValueVisibility,
                        isFriend
                    )

                val collection =
                    collectionRepository.load(
                        targetId,
                        showQuantity,
                        showValue
                    )

                call.respond(
                    FriendCollectionResponse(
                        totalValueEur =
                            collection.totalValueEur,

                        cards =
                            collection.cards.map {
                                FriendCollectionCardResponse(
                                    cardId =
                                        it.cardId,
                                    name =
                                        it.name,
                                    setId =
                                        it.setId,
                                    setName =
                                        it.setName,
                                    localId =
                                        it.localId,
                                    imageBase =
                                        it.imageBase,
                                    variant =
                                        it.variant,
                                    quantity =
                                        it.quantity
                                )
                            }
                    )
                )
            }

            get("/{friendCode}/sets") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val friendCode =
                    call.parameters["friendCode"]
                        ?.trim()
                        .orEmpty()

                val target =
                    repository.findUserByFriendCode(
                        friendCode
                    )

                if (target == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf(
                            "error" to
                                "user_not_found"
                        )
                    )
                    return@get
                }

                val targetId =
                    target.first

                val isFriend =
                    repository.isFriend(
                        userId,
                        targetId
                    )

                val privacy =
                    privacyRepository.get(
                        targetId
                    )

                if (
                    !visibilityAllowed(
                        privacy.setsVisibility,
                        isFriend
                    )
                ) {
                    call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf(
                            "error" to
                                "sets_private"
                        )
                    )
                    return@get
                }

                call.respond(
                    setRepository
                        .list(targetId)
                        .map {
                            FriendSetProgressResponse(
                                setId =
                                    it.setId,
                                setName =
                                    it.setName,
                                ownedCards =
                                    it.ownedCards,
                                totalCards =
                                    it.totalCards
                            )
                        }
                )
            }

            get("/{friendCode}/wishlist") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val friendCode =
                    call.parameters["friendCode"]
                        ?.trim()
                        .orEmpty()

                val target =
                    repository.findUserByFriendCode(
                        friendCode
                    )

                if (target == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf("error" to "user_not_found")
                    )
                    return@get
                }

                val targetId = target.first

                val isFriend =
                    repository.isFriend(
                        userId,
                        targetId
                    )

                val privacy =
                    privacyRepository.get(
                        targetId
                    )

                if (
                    !visibilityAllowed(
                        privacy.wishlistVisibility,
                        isFriend
                    )
                ) {
                    call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf("error" to "wishlist_private")
                    )
                    return@get
                }

                call.respond(
                    wishlistRepository
                        .list(targetId)
                        .map {
                            WishlistResponse(
                                id = it.id.toString(),
                                cardId = it.cardId,
                                languageCode = it.languageCode,
                                name = it.name,
                                setId = it.setId,
                                setName = it.setName,
                                localId = it.localId,
                                imageBase = it.imageBase,
                                variantId = it.variantId,
                                variantType = it.variantType,
                                variantSubtype = it.variantSubtype,
                                foil = it.foil,
                                size = it.size,
                                stamps = it.stamps,
                                priority =
                                    it.priority,
                                targetPriceEur =
                                    it.targetPriceEur
                            )
                        }
                )
            }

            get("/search") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val query =
                    call.request
                        .queryParameters["q"]
                        .orEmpty()

                call.respond(
                    repository
                        .searchUsers(
                            userId,
                            query
                        )
                        .map {
                            FriendUserResponse(
                                friendCode =
                                    it.friendCode,
                                displayName =
                                    it.displayName
                            )
                        }
                )
            }

            get("/requests") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                fun map(
                    request: FriendRequestRecord
                ) =
                    FriendRequestResponse(
                        id =
                            request.id.toString(),
                        user =
                            FriendUserResponse(
                                friendCode =
                                    request.user.friendCode,
                                displayName =
                                    request.user.displayName
                            ),
                        createdAt =
                            request.createdAt
                    )

                call.respond(
                    FriendRequestsResponse(
                        incoming =
                            repository
                                .incomingRequests(userId)
                                .map(::map),
                        outgoing =
                            repository
                                .outgoingRequests(userId)
                                .map(::map)
                    )
                )
            }

            post("/requests") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@post call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val request =
                    call.receive<SendFriendRequest>()

                when (
                    repository.createRequest(
                        userId,
                        request.friendCode
                    )
                ) {
                    CreateFriendRequestResult.CREATED ->
                        call.respond(
                            HttpStatusCode.Created,
                            mapOf(
                                "status" to "created"
                            )
                        )

                    CreateFriendRequestResult.USER_NOT_FOUND ->
                        call.respond(
                            HttpStatusCode.NotFound,
                            mapOf(
                                "error" to "user_not_found"
                            )
                        )

                    CreateFriendRequestResult.SELF ->
                        call.respond(
                            HttpStatusCode.BadRequest,
                            mapOf(
                                "error" to "cannot_add_self"
                            )
                        )

                    CreateFriendRequestResult.ALREADY_EXISTS ->
                        call.respond(
                            HttpStatusCode.Conflict,
                            mapOf(
                                "error" to "friendship_exists"
                            )
                        )
                }
            }

            post("/requests/{id}/accept") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@post call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val requestId =
                    call.parameters["id"]
                        ?.let {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }

                if (requestId == null) {
                    call.respond(
                        HttpStatusCode.BadRequest
                    )
                    return@post
                }

                if (
                    !repository.acceptRequest(
                        userId,
                        requestId
                    )
                ) {
                    call.respond(
                        HttpStatusCode.NotFound
                    )
                    return@post
                }

                call.respond(
                    mapOf(
                        "status" to "accepted"
                    )
                )
            }

            delete("/requests/{id}") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@delete call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val requestId =
                    call.parameters["id"]
                        ?.let {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }

                if (requestId == null) {
                    call.respond(
                        HttpStatusCode.BadRequest
                    )
                    return@delete
                }

                if (
                    !repository.deletePendingRequest(
                        userId,
                        requestId
                    )
                ) {
                    call.respond(
                        HttpStatusCode.NotFound
                    )
                    return@delete
                }

                call.respond(
                    HttpStatusCode.NoContent
                )
            }
        }
    }
}

@Serializable
data class FriendSetProgressResponse(
    val setId: String,
    val setName: String?,
    val ownedCards: Int,
    val totalCards: Int?
)

@Serializable
data class FriendCollectionCardResponse(
    val cardId: String,
    val name: String,
    val setId: String?,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variant: String,
    val quantity: Int?
)

@Serializable
data class FriendCollectionResponse(
    val totalValueEur: Double?,
    val cards: List<FriendCollectionCardResponse>
)

@Serializable
data class FriendProfileResponse(
    val friendCode: String,
    val displayName: String?,
    val avatarUrl: String?,
    val favoritePokemon: String? = null,
    val favoriteSet: String? = null,
    val collectingFocus: String? = null,
    val isFriend: Boolean,
    val canSeeShowcase: Boolean,
    val canSeeCollection: Boolean,
    val canSeeCollectionValue: Boolean,
    val canSeeQuantity: Boolean,
    val canSeeSets: Boolean,
    val canSeeWishlist: Boolean
)

private fun visibilityAllowed(
    visibility: String,
    isFriend: Boolean
): Boolean =
    visibility == "PUBLIC" ||
        (
            visibility == "FRIENDS" &&
            isFriend
        )
