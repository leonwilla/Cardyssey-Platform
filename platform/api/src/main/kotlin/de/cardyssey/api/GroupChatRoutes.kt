package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.route
import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
data class GroupChatMessageResponse(
    val id: String,
    val senderFriendCode: String,
    val senderDisplayName: String?,
    val body: String,
    val createdAt: String
)

@Serializable
data class GroupChatSummaryResponse(
    val id: String,
    val name: String,
    val memberCount: Int,
    val lastMessage: GroupChatMessageResponse?,
    val unreadCount: Int
)

@Serializable
data class CreateGroupChatRequest(
    val name: String,
    val memberFriendCodes: List<String>
)

class GroupChatRepository(
    private val dataSource: HikariDataSource,
    private val friendships: FriendshipRepository
) {
    fun groups(userId: UUID): List<GroupChatSummaryResponse> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT g.id, g.name, COUNT(DISTINCT all_members.user_id) AS member_count,
                       self.last_read_at,
                       (SELECT COUNT(*) FROM chat_group_messages um
                        WHERE um.group_id = g.id
                          AND um.sender_id <> ?
                          AND um.created_at > self.last_read_at) AS unread_count
                FROM chat_groups g
                JOIN chat_group_members self ON self.group_id = g.id AND self.user_id = ?
                JOIN chat_group_members all_members ON all_members.group_id = g.id
                GROUP BY g.id, g.name, self.last_read_at, g.updated_at
                ORDER BY g.updated_at DESC
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)
                statement.setObject(2, userId)
                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            val id = UUID.fromString(result.getString("id"))
                            add(
                                GroupChatSummaryResponse(
                                    id = id.toString(),
                                    name = result.getString("name"),
                                    memberCount = result.getInt("member_count"),
                                    lastMessage = latestMessage(id),
                                    unreadCount = result.getInt("unread_count")
                                )
                            )
                        }
                    }
                }
            }
        }

    fun create(
        userId: UUID,
        name: String,
        memberFriendCodes: List<String>
    ): GroupChatSummaryResponse? {
        val cleanName = name.trim().replace(Regex("\\s+"), " ")
        val codes = memberFriendCodes.map(String::trim).filter(String::isNotBlank).distinct()
        if (cleanName.length !in 2..60 || codes.isEmpty() || codes.size > 19) return null

        val members = codes.mapNotNull { code ->
            friendships.findUserByFriendCode(code)?.takeIf {
                friendships.isFriend(userId, it.first)
            }
        }
        if (members.size != codes.size) return null

        val id = UUID.randomUUID()
        dataSource.connection.use { connection ->
            connection.autoCommit = false
            try {
                connection.prepareStatement(
                    "INSERT INTO chat_groups (id, name, owner_id) VALUES (?, ?, ?)"
                ).use { s ->
                    s.setObject(1, id)
                    s.setString(2, cleanName)
                    s.setObject(3, userId)
                    s.executeUpdate()
                }
                connection.prepareStatement(
                    "INSERT INTO chat_group_members (group_id, user_id, role) VALUES (?, ?, ?)"
                ).use { s ->
                    s.setObject(1, id)
                    s.setObject(2, userId)
                    s.setString(3, "OWNER")
                    s.executeUpdate()
                    members.forEach { member ->
                        s.setObject(1, id)
                        s.setObject(2, member.first)
                        s.setString(3, "MEMBER")
                        s.addBatch()
                    }
                    s.executeBatch()
                }
                connection.commit()
            } catch (error: Throwable) {
                connection.rollback()
                throw error
            } finally {
                connection.autoCommit = true
            }
        }

        return GroupChatSummaryResponse(id.toString(), cleanName, members.size + 1, null, 0)
    }

    fun messages(userId: UUID, groupId: UUID): List<GroupChatMessageResponse>? {
        if (!isMember(userId, groupId)) return null

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                "UPDATE chat_group_members SET last_read_at = NOW() WHERE group_id = ? AND user_id = ?"
            ).use { s ->
                s.setObject(1, groupId)
                s.setObject(2, userId)
                s.executeUpdate()
            }

            return connection.prepareStatement(
                """
                SELECT m.id, u.friend_code, u.display_name, m.body, m.created_at
                FROM chat_group_messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.group_id = ?
                ORDER BY m.created_at DESC
                LIMIT 150
                """.trimIndent()
            ).use { s ->
                s.setObject(1, groupId)
                s.executeQuery().use { result ->
                    buildList {
                        while (result.next()) add(result.toGroupMessage())
                    }.reversed()
                }
            }
        }
    }

    fun send(userId: UUID, groupId: UUID, body: String): GroupChatMessageResponse? {
        if (!isMember(userId, groupId)) return null
        val clean = body.trim()
        if (clean.isBlank() || clean.length > 2000) return null

        dataSource.connection.use { connection ->
            val response = connection.prepareStatement(
                """
                INSERT INTO chat_group_messages (id, group_id, sender_id, body)
                VALUES (?, ?, ?, ?)
                RETURNING id, created_at
                """.trimIndent()
            ).use { s ->
                val id = UUID.randomUUID()
                s.setObject(1, id)
                s.setObject(2, groupId)
                s.setObject(3, userId)
                s.setString(4, clean)
                s.executeQuery().use { result ->
                    if (!result.next()) return null
                    GroupChatMessageResponse(
                        id = id.toString(),
                        senderFriendCode = userValue(userId, "friend_code").orEmpty(),
                        senderDisplayName = userValue(userId, "display_name"),
                        body = clean,
                        createdAt = result.getObject("created_at").toString()
                    )
                }
            }

            connection.prepareStatement(
                "UPDATE chat_groups SET updated_at = NOW() WHERE id = ?"
            ).use { s ->
                s.setObject(1, groupId)
                s.executeUpdate()
            }

            return response
        }
    }

    private fun latestMessage(groupId: UUID): GroupChatMessageResponse? =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT m.id, u.friend_code, u.display_name, m.body, m.created_at
                FROM chat_group_messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.group_id = ?
                ORDER BY m.created_at DESC
                LIMIT 1
                """.trimIndent()
            ).use { s ->
                s.setObject(1, groupId)
                s.executeQuery().use { result ->
                    if (result.next()) result.toGroupMessage() else null
                }
            }
        }

    private fun isMember(userId: UUID, groupId: UUID): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                "SELECT 1 FROM chat_group_members WHERE group_id = ? AND user_id = ?"
            ).use { s ->
                s.setObject(1, groupId)
                s.setObject(2, userId)
                s.executeQuery().use { it.next() }
            }
        }

    private fun userValue(userId: UUID, column: String): String? {
        require(column == "friend_code" || column == "display_name")
        return dataSource.connection.use { connection ->
            connection.prepareStatement("SELECT " + column + " FROM users WHERE id = ?").use { s ->
                s.setObject(1, userId)
                s.executeQuery().use { result ->
                    if (result.next()) result.getString(column) else null
                }
            }
        }
    }

    private fun java.sql.ResultSet.toGroupMessage() =
        GroupChatMessageResponse(
            id = getString("id"),
            senderFriendCode = getString("friend_code"),
            senderDisplayName = getString("display_name"),
            body = getString("body"),
            createdAt = getObject("created_at").toString()
        )
}

fun Route.groupChatRoutes(repository: GroupChatRepository) {
    authenticate("auth-jwt") {
        route("/api/v1/chat/groups") {
            get {
                val userId = call.authenticatedUserId()
                    ?: return@get call.respond(HttpStatusCode.Unauthorized)
                call.respond(repository.groups(userId))
            }

            post {
                val userId = call.authenticatedUserId()
                    ?: return@post call.respond(HttpStatusCode.Unauthorized)
                val request = call.receive<CreateGroupChatRequest>()
                val group = repository.create(userId, request.name, request.memberFriendCodes)
                    ?: return@post call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_group_or_members")
                    )
                call.respond(HttpStatusCode.Created, group)
            }

            route("/{groupId}/messages") {
                get {
                    val userId = call.authenticatedUserId()
                        ?: return@get call.respond(HttpStatusCode.Unauthorized)
                    val groupId = call.parameters["groupId"]
                        ?.let { runCatching { UUID.fromString(it) }.getOrNull() }
                        ?: return@get call.respond(HttpStatusCode.BadRequest)

                    val messages = repository.messages(userId, groupId)
                        ?: return@get call.respond(HttpStatusCode.Forbidden)
                    call.respond(messages)
                }

                post {
                    val userId = call.authenticatedUserId()
                        ?: return@post call.respond(HttpStatusCode.Unauthorized)
                    val groupId = call.parameters["groupId"]
                        ?.let { runCatching { UUID.fromString(it) }.getOrNull() }
                        ?: return@post call.respond(HttpStatusCode.BadRequest)
                    val request = call.receive<SendChatMessageRequest>()

                    val message = repository.send(userId, groupId, request.body)
                        ?: return@post call.respond(HttpStatusCode.BadRequest)
                    call.respond(HttpStatusCode.Created, message)
                }
            }
        }
    }
}
