package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.response.respondTextWriter
import io.ktor.server.routing.Route
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.patch
import io.ktor.server.routing.post
import io.ktor.server.routing.route
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.filter
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import java.sql.Timestamp
import java.time.Instant
import java.util.UUID

@Serializable
data class GroupChatMessageResponse(
    val id: String,
    val senderFriendCode: String,
    val senderDisplayName: String?,
    val body: String,
    val objectType: String? = null,
    val objectPayload: JsonElement? = null,
    val createdAt: String
)

@Serializable
data class GroupChatSummaryResponse(
    val id: String,
    val name: String,
    val imageUrl: String? = null,
    val memberCount: Int,
    val role: String,
    val lastMessage: GroupChatMessageResponse?,
    val unreadCount: Int
)

@Serializable
data class GroupChatMemberResponse(
    val friendCode: String,
    val displayName: String?,
    val role: String
)

@Serializable
data class GroupChatDetailResponse(
    val id: String,
    val name: String,
    val imageUrl: String?,
    val role: String,
    val members: List<GroupChatMemberResponse>
)

@Serializable
data class CreateGroupChatRequest(
    val name: String,
    val memberFriendCodes: List<String>
)

@Serializable
data class UpdateGroupChatRequest(
    val name: String? = null,
    val imageUrl: String? = null,
    val clearImage: Boolean = false
)

@Serializable
data class AddGroupMemberRequest(val friendCode: String)

@Serializable
data class UpdateGroupMemberRoleRequest(val role: String)

@Serializable
data class SendGroupChatMessageRequest(
    val body: String = "",
    val objectType: String? = null,
    val objectPayload: JsonElement? = null
)

@Serializable
data class GroupChatEvent(
    val type: String,
    val groupId: String,
    val message: GroupChatMessageResponse? = null
)

