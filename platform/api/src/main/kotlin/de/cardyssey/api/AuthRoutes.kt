package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.put
import io.ktor.server.routing.route
import kotlinx.serialization.Serializable

@Serializable
data class UpdateMeRequest(
    val displayName: String?,
    val favoritePokemon: String? = null,
    val favoriteSet: String? = null,
    val collectingFocus: String? = null
)

private val EMAIL_REGEX =
    Regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")

fun Route.authRoutes(
    repository: AuthRepository,
    tokens: TokenService,
    registrationSettings: RegistrationSettingsRepository
) {

    route("/api/v1/auth") {

        get("/registration-status") {
            call.respond(
                registrationSettings.get()
            )
        }

        post("/register") {
            if (!registrationSettings.registrationsEnabled()) {
                call.respond(
                    HttpStatusCode.Forbidden,
                    mapOf(
                        "error" to "registration_closed",
                        "message" to "Registrations are currently disabled."
                    )
                )
                return@post
            }

            val request =
                call.receive<RegisterRequest>()

            val email =
                request.email
                    .trim()
                    .lowercase()

            val displayName =
                request.displayName
                    ?.trim()
                    ?.takeIf {
                        it.isNotBlank()
                    }
                    ?.take(100)

            if (!EMAIL_REGEX.matches(email)) {
                call.respond(
                    HttpStatusCode.BadRequest,
                    mapOf(
                        "error" to
                            "invalid_email"
                    )
                )
                return@post
            }

            if (
                request.password.length < 12 ||
                request.password.length > 128
            ) {
                call.respond(
                    HttpStatusCode.BadRequest,
                    mapOf(
                        "error" to
                            "invalid_password",
                        "message" to
                            "Password must contain between 12 and 128 characters."
                    )
                )
                return@post
            }

            val passwordHash =
                PasswordHasher.hash(
                    request.password
                )

            val user =
                repository.createUser(
                    email = email,
                    passwordHash = passwordHash,
                    displayName = displayName
                )

            if (user == null) {
                call.respond(
                    HttpStatusCode.Conflict,
                    mapOf(
                        "error" to
                            "email_already_registered"
                    )
                )
                return@post
            }

            call.respond(
                HttpStatusCode.Created,
                issueAuth(
                    user,
                    repository,
                    tokens
                )
            )
        }


        post("/login") {
            val request =
                call.receive<LoginRequest>()

            val result =
                repository.findByEmail(
                    request.email.trim()
                )

            if (
                result == null ||
                !PasswordHasher.verify(
                    result.second,
                    request.password
                )
            ) {
                call.respond(
                    HttpStatusCode.Unauthorized,
                    mapOf(
                        "error" to
                            "invalid_credentials"
                    )
                )
                return@post
            }

            call.respond(
                issueAuth(
                    result.first,
                    repository,
                    tokens
                )
            )
        }


        post("/refresh") {
            val request =
                call.receive<RefreshRequest>()

            val oldHash =
                tokens.hashRefreshToken(
                    request.refreshToken
                )

            val user =
                repository.consumeRefreshToken(
                    oldHash
                )

            if (user == null) {
                call.respond(
                    HttpStatusCode.Unauthorized,
                    mapOf(
                        "error" to
                            "invalid_refresh_token"
                    )
                )
                return@post
            }

            call.respond(
                issueAuth(
                    user,
                    repository,
                    tokens
                )
            )
        }


        post("/logout") {
            val request =
                call.receive<LogoutRequest>()

            repository.revokeRefreshToken(
                tokens.hashRefreshToken(
                    request.refreshToken
                )
            )

            call.respond(
                HttpStatusCode.NoContent
            )
        }
    }


    authenticate("auth-jwt") {

        put("/api/v1/me") {

            val id =
                call.authenticatedUserId()

            if (id == null) {
                call.respond(
                    HttpStatusCode.Unauthorized
                )
                return@put
            }

            val request =
                call.receive<UpdateMeRequest>()

            val displayName =
                request.displayName
                    ?.trim()
                    ?.takeIf {
                        it.isNotBlank()
                    }
                    ?.take(100)

            val favoritePokemon =
                request.favoritePokemon
                    ?.trim()
                    ?.takeIf {
                        it.isNotBlank()
                    }
                    ?.take(80)

            val favoriteSet =
                request.favoriteSet
                    ?.trim()
                    ?.takeIf {
                        it.isNotBlank()
                    }
                    ?.take(120)

            val collectingFocus =
                request.collectingFocus
                    ?.trim()
                    ?.takeIf {
                        it.isNotBlank()
                    }
                    ?.take(240)

            val user =
                repository.updateCollectorProfile(
                    id =
                        id,
                    displayName =
                        displayName,
                    favoritePokemon =
                        favoritePokemon,
                    favoriteSet =
                        favoriteSet,
                    collectingFocus =
                        collectingFocus
                )

            if (user == null) {
                call.respond(
                    HttpStatusCode.NotFound
                )
                return@put
            }

            call.respond(
                UserResponse(
                    id = user.id.toString(),
                    email = user.email,
                    displayName =
                        user.displayName,
                    avatarUrl =
                        avatarUrlFor(
                            user.avatarPath
                        ),
                    favoritePokemon =
                        user.favoritePokemon,
                    favoriteSet =
                        user.favoriteSet,
                    collectingFocus =
                        user.collectingFocus
                )
            )
        }


        get("/api/v1/me") {

            val id =
                call.authenticatedUserId()

            if (id == null) {
                call.respond(
                    HttpStatusCode.Unauthorized
                )
                return@get
            }

            val user =
                repository.findById(id)

            if (user == null) {
                call.respond(
                    HttpStatusCode.Unauthorized
                )
                return@get
            }

            call.respond(
                UserResponse(
                    id =
                        user.id.toString(),
                    email =
                        user.email,
                    displayName =
                        user.displayName,
                    avatarUrl =
                        avatarUrlFor(
                            user.avatarPath
                        ),
                    favoritePokemon =
                        user.favoritePokemon,
                    favoriteSet =
                        user.favoriteSet,
                    collectingFocus =
                        user.collectingFocus
                )
            )
        }
    }
}


private fun issueAuth(
    user: UserRecord,
    repository: AuthRepository,
    tokens: TokenService
): AuthResponse {

    val refreshToken =
        tokens.createRefreshToken()

    repository.storeRefreshToken(
        userId =
            user.id,
        tokenHash =
            tokens.hashRefreshToken(
                refreshToken
            ),
        expiresAt =
            tokens.refreshExpiry()
    )

    return AuthResponse(
        accessToken =
            tokens.createAccessToken(
                user
            ),
        accessTokenExpiresInSeconds =
            TokenService.ACCESS_SECONDS,

        refreshToken =
            refreshToken,
        refreshTokenExpiresInSeconds =
            TokenService.REFRESH_SECONDS,

        user =
            UserResponse(
                id =
                    user.id.toString(),
                email =
                    user.email,
                displayName =
                    user.displayName,
                avatarUrl =
                    avatarUrlFor(
                        user.avatarPath
                    ),
                favoritePokemon =
                    user.favoritePokemon,
                favoriteSet =
                    user.favoriteSet,
                collectingFocus =
                    user.collectingFocus
            )
    )
}
