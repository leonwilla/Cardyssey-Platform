package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import java.util.UUID

data class PublicFriendUser(
    val friendCode: String,
    val displayName: String?
)

data class FriendRequestRecord(
    val id: UUID,
    val user: PublicFriendUser,
    val createdAt: String
)

data class FriendRecord(
    val user: PublicFriendUser
)

enum class CreateFriendRequestResult {
    CREATED,
    USER_NOT_FOUND,
    SELF,
    ALREADY_EXISTS
}

class FriendshipRepository(
    internal val dataSource: HikariDataSource
) {

    fun searchUsers(
        currentUserId: UUID,
        query: String
    ): List<PublicFriendUser> {

        val q = query.trim()

        if (q.length < 2) {
            return emptyList()
        }

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    friend_code,
                    display_name
                FROM users
                WHERE id <> ?
                  AND disabled_at IS NULL
                  AND (
                      UPPER(friend_code) = UPPER(?)
                      OR display_name ILIKE ?
                  )
                ORDER BY
                    CASE
                        WHEN UPPER(friend_code) = UPPER(?)
                        THEN 0
                        ELSE 1
                    END,
                    display_name NULLS LAST
                LIMIT 20
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, currentUserId)
                statement.setString(2, q)
                statement.setString(3, "%$q%")
                statement.setString(4, q)

                statement.executeQuery().use { result ->

                    val users =
                        mutableListOf<PublicFriendUser>()

                    while (result.next()) {
                        users +=
                            PublicFriendUser(
                                friendCode =
                                    result.getString(
                                        "friend_code"
                                    ),
                                displayName =
                                    result.getString(
                                        "display_name"
                                    )
                            )
                    }

                    return users
                }
            }
        }
    }

    fun createRequest(
        requesterId: UUID,
        friendCode: String
    ): CreateFriendRequestResult {

        dataSource.connection.use { connection ->

            val addresseeId =
                connection.prepareStatement(
                    """
                    SELECT id
                    FROM users
                    WHERE UPPER(friend_code) = UPPER(?)
                      AND disabled_at IS NULL
                    LIMIT 1
                    """.trimIndent()
                ).use { statement ->

                    statement.setString(
                        1,
                        friendCode.trim()
                    )

                    statement.executeQuery().use { result ->
                        if (!result.next()) {
                            return CreateFriendRequestResult.USER_NOT_FOUND
                        }

                        UUID.fromString(
                            result.getString("id")
                        )
                    }
                }

            if (requesterId == addresseeId) {
                return CreateFriendRequestResult.SELF
            }

            val exists =
                connection.prepareStatement(
                    """
                    SELECT 1
                    FROM friendships
                    WHERE (
                        requester_id = ?
                        AND addressee_id = ?
                    )
                    OR (
                        requester_id = ?
                        AND addressee_id = ?
                    )
                    LIMIT 1
                    """.trimIndent()
                ).use { statement ->

                    statement.setObject(1, requesterId)
                    statement.setObject(2, addresseeId)
                    statement.setObject(3, addresseeId)
                    statement.setObject(4, requesterId)

                    statement.executeQuery().use {
                        it.next()
                    }
                }

            if (exists) {
                return CreateFriendRequestResult.ALREADY_EXISTS
            }

            connection.prepareStatement(
                """
                INSERT INTO friendships (
                    id,
                    requester_id,
                    addressee_id,
                    status
                )
                VALUES (?, ?, ?, 'PENDING')
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    UUID.randomUUID()
                )

                statement.setObject(
                    2,
                    requesterId
                )

                statement.setObject(
                    3,
                    addresseeId
                )

                statement.executeUpdate()
            }

            return CreateFriendRequestResult.CREATED
        }
    }

    fun incomingRequests(
        userId: UUID
    ): List<FriendRequestRecord> =
        requests(
            userId,
            incoming = true
        )

    fun outgoingRequests(
        userId: UUID
    ): List<FriendRequestRecord> =
        requests(
            userId,
            incoming = false
        )

    private fun requests(
        userId: UUID,
        incoming: Boolean
    ): List<FriendRequestRecord> {

        val ownerColumn =
            if (incoming) {
                "addressee_id"
            } else {
                "requester_id"
            }

        val otherColumn =
            if (incoming) {
                "requester_id"
            } else {
                "addressee_id"
            }

        val sql =
            """
            SELECT
                f.id,
                f.created_at,
                u.friend_code,
                u.display_name
            FROM friendships f
            JOIN users u
              ON u.id = f.$otherColumn
            WHERE f.$ownerColumn = ?
              AND f.status = 'PENDING'
              AND u.disabled_at IS NULL
            ORDER BY f.created_at DESC
            """.trimIndent()

        dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->

                statement.setObject(1, userId)

                statement.executeQuery().use { result ->

                    val requests =
                        mutableListOf<FriendRequestRecord>()

                    while (result.next()) {
                        requests +=
                            FriendRequestRecord(
                                id =
                                    UUID.fromString(
                                        result.getString("id")
                                    ),
                                user =
                                    PublicFriendUser(
                                        friendCode =
                                            result.getString(
                                                "friend_code"
                                            ),
                                        displayName =
                                            result.getString(
                                                "display_name"
                                            )
                                    ),
                                createdAt =
                                    result.getObject(
                                        "created_at"
                                    ).toString()
                            )
                    }

                    return requests
                }
            }
        }
    }

    fun acceptRequest(
        userId: UUID,
        requestId: UUID
    ): Boolean {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE friendships
                SET
                    status = 'ACCEPTED',
                    responded_at = NOW()
                WHERE id = ?
                  AND addressee_id = ?
                  AND status = 'PENDING'
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, requestId)
                statement.setObject(2, userId)

                return statement.executeUpdate() > 0
            }
        }
    }

    fun deletePendingRequest(
        userId: UUID,
        requestId: UUID
    ): Boolean {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                DELETE FROM friendships
                WHERE id = ?
                  AND status = 'PENDING'
                  AND (
                      requester_id = ?
                      OR addressee_id = ?
                  )
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, requestId)
                statement.setObject(2, userId)
                statement.setObject(3, userId)

                return statement.executeUpdate() > 0
            }
        }
    }

    fun friends(
        userId: UUID
    ): List<FriendRecord> {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    u.friend_code,
                    u.display_name
                FROM friendships f
                JOIN users u
                  ON u.id =
                    CASE
                        WHEN f.requester_id = ?
                        THEN f.addressee_id
                        ELSE f.requester_id
                    END
                WHERE f.status = 'ACCEPTED'
                  AND (
                      f.requester_id = ?
                      OR f.addressee_id = ?
                  )
                  AND u.disabled_at IS NULL
                ORDER BY
                    u.display_name NULLS LAST,
                    u.friend_code
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, userId)
                statement.setObject(2, userId)
                statement.setObject(3, userId)

                statement.executeQuery().use { result ->

                    val friends =
                        mutableListOf<FriendRecord>()

                    while (result.next()) {
                        friends +=
                            FriendRecord(
                                user =
                                    PublicFriendUser(
                                        friendCode =
                                            result.getString(
                                                "friend_code"
                                            ),
                                        displayName =
                                            result.getString(
                                                "display_name"
                                            )
                                    )
                            )
                    }

                    return friends
                }
            }
        }
    }
}

fun FriendshipRepository.removeFriend(
    userId: UUID,
    friendCode: String
): Boolean {

    dataSource.connection.use { connection ->
        connection.prepareStatement(
            """
            DELETE FROM friendships f
            USING users u
            WHERE f.status = 'ACCEPTED'
              AND UPPER(u.friend_code) = UPPER(?)
              AND (
                    (f.requester_id = ? AND f.addressee_id = u.id)
                 OR (f.addressee_id = ? AND f.requester_id = u.id)
              )
            """.trimIndent()
        ).use { statement ->

            statement.setString(1, friendCode)
            statement.setObject(2, userId)
            statement.setObject(3, userId)

            return statement.executeUpdate() > 0
        }
    }
}

fun FriendshipRepository.isFriend(
    userId: UUID,
    otherId: UUID
): Boolean {

    dataSource.connection.use { connection ->
        connection.prepareStatement(
            """
            SELECT 1
            FROM friendships
            WHERE status = 'ACCEPTED'
              AND (
                    (requester_id = ? AND addressee_id = ?)
                 OR (requester_id = ? AND addressee_id = ?)
              )
            LIMIT 1
            """.trimIndent()
        ).use { statement ->

            statement.setObject(1, userId)
            statement.setObject(2, otherId)
            statement.setObject(3, otherId)
            statement.setObject(4, userId)

            statement.executeQuery().use {
                return it.next()
            }
        }
    }
}

fun FriendshipRepository.findUserByFriendCode(
    friendCode: String
): Pair<UUID, PublicFriendUser>? {

    dataSource.connection.use { connection ->
        connection.prepareStatement(
            """
            SELECT
                id,
                friend_code,
                display_name
            FROM users
            WHERE UPPER(friend_code) = UPPER(?)
              AND disabled_at IS NULL
            LIMIT 1
            """.trimIndent()
        ).use { statement ->

            statement.setString(1, friendCode.trim())

            statement.executeQuery().use { result ->
                if (!result.next()) {
                    return null
                }

                return Pair(
                    UUID.fromString(
                        result.getString("id")
                    ),
                    PublicFriendUser(
                        friendCode =
                            result.getString("friend_code"),
                        displayName =
                            result.getString("display_name")
                    )
                )
            }
        }
    }
}
