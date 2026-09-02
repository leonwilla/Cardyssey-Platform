package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.put
import io.ktor.server.routing.route
import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
data class PrivacySettings(
    val profileVisibility: String = "PUBLIC",
    val showcaseVisibility: String = "PUBLIC",
    val collectionVisibility: String = "FRIENDS",
    val collectionValueVisibility: String = "PRIVATE",
    val quantityVisibility: String = "PRIVATE",
    val setsVisibility: String = "PUBLIC",
    val wishlistVisibility: String = "FRIENDS",
    val showcaseSize: Int = 5
)

class PrivacyRepository(
    private val dataSource: HikariDataSource
) {

    fun get(userId: UUID): PrivacySettings {

        ensureExists(userId)

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    profile_visibility,
                    showcase_visibility,
                    collection_visibility,
                    collection_value_visibility,
                    quantity_visibility,
                    sets_visibility,
                    wishlist_visibility,
                    showcase_size
                FROM user_privacy_settings
                WHERE user_id = ?
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        return PrivacySettings()
                    }

                    return PrivacySettings(
                        profileVisibility =
                            result.getString("profile_visibility"),
                        showcaseVisibility =
                            result.getString("showcase_visibility"),
                        collectionVisibility =
                            result.getString("collection_visibility"),
                        collectionValueVisibility =
                            result.getString("collection_value_visibility"),
                        quantityVisibility =
                            result.getString("quantity_visibility"),
                        setsVisibility =
                            result.getString("sets_visibility"),
                        wishlistVisibility =
                            result.getString("wishlist_visibility"),
                        showcaseSize =
                            result.getInt("showcase_size")
                    )
                }
            }
        }
    }

    fun update(
        userId: UUID,
        settings: PrivacySettings
    ): PrivacySettings {

        ensureExists(userId)

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE user_privacy_settings
                SET
                    profile_visibility = ?,
                    showcase_visibility = ?,
                    collection_visibility = ?,
                    collection_value_visibility = ?,
                    quantity_visibility = ?,
                    sets_visibility = ?,
                    wishlist_visibility = ?,
                    showcase_size = ?,
                    updated_at = NOW()
                WHERE user_id = ?
                """.trimIndent()
            ).use { statement ->

                statement.setString(1, settings.profileVisibility)
                statement.setString(2, settings.showcaseVisibility)
                statement.setString(3, settings.collectionVisibility)
                statement.setString(4, settings.collectionValueVisibility)
                statement.setString(5, settings.quantityVisibility)
                statement.setString(6, settings.setsVisibility)
                statement.setString(7, settings.wishlistVisibility)
                statement.setInt(8, settings.showcaseSize)
                statement.setObject(9, userId)

                statement.executeUpdate()
            }
        }

        return get(userId)
    }

    private fun ensureExists(userId: UUID) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO user_privacy_settings (user_id)
                VALUES (?)
                ON CONFLICT (user_id) DO NOTHING
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)
                statement.executeUpdate()
            }
        }
    }
}

fun Route.privacyRoutes(
    repository: PrivacyRepository
) {

    authenticate("auth-jwt") {

        route("/api/v1/me/privacy") {

            get {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    repository.get(userId)
                )
            }

            put {
                val userId =
                    call.authenticatedUserId()
                        ?: return@put call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val settings =
                    call.receive<PrivacySettings>()

                val valid =
                    setOf(
                        "PRIVATE",
                        "FRIENDS",
                        "PUBLIC"
                    )

                if (
                    settings.profileVisibility !in valid ||
                    settings.showcaseVisibility !in valid ||
                    settings.collectionVisibility !in valid ||
                    settings.collectionValueVisibility !in valid ||
                    settings.quantityVisibility !in valid ||
                    settings.setsVisibility !in valid ||
                    settings.wishlistVisibility !in valid ||
                    settings.showcaseSize !in setOf(5, 10)
                ) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_privacy_settings")
                    )
                    return@put
                }

                call.respond(
                    repository.update(
                        userId,
                        settings
                    )
                )
            }
        }
    }
}
