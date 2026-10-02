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
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.collect
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import java.time.Instant
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

@Serializable
data class ChatObjectPayload(
    val type: String,
    val payload: JsonElement
)

@Serializable
data class CommunityRoomResponse(
    val id: String,
    val slug: String,
    val name: String,
    val roomType: String,
    val languageCode: String,
    val setId: String? = null,
    val setName: String? = null,
    val unreadCount: Int = 0
)

@Serializable
data class CommunityMessageResponse(
    val id: String,
    val roomId: String,
    val senderFriendCode: String,
    val senderDisplayName: String?,
    val body: String,
    val objectType: String? = null,
    val objectPayload: JsonElement? = null,
    val deleted: Boolean = false,
    val createdAt: String
)

@Serializable
data class SendCommunityMessageRequest(
    val body: String = "",
    val objectType: String? = null,
    val objectPayload: JsonElement? = null
)

@Serializable
data class EnsureSetRoomRequest(
    val setId: String,
    val setName: String,
    val languageCode: String
)

@Serializable
data class ReportCommunityMessageRequest(val reason: String)

@Serializable
data class BlockUserRequest(val friendCode: String)

@Serializable
data class ModerateChatRequest(
    val action: String,
    val targetFriendCode: String? = null,
    val messageId: String? = null,
    val reason: String? = null,
    val durationMinutes: Long? = null
)

@Serializable
data class CommunityEvent(
    val type: String,
    val roomId: String,
    val message: CommunityMessageResponse? = null
)

private class ChatSendGuard {
    private data class SendState(
        val timestamps: ArrayDeque<Long> = ArrayDeque(),
        var lastFingerprint: String = "",
        var duplicateCount: Int = 0
    )

    private val states = ConcurrentHashMap<UUID, SendState>()

    fun allow(userId: UUID, body: String, objectType: String?): Boolean {
        val now = System.currentTimeMillis()
        val state = states.computeIfAbsent(userId) { SendState() }
        synchronized(state) {
            while (state.timestamps.isNotEmpty() && now - state.timestamps.first() > 60_000L) {
                state.timestamps.removeFirst()
            }
            if (state.timestamps.size >= 20) return false

            val fingerprint = body.trim().lowercase() + "|" + objectType.orEmpty()
            if (fingerprint == state.lastFingerprint) {
                state.duplicateCount += 1
                if (state.duplicateCount > 3) return false
            } else {
                state.lastFingerprint = fingerprint
                state.duplicateCount = 1
            }
            state.timestamps.addLast(now)
            return true
        }
    }
}

