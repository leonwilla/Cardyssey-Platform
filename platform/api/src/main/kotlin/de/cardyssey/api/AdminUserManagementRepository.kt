package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
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
                        SELECT email, role
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
                                result.getString("email") to
                                    (UserRole.parse(result.getString("role")) ?: UserRole.USER)
                            }
                        }
                    }

                if (target == null) {
                    connection.rollback()
                    return@use AdminDeleteUserResult.NOT_FOUND
                }

                val (email, role) = target

                val forbidden =
                    when {
                        userId == actorUserId ->
                            AdminDeleteUserResult.SELF_FORBIDDEN

                        role == UserRole.FOUNDER ->
                            AdminDeleteUserResult.FOUNDER_FORBIDDEN

                        isRuntimeSmokeBotEmail(email) ->
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

                if (deleted == 1) {
                    connection.commit()
                    AdminDeleteUserResult.DELETED
                } else {
                    connection.rollback()
                    AdminDeleteUserResult.NOT_FOUND
                }
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
}
