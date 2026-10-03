package de.cardyssey.api

import com.auth0.jwt.JWT
import com.auth0.jwt.algorithms.Algorithm
import com.auth0.jwt.interfaces.JWTVerifier
import com.zaxxer.hikari.HikariDataSource
import de.mkammerer.argon2.Argon2Factory
import de.mkammerer.argon2.Argon2Factory.Argon2Types
import kotlinx.serialization.Serializable
import java.security.MessageDigest
import java.security.SecureRandom
import java.sql.SQLException
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.Base64
import java.util.Date
import java.util.UUID

@Serializable
data class RegisterRequest(
    val email: String,
    val password: String,
    val displayName: String? = null
)

@Serializable
data class LoginRequest(
    val email: String,
    val password: String
)

@Serializable
data class RefreshRequest(
    val refreshToken: String
)

@Serializable
data class LogoutRequest(
    val refreshToken: String
)

private fun friendCodeFor(
    id: UUID
): String {
    val compact =
        id.toString()
            .replace("-", "")
            .uppercase()
            .take(20)

    return "CDY-" +
        compact
            .chunked(4)
            .joinToString("-")
}

private fun friendCodeFor(
    id: String
): String =
    friendCodeFor(
        UUID.fromString(id)
    )

@Serializable
data class UserResponse(
    val id: String,
    val email: String,
    val displayName: String?,
    val avatarUrl: String? = null,
    val favoritePokemon: String? = null,
    val favoriteSet: String? = null,
    val collectingFocus: String? = null,
    val friendCode: String =
        friendCodeFor(id)
)

@Serializable
data class AuthResponse(
    val accessToken: String,
    val accessTokenExpiresInSeconds: Long,
    val refreshToken: String,
    val refreshTokenExpiresInSeconds: Long,
    val user: UserResponse
)

data class UserRecord(
    val id: UUID,
    val email: String,
    val displayName: String?,
    val avatarPath: String?,
    val favoritePokemon: String? = null,
    val favoriteSet: String? = null,
    val collectingFocus: String? = null
)

object PasswordHasher {

    fun hash(password: String): String {
        val chars = password.toCharArray()

        return try {
            Argon2Factory
                .create(Argon2Types.ARGON2id)
                .hash(
                    3,
                    65_536,
                    1,
                    chars
                )
        } finally {
            chars.fill('\u0000')
        }
    }

    fun verify(
        encodedHash: String,
        password: String
    ): Boolean {
        val chars = password.toCharArray()

        return try {
            Argon2Factory
                .create(Argon2Types.ARGON2id)
                .verify(
                    encodedHash,
                    chars
                )
        } finally {
            chars.fill('\u0000')
        }
    }
}

class TokenService(
    secret: String
) {
    companion object {
        const val ACCESS_SECONDS = 15L * 60L
        const val REFRESH_SECONDS = 30L * 24L * 60L * 60L

        const val ISSUER = "cardyssey-api"
        const val AUDIENCE = "cardyssey-clients"
    }

    private val algorithm =
        Algorithm.HMAC256(secret)

    val verifier: JWTVerifier =
        JWT.require(algorithm)
            .withIssuer(ISSUER)
            .withAudience(AUDIENCE)
            .build()

    fun createAccessToken(
        user: UserRecord
    ): String {
        val now = Instant.now()
        val expires = now.plusSeconds(ACCESS_SECONDS)

        return JWT.create()
            .withIssuer(ISSUER)
            .withAudience(AUDIENCE)
            .withSubject(user.id.toString())
            .withClaim("email", user.email)
            .withIssuedAt(Date.from(now))
            .withExpiresAt(Date.from(expires))
            .sign(algorithm)
    }

    fun createRefreshToken(): String {
        val bytes = ByteArray(64)
        SecureRandom().nextBytes(bytes)

        return Base64
            .getUrlEncoder()
            .withoutPadding()
            .encodeToString(bytes)
    }

    fun hashRefreshToken(
        token: String
    ): String {
        val digest =
            MessageDigest
                .getInstance("SHA-256")
                .digest(
                    token.toByteArray(
                        Charsets.UTF_8
                    )
                )

        return digest.joinToString("") {
            "%02x".format(it)
        }
    }

    fun refreshExpiry(): Instant =
        Instant.now()
            .plus(
                30,
                ChronoUnit.DAYS
            )
}