class CommunityChatRepository(
    private val dataSource: HikariDataSource
) {
    private val events = MutableSharedFlow<CommunityEvent>(extraBufferCapacity = 256)
    private val sendGuard = ChatSendGuard()

    fun eventFlow() = events

    fun rooms(userId: UUID, language: String?, query: String?): List<CommunityRoomResponse> {
        val lang = language?.normalizeChatLanguage()
        val search = query?.trim()?.takeIf(String::isNotBlank)
        return dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT r.id, r.slug, r.name, r.room_type, r.language_code, r.set_id, r.set_name,
                       COALESCE((
                           SELECT COUNT(*)
                           FROM community_messages m
                           LEFT JOIN community_room_reads rr
                             ON rr.room_id = r.id AND rr.user_id = ?
                           WHERE m.room_id = r.id
                             AND m.deleted_at IS NULL
                             AND m.sender_id <> ?
                             AND m.created_at > COALESCE(rr.last_read_at, TIMESTAMPTZ '1970-01-01')
                       ), 0) AS unread_count
                FROM community_rooms r
                WHERE (? IS NULL OR r.language_code = ?)
                  AND (? IS NULL OR LOWER(r.name) LIKE LOWER(?))
                ORDER BY
                    CASE WHEN r.slug LIKE 'lounge-%' THEN 0 ELSE 1 END,
                    r.last_activity_at DESC,
                    r.name ASC
                LIMIT 250
                """.trimIndent()
            ).use { s ->
                s.setObject(1, userId)
                s.setObject(2, userId)
                s.setString(3, lang)
                s.setString(4, lang)
                s.setString(5, search)
                s.setString(6, search?.let { "%$it%" })
                s.executeQuery().use { rs ->
                    buildList {
                        while (rs.next()) {
                            add(
                                CommunityRoomResponse(
                                    id = rs.getString("id"),
                                    slug = rs.getString("slug"),
                                    name = rs.getString("name"),
                                    roomType = rs.getString("room_type"),
                                    languageCode = rs.getString("language_code"),
                                    setId = rs.getString("set_id"),
                                    setName = rs.getString("set_name"),
                                    unreadCount = rs.getInt("unread_count")
                                )
                            )
                        }
                    }
                }
            }
        }
    }

    fun ensureSetRoom(request: EnsureSetRoomRequest): CommunityRoomResponse? {
        val setId = request.setId.trim().takeIf { it.isNotBlank() } ?: return null
        val setName = request.setName.trim().takeIf { it.isNotBlank() } ?: return null
        val language = request.languageCode.normalizeChatLanguage() ?: return null
        val slug = "set-" + setId.lowercase().replace(Regex("[^a-z0-9]+"), "-").trim('-') + "-$language"
        val id = UUID.randomUUID()

        return dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO community_rooms (id, slug, name, room_type, language_code, set_id, set_name)
                VALUES (?, ?, ?, 'SET', ?, ?, ?)
                ON CONFLICT (slug) DO UPDATE SET set_name = EXCLUDED.set_name
                RETURNING id, slug, name, room_type, language_code, set_id, set_name
                """.trimIndent()
            ).use { s ->
                s.setObject(1, id)
                s.setString(2, slug)
                s.setString(3, setName)
                s.setString(4, language)
                s.setString(5, setId)
                s.setString(6, setName)
                s.executeQuery().use { rs ->
                    if (!rs.next()) return null
                    CommunityRoomResponse(
                        id = rs.getString("id"),
                        slug = rs.getString("slug"),
                        name = rs.getString("name"),
                        roomType = rs.getString("room_type"),
                        languageCode = rs.getString("language_code"),
                        setId = rs.getString("set_id"),
                        setName = rs.getString("set_name")
                    )
                }
            }
        }
    }

    fun messages(userId: UUID, roomId: UUID, before: Instant?, limit: Int): List<CommunityMessageResponse>? {
        if (!roomExists(roomId)) return null
        val safeLimit = limit.coerceIn(1, 100)
        val result = dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT m.id, m.room_id, u.friend_code, u.display_name, m.body,
                       m.object_type, m.object_payload, m.deleted_at, m.created_at
                FROM community_messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.room_id = ?
                  AND (? IS NULL OR m.created_at < ?)
                  AND NOT EXISTS (
                      SELECT 1 FROM chat_user_blocks b
                      WHERE (b.blocker_id = ? AND b.blocked_id = m.sender_id)
                         OR (b.blocker_id = m.sender_id AND b.blocked_id = ?)
                  )
                ORDER BY m.created_at DESC, m.id DESC
                LIMIT ?
                """.trimIndent()
            ).use { s ->
                s.setObject(1, roomId)
                s.setObject(2, before)
                s.setObject(3, before)
                s.setObject(4, userId)
                s.setObject(5, userId)
                s.setInt(6, safeLimit)
                s.executeQuery().use { rs ->
                    buildList {
                        while (rs.next()) {
                            val deleted = rs.getObject("deleted_at") != null
                            add(
                                CommunityMessageResponse(
                                    id = rs.getString("id"),
                                    roomId = rs.getString("room_id"),
                                    senderFriendCode = rs.getString("friend_code"),
                                    senderDisplayName = rs.getString("display_name"),
                                    body = if (deleted) "" else rs.getString("body"),
                                    objectType = if (deleted) null else rs.getString("object_type"),
                                    objectPayload = if (deleted) null else rs.getString("object_payload")?.let {
                                        runCatching { Json.parseToJsonElement(it) }.getOrNull()
                                    },
                                    deleted = deleted,
                                    createdAt = rs.getObject("created_at").toString()
                                )
                            )
                        }
                    }.reversed()
                }
            }
        }
        markRead(userId, roomId)
        return result
    }

    fun send(userId: UUID, roomId: UUID, request: SendCommunityMessageRequest): Pair<String, CommunityMessageResponse?> {
        if (!roomExists(roomId)) return "room_not_found" to null
        if (isSanctioned(userId)) return "chat_restricted" to null

        val body = request.body.trim()
        val objectType = request.objectType?.trim()?.uppercase()?.takeIf(String::isNotBlank)
        val allowedObjectTypes = setOf("CARD", "SET", "WISHLIST_CARD", "SHOWCASE", "TRADE_OFFER")
        if (body.length > 1200) return "message_too_long" to null
        if (body.isBlank() && objectType == null) return "empty_message" to null
        if (objectType != null && objectType !in allowedObjectTypes) return "invalid_object_type" to null
        if (objectType != null && request.objectPayload == null) return "missing_object_payload" to null
        if (!sendGuard.allow(userId, body, objectType)) return "rate_limited" to null

        return dataSource.connection.use { connection ->
            val id = UUID.randomUUID()
            val response = connection.prepareStatement(
                """
                INSERT INTO community_messages
                    (id, room_id, sender_id, body, object_type, object_payload)
                VALUES (?, ?, ?, ?, ?, ?::jsonb)
                RETURNING created_at
                """.trimIndent()
            ).use { s ->
                s.setObject(1, id)
                s.setObject(2, roomId)
                s.setObject(3, userId)
                s.setString(4, body)
                s.setString(5, objectType)
                s.setString(6, request.objectPayload?.let { Json.encodeToString(it) })
                s.executeQuery().use { rs ->
                    if (!rs.next()) return@use null
                    val user = userInfo(connection, userId)
                    CommunityMessageResponse(
                        id = id.toString(),
                        roomId = roomId.toString(),
                        senderFriendCode = user.first,
                        senderDisplayName = user.second,
                        body = body,
                        objectType = objectType,
                        objectPayload = request.objectPayload,
                        createdAt = rs.getObject("created_at").toString()
                    )
                }
            }
            if (response != null) {
                connection.prepareStatement(
                    "UPDATE community_rooms SET last_activity_at = NOW() WHERE id = ?"
                ).use { s ->
                    s.setObject(1, roomId)
                    s.executeUpdate()
                }
                events.tryEmit(CommunityEvent("MESSAGE_CREATED", roomId.toString(), response))
            }
            "ok" to response
        }
    }

    fun report(userId: UUID, messageId: UUID, reason: String): Boolean {
        val clean = reason.trim().take(300)
        if (clean.isBlank()) return false
        return dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO community_message_reports (id, message_id, reporter_id, reason)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (message_id, reporter_id) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    status = 'OPEN',
                    created_at = NOW(),
                    resolved_at = NULL,
                    resolved_by = NULL
                """.trimIndent()
            ).use { s ->
                s.setObject(1, UUID.randomUUID())
                s.setObject(2, messageId)
                s.setObject(3, userId)
                s.setString(4, clean)
                runCatching { s.executeUpdate() > 0 }.getOrDefault(false)
            }
        }
    }

    fun block(userId: UUID, friendCode: String, blocked: Boolean): Boolean {
        val target = findUserId(friendCode) ?: return false
        if (target == userId) return false
        return dataSource.connection.use { connection ->
            if (blocked) {
                connection.prepareStatement(
                    "INSERT INTO chat_user_blocks (blocker_id, blocked_id) VALUES (?, ?) ON CONFLICT DO NOTHING"
                ).use { s ->
                    s.setObject(1, userId)
                    s.setObject(2, target)
                    s.executeUpdate()
                }
            } else {
                connection.prepareStatement(
                    "DELETE FROM chat_user_blocks WHERE blocker_id = ? AND blocked_id = ?"
                ).use { s ->
                    s.setObject(1, userId)
                    s.setObject(2, target)
                    s.executeUpdate()
                }
            }
        }.let { true }
    }

    fun canModerate(userId: UUID, roles: RoleRepository): Boolean {
        if (roles.roleFor(userId)?.canAdmin == true) return true
        return dataSource.connection.use { connection ->
            connection.prepareStatement(
                "SELECT 1 FROM chat_moderator_roles WHERE user_id = ? AND active = TRUE"
            ).use { s ->
                s.setObject(1, userId)
                runCatching { s.executeQuery().use { it.next() } }.getOrDefault(false)
            }
        }
    }

    fun moderate(moderatorId: UUID, request: ModerateChatRequest): Boolean {
        val action = request.action.trim().uppercase()
        val allowed = setOf("DELETE_MESSAGE", "WARN", "MUTE", "UNMUTE", "BAN", "UNBAN")
        if (action !in allowed) return false
        val targetId = request.targetFriendCode?.let(::findUserId)
        val messageId = request.messageId?.let { runCatching { UUID.fromString(it) }.getOrNull() }
        val expiresAt = request.durationMinutes?.takeIf { it > 0 }?.let { Instant.now().plusSeconds(it * 60L) }

        return dataSource.connection.use { connection ->
            connection.autoCommit = false
            try {
                when (action) {
                    "DELETE_MESSAGE" -> {
                        if (messageId == null) return false
                        connection.prepareStatement(
                            "UPDATE community_messages SET deleted_at = NOW(), deleted_by = ? WHERE id = ?"
                        ).use { s ->
                            s.setObject(1, moderatorId)
                            s.setObject(2, messageId)
                            if (s.executeUpdate() == 0) return false
                        }
                    }
                    "MUTE" -> {
                        if (targetId == null || expiresAt == null) return false
                        upsertSanction(connection, targetId, expiresAt, ban = false)
                    }
                    "UNMUTE" -> {
                        if (targetId == null) return false
                        connection.prepareStatement(
                            "INSERT INTO chat_user_sanctions (user_id, muted_until) VALUES (?, NULL) ON CONFLICT (user_id) DO UPDATE SET muted_until = NULL, updated_at = NOW()"
                        ).use { s -> s.setObject(1, targetId); s.executeUpdate() }
                    }
                    "BAN" -> {
                        if (targetId == null) return false
                        upsertSanction(connection, targetId, null, ban = true)
                    }
                    "UNBAN" -> {
                        if (targetId == null) return false
                        connection.prepareStatement(
                            "INSERT INTO chat_user_sanctions (user_id, banned_at) VALUES (?, NULL) ON CONFLICT (user_id) DO UPDATE SET banned_at = NULL, updated_at = NOW()"
                        ).use { s -> s.setObject(1, targetId); s.executeUpdate() }
                    }
                }

                connection.prepareStatement(
                    """
                    INSERT INTO chat_moderation_actions
                        (id, target_user_id, message_id, moderator_id, action, reason, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """.trimIndent()
                ).use { s ->
                    s.setObject(1, UUID.randomUUID())
                    s.setObject(2, targetId)
                    s.setObject(3, messageId)
                    s.setObject(4, moderatorId)
                    s.setString(5, action)
                    s.setString(6, request.reason?.trim()?.take(500))
                    s.setObject(7, expiresAt)
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

    private fun upsertSanction(
        connection: java.sql.Connection,
        userId: UUID,
        mutedUntil: Instant?,
        ban: Boolean
    ) {
        if (ban) {
            connection.prepareStatement(
                "INSERT INTO chat_user_sanctions (user_id, banned_at) VALUES (?, NOW()) ON CONFLICT (user_id) DO UPDATE SET banned_at = NOW(), updated_at = NOW()"
            ).use { s -> s.setObject(1, userId); s.executeUpdate() }
        } else {
            connection.prepareStatement(
                "INSERT INTO chat_user_sanctions (user_id, muted_until) VALUES (?, ?) ON CONFLICT (user_id) DO UPDATE SET muted_until = EXCLUDED.muted_until, updated_at = NOW()"
            ).use { s -> s.setObject(1, userId); s.setObject(2, mutedUntil); s.executeUpdate() }
        }
    }

    private fun isSanctioned(userId: UUID): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                "SELECT banned_at IS NOT NULL OR (muted_until IS NOT NULL AND muted_until > NOW()) AS restricted FROM chat_user_sanctions WHERE user_id = ?"
            ).use { s ->
                s.setObject(1, userId)
                s.executeQuery().use { rs -> rs.next() && rs.getBoolean("restricted") }
            }
        }

    private fun markRead(userId: UUID, roomId: UUID) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO community_room_reads (room_id, user_id, last_read_at)
                VALUES (?, ?, NOW())
                ON CONFLICT (room_id, user_id) DO UPDATE SET last_read_at = NOW()
                """.trimIndent()
            ).use { s ->
                s.setObject(1, roomId)
                s.setObject(2, userId)
                s.executeUpdate()
            }
        }
    }

    private fun roomExists(roomId: UUID): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement("SELECT 1 FROM community_rooms WHERE id = ?").use { s ->
                s.setObject(1, roomId)
                s.executeQuery().use { it.next() }
            }
        }

    private fun findUserId(friendCode: String): UUID? =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                "SELECT id FROM users WHERE UPPER(friend_code) = UPPER(?) AND disabled_at IS NULL"
            ).use { s ->
                s.setString(1, friendCode.trim())
                s.executeQuery().use { rs -> if (rs.next()) rs.getObject("id", UUID::class.java) else null }
            }
        }

    private fun userInfo(connection: java.sql.Connection, userId: UUID): Pair<String, String?> =
        connection.prepareStatement("SELECT friend_code, display_name FROM users WHERE id = ?").use { s ->
            s.setObject(1, userId)
            s.executeQuery().use { rs ->
                if (rs.next()) rs.getString("friend_code").orEmpty() to rs.getString("display_name")
                else "" to null
            }
        }

    private fun String.normalizeChatLanguage(): String? =
        trim().lowercase().let {
            when (it) {
                "de", "en", "ja", "ko", "zh" -> it
                "zh-cn", "zh-tw" -> "zh"
                else -> null
            }
        }
}

fun Route.communityChatRoutes(
    repository: CommunityChatRepository,
    roles: RoleRepository
) {
    authenticate("auth-jwt") {
        route("/api/v1/chat/community") {
            get("/rooms") {
                val userId = call.authenticatedUserId()
                    ?: return@get call.respond(HttpStatusCode.Unauthorized)
                call.respond(
                    repository.rooms(
                        userId,
                        call.request.queryParameters["language"],
                        call.request.queryParameters["q"]
                    )
                )
            }

            post("/rooms/set") {
                call.authenticatedUserId()
                    ?: return@post call.respond(HttpStatusCode.Unauthorized)
                val room = repository.ensureSetRoom(call.receive<EnsureSetRoomRequest>())
                    ?: return@post call.respond(HttpStatusCode.BadRequest)
                call.respond(room)
            }

            get("/rooms/{roomId}/messages") {
                val userId = call.authenticatedUserId()
                    ?: return@get call.respond(HttpStatusCode.Unauthorized)
                val roomId = call.parameters["roomId"]?.let { runCatching { UUID.fromString(it) }.getOrNull() }
                    ?: return@get call.respond(HttpStatusCode.BadRequest)
                val before = call.request.queryParameters["before"]?.let { runCatching { Instant.parse(it) }.getOrNull() }
                val limit = call.request.queryParameters["limit"]?.toIntOrNull() ?: 50
                val messages = repository.messages(userId, roomId, before, limit)
                    ?: return@get call.respond(HttpStatusCode.NotFound)
                call.respond(messages)
            }

            post("/rooms/{roomId}/messages") {
                val userId = call.authenticatedUserId()
                    ?: return@post call.respond(HttpStatusCode.Unauthorized)
                val roomId = call.parameters["roomId"]?.let { runCatching { UUID.fromString(it) }.getOrNull() }
                    ?: return@post call.respond(HttpStatusCode.BadRequest)
                val (status, message) = repository.send(userId, roomId, call.receive<SendCommunityMessageRequest>())
                when {
                    message != null -> call.respond(HttpStatusCode.Created, message)
                    status == "rate_limited" -> call.respond(HttpStatusCode.TooManyRequests, mapOf("error" to status))
                    status == "chat_restricted" -> call.respond(HttpStatusCode.Forbidden, mapOf("error" to status))
                    status == "room_not_found" -> call.respond(HttpStatusCode.NotFound, mapOf("error" to status))
                    else -> call.respond(HttpStatusCode.BadRequest, mapOf("error" to status))
                }
            }

            post("/messages/{messageId}/report") {
                val userId = call.authenticatedUserId()
                    ?: return@post call.respond(HttpStatusCode.Unauthorized)
                val messageId = call.parameters["messageId"]?.let { runCatching { UUID.fromString(it) }.getOrNull() }
                    ?: return@post call.respond(HttpStatusCode.BadRequest)
                val ok = repository.report(userId, messageId, call.receive<ReportCommunityMessageRequest>().reason)
                call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.BadRequest)
            }

            post("/blocks") {
                val userId = call.authenticatedUserId()
                    ?: return@post call.respond(HttpStatusCode.Unauthorized)
                val ok = repository.block(userId, call.receive<BlockUserRequest>().friendCode, true)
                call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.BadRequest)
            }

            delete("/blocks/{friendCode}") {
                val userId = call.authenticatedUserId()
                    ?: return@delete call.respond(HttpStatusCode.Unauthorized)
                val code = call.parameters["friendCode"] ?: return@delete call.respond(HttpStatusCode.BadRequest)
                val ok = repository.block(userId, code, false)
                call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.BadRequest)
            }

            get("/events") {
                call.authenticatedUserId()
                    ?: return@get call.respond(HttpStatusCode.Unauthorized)
                val roomFilter = call.request.queryParameters["roomId"]
                call.respondTextWriter(ContentType.Text.EventStream) {
                    repository.eventFlow()
                        .filter { roomFilter == null || it.roomId == roomFilter }
                        .collect { event ->
                            write("event: community\n")
                            write("data: " + Json.encodeToString(event) + "\n\n")
                            flush()
                        }
                }
            }

            post("/moderation/actions") {
                val userId = call.authenticatedUserId()
                    ?: return@post call.respond(HttpStatusCode.Unauthorized)
                if (!repository.canModerate(userId, roles)) {
                    return@post call.respond(HttpStatusCode.Forbidden)
                }
                val ok = repository.moderate(userId, call.receive<ModerateChatRequest>())
                call.respond(if (ok) HttpStatusCode.NoContent else HttpStatusCode.BadRequest)
            }
        }
    }
}
