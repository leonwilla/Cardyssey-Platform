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

private val supportedThemes =
    setOf(
        "OBSIDIAN_GOLD",
        "MIDNIGHT_CYAN",
        "ROYAL_VIOLET",
        "EMERALD_MINT"
    )

@Serializable
data class AppearanceSettings(
    val theme: String = "OBSIDIAN_GOLD"
)

class AppearanceRepository(
    private val dataSource: HikariDataSource
) {
    fun get(userId: UUID): AppearanceSettings {
        ensureExists(userId)

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT theme
                FROM user_appearance_settings
                WHERE user_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    return if (result.next()) {
                        AppearanceSettings(
                            theme = result.getString("theme")
                        )
                    } else {
                        AppearanceSettings()
                    }
                }
            }
        }
    }

    fun update(
        userId: UUID,
        settings: AppearanceSettings
    ): AppearanceSettings {
        ensureExists(userId)

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE user_appearance_settings
                SET theme = ?, updated_at = NOW()
                WHERE user_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, settings.theme)
                statement.setObject(2, userId)
                statement.executeUpdate()
            }
        }

        return get(userId)
    }

    private fun ensureExists(userId: UUID) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO user_appearance_settings (user_id)
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

fun Route.appearanceRoutes(
    repository: AppearanceRepository
) {
    authenticate("auth-jwt") {
        route("/api/v1/me/appearance") {
            get {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(repository.get(userId))
            }

            put {
                val userId =
                    call.authenticatedUserId()
                        ?: return@put call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val settings =
                    call.receive<AppearanceSettings>()

                if (settings.theme !in supportedThemes) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_theme")
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
