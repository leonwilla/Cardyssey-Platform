package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import java.io.File
import java.util.UUID

enum class AdminDeleteUserResult {
    DELETED,
    NOT_FOUND,
    SELF_FORBIDDEN,
    FOUNDER_FORBIDDEN,
    SYSTEM_BOT_FORBIDDEN
}

class AdminUserManagementRepository(
    private val dataSource: HikariDataSource
) {
    fun deleteUser(
        userId: UUID,
        actorUserId: UUID
    ): AdminDeleteUserResult =
        dataSource.connection.use { connection ->
            connection.autoCommit = false

            try {
                val target =
                    connection.prepareStatement(
                        """
                        SELECT email, display_name, role, avatar_path
                        FROM users
                        WHERE id = ?
                        FOR UPDATE
                        """.trimIndent()
                    ).use { statement ->
                        statement.setObject(1, userId)

                        statement.executeQuery().use { result ->
                            if (!result.next()) {
                                null
                            } else {
                                TargetUser(
                                    email = result.getString("email"),
                                    displayName = result.getString("display_name"),
                                    role = UserRole.parse(result.getString("role")) ?: UserRole.USER,
                                    avatarPath = result.getString("avatar_path")
                                )
                            }
                        }
                    }

                if (target == null) {
                    connection.rollback()
                    return@use AdminDeleteUserResult.NOT_FOUND
                }

                val forbidden =
                    when {
                        userId == actorUserId ->
                            AdminDeleteUserResult.SELF_FORBIDDEN

                        target.role == UserRole.FOUNDER ->
                            AdminDeleteUserResult.FOUNDER_FORBIDDEN

                        target.isRuntimeSmokeBot ->
                            AdminDeleteUserResult.SYSTEM_BOT_FORBIDDEN

                        else -> null
                    }

                if (forbidden != null) {
                    connection.rollback()
                    return@use forbidden
                }

                val deleted =
                    connection.prepareStatement(
                        "DELETE FROM users WHERE id = ?"
                    ).use { statement ->
                        statement.setObject(1, userId)
                        statement.executeUpdate()
                    }

                if (deleted != 1) {
                    connection.rollback()
                    return@use AdminDeleteUserResult.NOT_FOUND
                }

                connection.commit()
                deleteAvatarFile(target.avatarPath)
                AdminDeleteUserResult.DELETED

            } catch (error: Throwable) {
                runCatching {
                    connection.rollback()
                }
                throw error
            } finally {
                runCatching {
                    connection.autoCommit = true
                }
            }
        }

    private data class TargetUser(
        val email: String,
        val displayName: String?,
        val role: UserRole,
        val avatarPath: String?
    ) {
        val isRuntimeSmokeBot: Boolean
            get() {
                val normalizedEmail = email.trim().lowercase()

                return (
                    normalizedEmail.startsWith("runtime-smoke-") &&
                        normalizedEmail.endsWith("@cardyssey.de")
                    ) || displayName == "Cardyssey Runtime Smoke"
            }
    }

    private fun deleteAvatarFile(
        avatarPath: String?
    ) {
        if (
            avatarPath.isNullOrBlank() ||
            !avatarPath.matches(Regex("^[A-Za-z0-9._-]+$"))
        ) {
            return
        }

        val directory =
            File(
                System.getenv("AVATAR_DIR")
                    ?.takeIf(String::isNotBlank)
                    ?: "/data/avatars"
            )

        runCatching {
            File(directory, avatarPath).delete()
        }
    }
}
