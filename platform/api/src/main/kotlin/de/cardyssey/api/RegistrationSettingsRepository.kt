package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable

@Serializable
data class RegistrationSettingsResponse(
    val enabled: Boolean
)

@Serializable
data class UpdateRegistrationSettingsRequest(
    val enabled: Boolean
)

class RegistrationSettingsRepository(
    private val dataSource: HikariDataSource
) {
    fun get(): RegistrationSettingsResponse =
        RegistrationSettingsResponse(
            enabled = registrationsEnabled()
        )

    fun registrationsEnabled(): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT value
                FROM system_settings
                WHERE key = 'registrations_enabled'
                LIMIT 1
                """.trimIndent()
            ).use { statement ->
                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        false
                    } else {
                        result.getString("value")
                            ?.trim()
                            ?.equals("true", ignoreCase = true)
                            ?: false
                    }
                }
            }
        }

    fun setRegistrationsEnabled(enabled: Boolean): RegistrationSettingsResponse {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO system_settings (
                    key,
                    value,
                    updated_at
                )
                VALUES (
                    'registrations_enabled',
                    ?,
                    NOW()
                )
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, enabled.toString())
                statement.executeUpdate()
            }
        }

        return RegistrationSettingsResponse(enabled)
    }
}