class AuthRepository(
    private val dataSource: HikariDataSource
) {

    fun createUser(
        email: String,
        passwordHash: String,
        displayName: String?
    ): UserRecord? {
        val id = UUID.randomUUID()

        return try {
            dataSource.connection.use { connection ->
                connection.prepareStatement(
                    """
                    INSERT INTO users (
                        id,
                        email,
                        password_hash,
                        display_name,
                        friend_code
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """.trimIndent()
                ).use { statement ->

                    statement.setObject(1, id)
                    statement.setString(2, email)
                    statement.setString(3, passwordHash)
                    statement.setString(4, displayName)

                    statement.setString(
                        5,
                        friendCodeFor(id)
                    )

                    statement.executeUpdate()
                }
            }

            UserRecord(
                id = id,
                email = email,
                displayName = displayName,
                avatarPath = null
            )
        } catch (exception: SQLException) {
            if (exception.sqlState == "23505") {
                null
            } else {
                throw exception
            }
        }
    }

    fun findByEmail(
        email: String
    ): Pair<UserRecord, String>? {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    id,
                    email,
                    display_name,
                    avatar_path,
                    favorite_pokemon,
                    favorite_set,
                    collecting_focus,
                    password_hash
                FROM users
                WHERE LOWER(email) = LOWER(?)
                  AND disabled_at IS NULL
                LIMIT 1
                """.trimIndent()
            ).use { statement ->

                statement.setString(1, email)

                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        return null
                    }

                    return Pair(
                        UserRecord(
                            id = UUID.fromString(
                                result.getString("id")
                            ),
                            email =
                                result.getString("email"),
                            displayName =
                                result.getString(
                                    "display_name"
                                ),
                            avatarPath =
                                result.getString(
                                    "avatar_path"
                                ),
                            favoritePokemon =
                                result.getString(
                                    "favorite_pokemon"
                                ),
                            favoriteSet =
                                result.getString(
                                    "favorite_set"
                                ),
                            collectingFocus =
                                result.getString(
                                    "collecting_focus"
                                )
                        ),
                        result.getString(
                            "password_hash"
                        )
                    )
                }
            }
        }
    }

    fun findById(
        id: UUID
    ): UserRecord? {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    id,
                    email,
                    display_name,
                    avatar_path,
                    favorite_pokemon,
                    favorite_set,
                    collecting_focus
                FROM users
                WHERE id = ?
                  AND disabled_at IS NULL
                LIMIT 1
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, id)

                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        return null
                    }

                    return UserRecord(
                        id = UUID.fromString(
                            result.getString("id")
                        ),
                        email =
                            result.getString("email"),
                        displayName =
                            result.getString(
                                "display_name"
                            ),
                        avatarPath =
                            result.getString(
                                "avatar_path"
                            ),
                        favoritePokemon =
                            result.getString(
                                "favorite_pokemon"
                            ),
                        favoriteSet =
                            result.getString(
                                "favorite_set"
                            ),
                        collectingFocus =
                            result.getString(
                                "collecting_focus"
                            )
                    )
                }
            }
        }
    }

    fun updateDisplayName(
        id: UUID,
        displayName: String?
    ): UserRecord? {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE users
                SET
                    display_name = ?,
                    updated_at = NOW()
                WHERE id = ?
                  AND disabled_at IS NULL
                """.trimIndent()
            ).use { statement ->

                statement.setString(
                    1,
                    displayName
                )

                statement.setObject(
                    2,
                    id
                )

                if (
                    statement.executeUpdate() == 0
                ) {
                    return null
                }
            }
        }

        return findById(id)
    }

    fun updateCollectorProfile(
        id: UUID,
        displayName: String?,
        favoritePokemon: String?,
        favoriteSet: String?,
        collectingFocus: String?
    ): UserRecord? {
        dataSource.connection.use {
            connection ->
            connection.prepareStatement(
                """
                UPDATE users
                SET display_name = ?,
                    favorite_pokemon = ?,
                    favorite_set = ?,
                    collecting_focus = ?,
                    updated_at = NOW()
                WHERE id = ?
                  AND disabled_at IS NULL
                """.trimIndent()
            ).use {
                statement ->
                statement.setString(
                    1,
                    displayName
                )
                statement.setString(
                    2,
                    favoritePokemon
                )
                statement.setString(
                    3,
                    favoriteSet
                )
                statement.setString(
                    4,
                    collectingFocus
                )
                statement.setObject(
                    5,
                    id
                )

                if (
                    statement.executeUpdate() ==
                    0
                ) {
                    return null
                }
            }
        }

        return findById(
            id
        )
    }

    fun updateAvatarPath(
        id: UUID,
        avatarPath: String?
    ): UserRecord? {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE users
                SET
                    avatar_path = ?,
                    updated_at = NOW()
                WHERE id = ?
                  AND disabled_at IS NULL
                """.trimIndent()
            ).use { statement ->

                statement.setString(
                    1,
                    avatarPath
                )

                statement.setObject(
                    2,
                    id
                )

                if (
                    statement.executeUpdate() == 0
                ) {
                    return null
                }
            }
        }

        return findById(id)
    }


    fun storeRefreshToken(
        userId: UUID,
        tokenHash: String,
        expiresAt: Instant
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO refresh_tokens (
                    id,
                    user_id,
                    token_hash,
                    expires_at
                )
                VALUES (?, ?, ?, ?)
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    UUID.randomUUID()
                )

                statement.setObject(
                    2,
                    userId
                )

                statement.setString(
                    3,
                    tokenHash
                )

                statement.setObject(
                    4,
                    java.time.OffsetDateTime.ofInstant(
                        expiresAt,
                        java.time.ZoneOffset.UTC
                    )
                )

                statement.executeUpdate()
            }
        }
    }

    fun consumeRefreshToken(
        tokenHash: String
    ): UserRecord? {

        dataSource.connection.use { connection ->
            connection.autoCommit = false

            try {
                val user =
                    connection.prepareStatement(
                        """
                        SELECT
                            u.id,
                            u.email,
                            u.display_name,
                            u.avatar_path,
                            u.favorite_pokemon,
                            u.favorite_set,
                            u.collecting_focus
                        FROM refresh_tokens rt
                        JOIN users u
                          ON u.id = rt.user_id
                        WHERE rt.token_hash = ?
                          AND rt.revoked_at IS NULL
                          AND rt.expires_at > NOW()
                          AND u.disabled_at IS NULL
                        LIMIT 1
                        FOR UPDATE OF rt
                        """.trimIndent()
                    ).use { statement ->

                        statement.setString(
                            1,
                            tokenHash
                        )

                        statement
                            .executeQuery()
                            .use { result ->

                                if (!result.next()) {
                                    null
                                } else {
                                    UserRecord(
                                        id =
                                            UUID.fromString(
                                                result.getString(
                                                    "id"
                                                )
                                            ),
                                        email =
                                            result.getString(
                                                "email"
                                            ),
                                        displayName =
                                            result.getString(
                                                "display_name"
                                            ),
                                        avatarPath =
                                            result.getString(
                                                "avatar_path"
                                            ),
                                        favoritePokemon =
                                            result.getString(
                                                "favorite_pokemon"
                                            ),
                                        favoriteSet =
                                            result.getString(
                                                "favorite_set"
                                            ),
                                        collectingFocus =
                                            result.getString(
                                                "collecting_focus"
                                            )
                                    )
                                }
                            }
                    }

                if (user == null) {
                    connection.rollback()
                    return null
                }

                connection.prepareStatement(
                    """
                    UPDATE refresh_tokens
                    SET revoked_at = NOW()
                    WHERE token_hash = ?
                    """.trimIndent()
                ).use { statement ->
                    statement.setString(
                        1,
                        tokenHash
                    )
                    statement.executeUpdate()
                }

                connection.commit()

                return user

            } catch (throwable: Throwable) {
                connection.rollback()
                throw throwable
            } finally {
                connection.autoCommit = true
            }
        }
    }

    fun revokeRefreshToken(
        tokenHash: String
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE refresh_tokens
                SET revoked_at = NOW()
                WHERE token_hash = ?
                  AND revoked_at IS NULL
                """.trimIndent()
            ).use { statement ->

                statement.setString(
                    1,
                    tokenHash
                )

                statement.executeUpdate()
            }
        }
    }

    fun deleteOwnAccount(
        userId: UUID
    ): Boolean {
        var avatarPath: String? = null

        val deleted =
            dataSource.connection.use {
                connection ->
                connection.autoCommit = false

                try {
                    avatarPath =
                        connection.prepareStatement(
                            """
                            SELECT avatar_path
                            FROM users
                            WHERE id = ?
                              AND disabled_at IS NULL
                            FOR UPDATE
                            """.trimIndent()
                        ).use {
                            statement ->
                            statement.setObject(
                                1,
                                userId
                            )

                            statement.executeQuery()
                                .use {
                                    result ->
                                    if (
                                        result.next()
                                    ) {
                                        result.getString(
                                            "avatar_path"
                                        )
                                    } else {
                                        null
                                    }
                                }
                        }

                    val count =
                        connection.prepareStatement(
                            "DELETE FROM users WHERE id = ?"
                        ).use {
                            statement ->
                            statement.setObject(
                                1,
                                userId
                            )
                            statement.executeUpdate()
                        }

                    if (count != 1) {
                        connection.rollback()
                        false
                    } else {
                        connection.commit()
                        true
                    }
                } catch (
                    error: Throwable
                ) {
                    runCatching {
                        connection.rollback()
                    }
                    throw error
                } finally {
                    runCatching {
                        connection.autoCommit =
                            true
                    }
                }
            }

        if (
            deleted &&
            !avatarPath.isNullOrBlank() &&
            avatarPath!!.matches(
                Regex(
                    "^[A-Za-z0-9._-]+$"
                )
            )
        ) {
            val directory =
                java.io.File(
                    System.getenv(
                        "AVATAR_DIR"
                    )
                        ?.takeIf(
                            String::isNotBlank
                        )
                        ?: "/data/avatars"
                )

            runCatching {
                java.io.File(
                    directory,
                    avatarPath!!
                ).delete()
            }
        }

        return deleted
    }
}
