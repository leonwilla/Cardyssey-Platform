package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
enum class UserRole {
    USER,
    ADMIN,
    FOUNDER;

    val canAdmin: Boolean
        get() = this == ADMIN || this == FOUNDER

    val canFounder: Boolean
        get() = this == FOUNDER

    companion object {
        fun parse(value: String?): UserRole? =
            entries.firstOrNull {
                it.name.equals(
                    value?.trim(),
                    ignoreCase = true
                )
            }
    }
}

@Serializable
data class AdminAccessResponse(
    val role: UserRole,
    val canAdmin: Boolean,
    val canFounder: Boolean
)

class RoleRepository(
    private val dataSource: HikariDataSource
) {
    fun roleFor(userId: UUID): UserRole? {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT role
                FROM users
                WHERE id = ?
                  AND disabled_at IS NULL
                LIMIT 1
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        return null
                    }

                    return UserRole.parse(
                        result.getString("role")
                    )
                }
            }
        }
    }

    fun accessFor(userId: UUID): AdminAccessResponse? {
        val role = roleFor(userId)
            ?: return null

        return AdminAccessResponse(
            role = role,
            canAdmin = role.canAdmin,
            canFounder = role.canFounder
        )
    }
}
