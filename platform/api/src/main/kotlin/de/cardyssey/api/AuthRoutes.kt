package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.delete
import io.ktor.server.routing.post
import io.ktor.server.routing.put
import io.ktor.server.routing.route
import kotlinx.serialization.Serializable
import java.util.concurrent.ConcurrentHashMap

@Serializable
data class UpdateMeRequest(
    val displayName: String?,
    val favoritePokemon: String? = null,
    val favoriteSet: String? = null,
    val collectingFocus: String? = null
)

private val EMAIL_REGEX =
    Regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")

private class LoginAttemptGuard {
    private data class State(
        var failures: Int,
        var blockedUntilMs: Long
    )

    private val states =
        ConcurrentHashMap<
            String,
            State
        >()

    fun allowed(
        email: String
    ): Boolean {
        val now =
            System.currentTimeMillis()

        val state =
            states[
                email.normalizedKey()
            ]
                ?: return true

        if (
            state.blockedUntilMs >
            now
        ) {
            return false
        }

        if (
            state.blockedUntilMs >
            0L
        ) {
            states.remove(
                email.normalizedKey()
            )
        }

        return true
    }

    fun failure(
        email: String
    ) {
        val key =
            email.normalizedKey()

        val now =
            System.currentTimeMillis()

        states.compute(
            key
        ) {
            _,
            previous ->
            val current =
                previous
                    ?.takeIf {
                        it.blockedUntilMs <=
                            now
                    }

            val failures =
                (
                    current?.failures
                        ?: 0
                    ) + 1

            State(
                failures =
                    failures,
                blockedUntilMs =
                    if (
                        failures >=
                        8
                    ) {
                        now +
                            15L *
                            60L *
                            1000L
                    } else {
                        0L
                    }
            )
        }
    }

    fun success(
        email: String
    ) {
        states.remove(
            email.normalizedKey()
        )
    }

    private fun String.normalizedKey():
        String =
        trim()
            .lowercase()
            .take(
                320
            )
}

private val loginAttemptGuard =
    LoginAttemptGuard()

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

            val email =
                request.email
                    .trim()
                    .lowercase()

            if (
                !loginAttemptGuard
                    .allowed(
                        email
                    )
            ) {
                call.respond(
                    HttpStatusCode.TooManyRequests,
                    mapOf(
                        "error" to
                            "login_rate_limited",
                        "message" to
                            "Too many failed login attempts. Try again later."
                    )
                )
                return@post
            }

            val result =
                repository.findByEmail(
                    email
                )

            if (
                result == null ||
                !PasswordHasher.verify(
                    result.second,
                    request.password
                )
            ) {
                loginAttemptGuard
                    .failure(
                        email
                    )

                call.respond(
                    HttpStatusCode.Unauthorized,
                    mapOf(
                        "error" to
                            "invalid_credentials"
                    )
                )
                return@post
            }

            loginAttemptGuard
                .success(
                    email
                )

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


        delete("/api/v1/me") {
            val id = call.authenticatedUserId()
            if (id == null) {
                call.respond(HttpStatusCode.Unauthorized)
                return@delete
            }

            if (!repository.deleteOwnAccount(id)) {
                call.respond(HttpStatusCode.NotFound)
                return@delete
            }

            call.respond(HttpStatusCode.NoContent)
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