class GroupChatRepository(
    private val dataSource: HikariDataSource,
    private val friendships: FriendshipRepository
) {
    private val events =
        MutableSharedFlow<GroupChatEvent>(
            extraBufferCapacity = 256
        )

    fun eventFlow() = events
    fun groups(userId: UUID): List<GroupChatSummaryResponse> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT g.id, g.name, g.image_url, self.role,
                       COUNT(DISTINCT all_members.user_id) AS member_count,
                       self.last_read_at,
                       (SELECT COUNT(*) FROM chat_group_messages um
                        WHERE um.group_id = g.id
                          AND um.sender_id <> ?
                          AND um.created_at > self.last_read_at) AS unread_count
                FROM chat_groups g
                JOIN chat_group_members self ON self.group_id = g.id AND self.user_id = ?
                JOIN chat_group_members all_members ON all_members.group_id = g.id
                GROUP BY g.id, g.name, g.image_url, self.role, self.last_read_at, g.updated_at
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
                                    imageUrl = result.getString("image_url"),
                                    memberCount = result.getInt("member_count"),
                                    role = result.getString("role"),
                                    lastMessage = latestMessage(id),
                                    unreadCount = result.getInt("unread_count")
                                )
                            )
                        }
                    }
                }
            }
        }

    fun create(userId: UUID, name: String, memberFriendCodes: List<String>): GroupChatSummaryResponse? {
        val cleanName = name.trim().replace(Regex("\\s+"), " ")
        val codes = memberFriendCodes.map(String::trim).filter(String::isNotBlank).distinct()
        if (cleanName.length !in 2..60 || codes.isEmpty() || codes.size > 19) return null

        val members = codes.mapNotNull { code ->
            friendships.findUserByFriendCode(code)?.takeIf { friendships.isFriend(userId, it.first) }
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
        return GroupChatSummaryResponse(id.toString(), cleanName, null, members.size + 1, "OWNER", null, 0)
    }

    fun detail(userId: UUID, groupId: UUID): GroupChatDetailResponse? {
        val role = memberRole(userId, groupId) ?: return null
        return dataSource.connection.use { connection ->
            val header = connection.prepareStatement(
                "SELECT name, image_url FROM chat_groups WHERE id = ?"
            ).use { s ->
                s.setObject(1, groupId)
                s.executeQuery().use { rs ->
                    if (!rs.next()) return null
                    rs.getString("name") to rs.getString("image_url")
                }
            }
            val members = connection.prepareStatement(
                """
                SELECT u.friend_code, u.display_name, m.role
                FROM chat_group_members m
                JOIN users u ON u.id = m.user_id
                WHERE m.group_id = ?
                ORDER BY CASE m.role WHEN 'OWNER' THEN 0 WHEN 'ADMIN' THEN 1 ELSE 2 END,
                         LOWER(COALESCE(u.display_name, u.friend_code))
                """.trimIndent()
            ).use { s ->
                s.setObject(1, groupId)
                s.executeQuery().use { rs ->
                    buildList {
                        while (rs.next()) {
                            add(
                                GroupChatMemberResponse(
                                    rs.getString("friend_code"),
                                    rs.getString("display_name"),
                                    rs.getString("role")
                                )
                            )
                        }
                    }
                }
            }
            GroupChatDetailResponse(groupId.toString(), header.first, header.second, role, members)
        }
    }

    fun update(userId: UUID, groupId: UUID, request: UpdateGroupChatRequest): Boolean {
        if (memberRole(userId, groupId) !in setOf("OWNER", "ADMIN")) return false
        val cleanName = request.name?.trim()?.replace(Regex("\\s+"), " ")
        if (cleanName != null && cleanName.length !in 2..60) return false
        val image = request.imageUrl?.trim()?.takeIf(String::isNotBlank)
        if (image != null && image.length > 1000) return false

        return dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE chat_groups
                SET name = COALESCE(?, name),
                    image_url = CASE WHEN ? THEN NULL ELSE COALESCE(?, image_url) END,
                    updated_at = NOW()
                WHERE id = ?
                """.trimIndent()
            ).use { s ->
                s.setString(1, cleanName)
                s.setBoolean(2, request.clearImage)
                s.setString(3, image)
                s.setObject(4, groupId)
                s.executeUpdate() > 0
            }
        }
    }

    fun addMember(actorId: UUID, groupId: UUID, friendCode: String): Boolean {
        if (memberRole(actorId, groupId) !in setOf("OWNER", "ADMIN")) return false
        val target = friendships.findUserByFriendCode(friendCode.trim()) ?: return false
        if (!friendships.isFriend(actorId, target.first)) return false
        return dataSource.connection.use { connection ->
            val count = connection.prepareStatement(
                "SELECT COUNT(*) FROM chat_group_members WHERE group_id = ?"
            ).use { s ->
                s.setObject(1, groupId)
                s.executeQuery().use { rs -> rs.next(); rs.getInt(1) }
            }
            if (count >= 20) return false
            connection.prepareStatement(
                "INSERT INTO chat_group_members (group_id, user_id, role) VALUES (?, ?, 'MEMBER') ON CONFLICT DO NOTHING"
            ).use { s ->
                s.setObject(1, groupId)
                s.setObject(2, target.first)
                s.executeUpdate() > 0
            }
        }
    }

    fun updateMemberRole(actorId: UUID, groupId: UUID, friendCode: String, role: String): Boolean {
        if (memberRole(actorId, groupId) != "OWNER") return false
        val cleanRole = role.trim().uppercase()
        if (cleanRole !in setOf("ADMIN", "MEMBER")) return false
        val target = friendships.findUserByFriendCode(friendCode.trim()) ?: return false
        return dataSource.connection.use { connection ->
            connection.prepareStatement(
                "UPDATE chat_group_members SET role = ? WHERE group_id = ? AND user_id = ? AND role <> 'OWNER'"
            ).use { s ->
                s.setString(1, cleanRole)
                s.setObject(2, groupId)
                s.setObject(3, target.first)
                s.executeUpdate() > 0
            }
        }
    }

    fun removeMember(actorId: UUID, groupId: UUID, friendCode: String): Boolean {
        val actorRole = memberRole(actorId, groupId) ?: return false
        val target = friendships.findUserByFriendCode(friendCode.trim()) ?: return false
        val targetRole = memberRole(target.first, groupId) ?: return false
        val allowed = actorRole == "OWNER" && targetRole != "OWNER" ||
            actorRole == "ADMIN" && targetRole == "MEMBER"
        if (!allowed) return false
        return deleteMembership(groupId, target.first)
    }

    fun leave(userId: UUID, groupId: UUID): Boolean {
        val role = memberRole(userId, groupId) ?: return false
        return dataSource.connection.use { connection ->
            connection.autoCommit = false
            try {
                if (role == "OWNER") {
                    val nextOwner = connection.prepareStatement(
                        """
                        SELECT user_id
                        FROM chat_group_members
                        WHERE group_id = ? AND user_id <> ?
                        ORDER BY CASE role WHEN 'ADMIN' THEN 0 ELSE 1 END, joined_at ASC
                        LIMIT 1
                        """.trimIndent()
                    ).use { s ->
                        s.setObject(1, groupId)
                        s.setObject(2, userId)
                        s.executeQuery().use { rs ->
                            if (rs.next()) rs.getObject("user_id", UUID::class.java) else null
                        }
                    }
                    if (nextOwner == null) {
                        connection.prepareStatement("DELETE FROM chat_groups WHERE id = ?").use { s ->
                            s.setObject(1, groupId)
                            s.executeUpdate()
                        }
                        connection.commit()
                        return true
                    }
                    connection.prepareStatement(
                        "UPDATE chat_group_members SET role = 'OWNER' WHERE group_id = ? AND user_id = ?"
                    ).use { s ->
                        s.setObject(1, groupId)
                        s.setObject(2, nextOwner)
                        s.executeUpdate()
                    }
                    connection.prepareStatement(
                        "UPDATE chat_groups SET owner_id = ?, updated_at = NOW() WHERE id = ?"
                    ).use { s ->
                        s.setObject(1, nextOwner)
                        s.setObject(2, groupId)
                        s.executeUpdate()
                    }
                }

                connection.prepareStatement(
                    "DELETE FROM chat_group_members WHERE group_id = ? AND user_id = ?"
                ).use { s ->
                    s.setObject(1, groupId)
                    s.setObject(2, userId)
                    s.executeUpdate()
                }
                connection.commit()
                true
            } catch (_: Throwable) {
                connection.rollback()
                false
            } finally {
                connection.autoCommit = true
            }
        }
    }

    fun messages(userId: UUID, groupId: UUID, before: Instant?, limit: Int): List<GroupChatMessageResponse>? {
        if (memberRole(userId, groupId) == null) return null
        val safeLimit = limit.coerceIn(1, 100)
        val messages = dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT m.id, u.friend_code, u.display_name, m.body, m.object_type,
                       m.object_payload, m.created_at
                FROM chat_group_messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.group_id = ?
                  AND (? IS NULL OR m.created_at < ?)
                ORDER BY m.created_at DESC, m.id DESC
                LIMIT ?
                """.trimIndent()
            ).use { s ->
                s.setObject(1, groupId)
                s.setTimestamp(2, before?.let(Timestamp::from))
                s.setTimestamp(3, before?.let(Timestamp::from))
                s.setInt(4, safeLimit)
                s.executeQuery().use { result ->
                    buildList {
                        while (result.next()) add(result.toGroupMessage())
                    }.reversed()
                }
            }
        }
        markRead(userId, groupId)
        return messages
    }

    fun send(userId: UUID, groupId: UUID, request: SendGroupChatMessageRequest): GroupChatMessageResponse? {
        if (memberRole(userId, groupId) == null) return null
        val clean = request.body.trim()
        val objectType = request.objectType?.trim()?.uppercase()?.takeIf(String::isNotBlank)
        val allowedObjectTypes = setOf("CARD", "SET", "WISHLIST_CARD", "SHOWCASE", "TRADE_OFFER")
        if (clean.length > 2000 || (clean.isBlank() && objectType == null)) return null
        if (objectType != null && (objectType !in allowedObjectTypes || request.objectPayload == null)) return null

        return dataSource.connection.use { connection ->
            val id = UUID.randomUUID()
            val response = connection.prepareStatement(
                """
                INSERT INTO chat_group_messages
                    (id, group_id, sender_id, body, object_type, object_payload)
                VALUES (?, ?, ?, ?, ?, ?::jsonb)
                RETURNING created_at
                """.trimIndent()
            ).use { s ->
                s.setObject(1, id)
                s.setObject(2, groupId)
                s.setObject(3, userId)
                s.setString(4, clean)
                s.setString(5, objectType)
                s.setString(6, request.objectPayload?.let { Json.encodeToString(it) })
                s.executeQuery().use { result ->
                    if (!result.next()) return null
                    GroupChatMessageResponse(
                        id = id.toString(),
                        senderFriendCode = userValue(userId, "friend_code").orEmpty(),
                        senderDisplayName = userValue(userId, "display_name"),
                        body = clean,
                        objectType = objectType,
                        objectPayload = request.objectPayload,
                        createdAt = result.getObject("created_at").toString()
                    )
                }
            }
            connection.prepareStatement("UPDATE chat_groups SET updated_at = NOW() WHERE id = ?").use { s ->
                s.setObject(1, groupId)
                s.executeUpdate()
            }
            events.tryEmit(
                GroupChatEvent(
                    type = "MESSAGE_CREATED",
                    groupId = groupId.toString(),
                    message = response
                )
            )
            response
        }
    }

    private fun latestMessage(groupId: UUID): GroupChatMessageResponse? =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT m.id, u.friend_code, u.display_name, m.body, m.object_type,
                       m.object_payload, m.created_at
                FROM chat_group_messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.group_id = ?
                ORDER BY m.created_at DESC
                LIMIT 1
                """.trimIndent()
            ).use { s ->
                s.setObject(1, groupId)
                s.executeQuery().use { result -> if (result.next()) result.toGroupMessage() else null }
            }
        }

    private fun markRead(userId: UUID, groupId: UUID) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                "UPDATE chat_group_members SET last_read_at = NOW() WHERE group_id = ? AND user_id = ?"
            ).use { s ->
                s.setObject(1, groupId)
                s.setObject(2, userId)
                s.executeUpdate()
            }
        }
    }

    private fun memberRole(userId: UUID, groupId: UUID): String? =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                "SELECT role FROM chat_group_members WHERE group_id = ? AND user_id = ?"
            ).use { s ->
                s.setObject(1, groupId)
                s.setObject(2, userId)
                s.executeQuery().use { rs -> if (rs.next()) rs.getString("role") else null }
            }
        }

    private fun deleteMembership(groupId: UUID, userId: UUID): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                "DELETE FROM chat_group_members WHERE group_id = ? AND user_id = ?"
            ).use { s ->
                s.setObject(1, groupId)
                s.setObject(2, userId)
                s.executeUpdate() > 0
            }
        }

    private fun userValue(userId: UUID, column: String): String? {
        require(column == "friend_code" || column == "display_name")
        return dataSource.connection.use { connection ->
            connection.prepareStatement("SELECT $column FROM users WHERE id = ?").use { s ->
                s.setObject(1, userId)
                s.executeQuery().use { result -> if (result.next()) result.getString(column) else null }
            }
        }
    }

    private fun java.sql.ResultSet.toGroupMessage() =
        GroupChatMessageResponse(
            id = getString("id"),
            senderFriendCode = getString("friend_code"),
            senderDisplayName = getString("display_name"),
            body = getString("body"),
            objectType = getString("object_type"),
            objectPayload = getString("object_payload")?.let {
                runCatching { Json.parseToJsonElement(it) }.getOrNull()
            },
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
                    ?: return@post call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_group_or_members"))
                call.respond(HttpStatusCode.Created, group)
            }

            get("/events") {
                val userId = call.authenticatedUserId()
                    ?: return@get call.respond(HttpStatusCode.Unauthorized)
                val groupFilter = call.request.queryParameters["groupId"]

                call.respondTextWriter(ContentType.Text.EventStream) {
                    repository.eventFlow()
                        .filter { event ->
                            val groupId = runCatching {
                                UUID.fromString(event.groupId)
                            }.getOrNull()

                            groupId != null &&
                                repository.detail(userId, groupId) != null &&
                                (groupFilter == null || event.groupId == groupFilter)
                        }
                        .collect { event ->
                            write("event: group\\n")
                            write("data: " + Json.encodeToString(event) + "\\n\\n")
                            flush()
                        }
                }
            }

            route("/{groupId}") {
                get {
                    val userId = call.authenticatedUserId()
                        ?: return@get call.respond(HttpStatusCode.Unauthorized)
                    val groupId = call.parameters["groupId"]?.toUuid()
                        ?: return@get call.respond(HttpStatusCode.BadRequest)
                    val detail = repository.detail(userId, groupId)
                        ?: return@get call.respond(HttpStatusCode.Forbidden)
                    call.respond(detail)
                }

                patch {
                    val userId = call.authenticatedUserId()
                        ?: return@patch call.respond(HttpStatusCode.Unauthorized)
                    val groupId = call.parameters["groupId"]?.toUuid()
                        ?: return@patch call.respond(HttpStatusCode.BadRequest)
                    val ok = repository.update(userId, groupId, call.receive<UpdateGroupChatRequest>())
                    call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.Forbidden)
                }

                delete("/leave") {
                    val userId = call.authenticatedUserId()
                        ?: return@delete call.respond(HttpStatusCode.Unauthorized)
                    val groupId = call.parameters["groupId"]?.toUuid()
                        ?: return@delete call.respond(HttpStatusCode.BadRequest)
                    val ok = repository.leave(userId, groupId)
                    call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.BadRequest)
                }

                post("/members") {
                    val userId = call.authenticatedUserId()
                        ?: return@post call.respond(HttpStatusCode.Unauthorized)
                    val groupId = call.parameters["groupId"]?.toUuid()
                        ?: return@post call.respond(HttpStatusCode.BadRequest)
                    val ok = repository.addMember(userId, groupId, call.receive<AddGroupMemberRequest>().friendCode)
                    call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.BadRequest)
                }

                patch("/members/{friendCode}") {
                    val userId = call.authenticatedUserId()
                        ?: return@patch call.respond(HttpStatusCode.Unauthorized)
                    val groupId = call.parameters["groupId"]?.toUuid()
                        ?: return@patch call.respond(HttpStatusCode.BadRequest)
                    val code = call.parameters["friendCode"] ?: return@patch call.respond(HttpStatusCode.BadRequest)
                    val request = call.receive<UpdateGroupMemberRoleRequest>()
                    val ok = repository.updateMemberRole(userId, groupId, code, request.role)
                    call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.Forbidden)
                }

                delete("/members/{friendCode}") {
                    val userId = call.authenticatedUserId()
                        ?: return@delete call.respond(HttpStatusCode.Unauthorized)
                    val groupId = call.parameters["groupId"]?.toUuid()
                        ?: return@delete call.respond(HttpStatusCode.BadRequest)
                    val code = call.parameters["friendCode"] ?: return@delete call.respond(HttpStatusCode.BadRequest)
                    val ok = repository.removeMember(userId, groupId, code)
                    call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.Forbidden)
                }

                route("/messages") {
                    get {
                        val userId = call.authenticatedUserId()
                            ?: return@get call.respond(HttpStatusCode.Unauthorized)
                        val groupId = call.parameters["groupId"]?.toUuid()
                            ?: return@get call.respond(HttpStatusCode.BadRequest)
                        val before = call.request.queryParameters["before"]?.let {
                            runCatching { Instant.parse(it) }.getOrNull()
                        }
                        val limit = call.request.queryParameters["limit"]?.toIntOrNull() ?: 50
                        val messages = repository.messages(userId, groupId, before, limit)
                            ?: return@get call.respond(HttpStatusCode.Forbidden)
                        call.respond(messages)
                    }

                    post {
                        val userId = call.authenticatedUserId()
                            ?: return@post call.respond(HttpStatusCode.Unauthorized)
                        val groupId = call.parameters["groupId"]?.toUuid()
                            ?: return@post call.respond(HttpStatusCode.BadRequest)
                        val message = repository.send(userId, groupId, call.receive<SendGroupChatMessageRequest>())
                            ?: return@post call.respond(HttpStatusCode.BadRequest)
                        call.respond(HttpStatusCode.Created, message)
                    }
                }
            }
        }
    }
}

private fun String.toUuid(): UUID? = runCatching { UUID.fromString(this) }.getOrNull()
