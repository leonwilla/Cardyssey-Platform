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
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.route
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.filter
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.util.UUID

@Serializable
data class ChatMessageResponse(
    val id: String,
    val senderFriendCode: String,
    val recipientFriendCode: String,
    val body: String,
    val createdAt: String,
    val readAt: String?
)

@Serializable
data class ChatThreadResponse(
    val friendCode: String,
    val displayName: String?,
    val avatarUrl: String?,
    val lastMessage: ChatMessageResponse?,
    val unreadCount: Int
)

@Serializable
data class SendChatMessageRequest(
    val body: String
)

@Serializable
data class DirectChatEvent(
    val type: String,
    val message: ChatMessageResponse
)

private data class ChatMessageRecord(
    val id: UUID,
    val senderId: UUID,
    val recipientId: UUID,
    val senderFriendCode: String,
    val recipientFriendCode: String,
    val body: String,
    val createdAt: String,
    val readAt: String?
)

class ChatRepository(
    private val dataSource: HikariDataSource,
    private val friendships: FriendshipRepository
) {
    private val events =
        MutableSharedFlow<DirectChatEvent>(
            extraBufferCapacity = 256
        )

    fun eventFlow() =
        events

    fun currentFriendCode(
        userId: UUID
    ): String =
        friendCodeFor(userId)

    fun threads(userId: UUID): List<ChatThreadResponse> =
        friendships
            .friends(userId)
            .map { friend ->
                val target =
                    friendships.findUserByFriendCode(
                        friend.user.friendCode
                    )
                        ?: return@map ChatThreadResponse(
                            friendCode = friend.user.friendCode,
                            displayName = friend.user.displayName,
                            avatarUrl = null,
                            lastMessage = null,
                            unreadCount = 0
                        )

                ChatThreadResponse(
                    friendCode = friend.user.friendCode,
                    displayName = friend.user.displayName,
                    avatarUrl =
                        avatarUrlFor(
                            friendships.avatarPath(
                                target.first
                            )
                        ),
                    lastMessage =
                        latestMessage(
                            userId,
                            target.first
                        )?.toResponse(),
                    unreadCount =
                        unreadCount(
                            userId,
                            target.first
                        )
                )
            }
            .sortedWith(
                compareByDescending<ChatThreadResponse> {
                    it.lastMessage?.createdAt
                }.thenBy {
                    it.displayName ?: it.friendCode
                }
            )

    fun messages(
        userId: UUID,
        friendCode: String
    ): List<ChatMessageResponse>? {
        val target =
            allowedFriend(userId, friendCode)
                ?: return null

        markRead(
            userId = userId,
            friendId = target.first
        )

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    m.id,
                    m.sender_id,
                    m.recipient_id,
                    sender.friend_code AS sender_friend_code,
                    recipient.friend_code AS recipient_friend_code,
                    m.body,
                    m.created_at,
                    m.read_at
                FROM direct_messages m
                JOIN users sender
                  ON sender.id = m.sender_id
                JOIN users recipient
                  ON recipient.id = m.recipient_id
                WHERE (
                    m.sender_id = ?
                    AND m.recipient_id = ?
                ) OR (
                    m.sender_id = ?
                    AND m.recipient_id = ?
                )
                ORDER BY m.created_at DESC
                LIMIT 100
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)
                statement.setObject(2, target.first)
                statement.setObject(3, target.first)
                statement.setObject(4, userId)

                statement.executeQuery().use { result ->
                    val messages =
                        mutableListOf<ChatMessageResponse>()

                    while (result.next()) {
                        messages +=
                            result.toChatRecord().toResponse()
                    }

                    return messages.reversed()
                }
            }
        }
    }

    fun send(
        userId: UUID,
        friendCode: String,
        body: String
    ): ChatMessageResponse? {
        val target =
            allowedFriend(userId, friendCode)
                ?: return null

        val normalized =
            body.trim()

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO direct_messages (
                    id,
                    sender_id,
                    recipient_id,
                    body
                )
                VALUES (?, ?, ?, ?)
                RETURNING
                    id,
                    created_at
                """.trimIndent()
            ).use { statement ->
                val id = UUID.randomUUID()
                statement.setObject(1, id)
                statement.setObject(2, userId)
                statement.setObject(3, target.first)
                statement.setString(4, normalized)

                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        return null
                    }

                    val response =
                        ChatMessageResponse(
                            id = id.toString(),
                            senderFriendCode =
                                friendCodeFor(userId),
                            recipientFriendCode =
                                target.second.friendCode,
                            body = normalized,
                            createdAt =
                                result.getObject("created_at").toString(),
                            readAt = null
                        )

                    events.tryEmit(
                        DirectChatEvent(
                            type = "message",
                            message = response
                        )
                    )

                    return response
                }
            }
        }
    }

    private fun allowedFriend(
        userId: UUID,
        friendCode: String
    ): Pair<UUID, PublicFriendUser>? {
        val target =
            friendships.findUserByFriendCode(friendCode)
                ?: return null

        return target.takeIf {
            friendships.isFriend(
                userId,
                target.first
            )
        }
    }

    private fun latestMessage(
        userId: UUID,
        friendId: UUID
    ): ChatMessageRecord? {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    m.id,
                    m.sender_id,
                    m.recipient_id,
                    sender.friend_code AS sender_friend_code,
                    recipient.friend_code AS recipient_friend_code,
                    m.body,
                    m.created_at,
                    m.read_at
                FROM direct_messages m
                JOIN users sender
                  ON sender.id = m.sender_id
                JOIN users recipient
                  ON recipient.id = m.recipient_id
                WHERE (
                    m.sender_id = ?
                    AND m.recipient_id = ?
                ) OR (
                    m.sender_id = ?
                    AND m.recipient_id = ?
                )
                ORDER BY m.created_at DESC
                LIMIT 1
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)
                statement.setObject(2, friendId)
                statement.setObject(3, friendId)
                statement.setObject(4, userId)

                statement.executeQuery().use { result ->
                    return if (result.next()) {
                        result.toChatRecord()
                    } else {
                        null
                    }
                }
            }
        }
    }

    private fun unreadCount(
        userId: UUID,
        friendId: UUID
    ): Int {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT COUNT(*)
                FROM direct_messages
                WHERE sender_id = ?
                  AND recipient_id = ?
                  AND read_at IS NULL
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, friendId)
                statement.setObject(2, userId)

                statement.executeQuery().use { result ->
                    result.next()
                    return result.getInt(1)
                }
            }
        }
    }

    private fun markRead(
        userId: UUID,
        friendId: UUID
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE direct_messages
                SET read_at = NOW()
                WHERE sender_id = ?
                  AND recipient_id = ?
                  AND read_at IS NULL
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, friendId)
                statement.setObject(2, userId)
                statement.executeUpdate()
            }
        }
    }

    private fun friendCodeFor(userId: UUID): String {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT friend_code
                FROM users
                WHERE id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    return if (result.next()) {
                        result.getString("friend_code")
                    } else {
                        ""
                    }
                }
            }
        }
    }

    private fun java.sql.ResultSet.toChatRecord() =
        ChatMessageRecord(
            id = UUID.fromString(getString("id")),
            senderId =
                UUID.fromString(getString("sender_id")),
            recipientId =
                UUID.fromString(getString("recipient_id")),
            senderFriendCode =
                getString("sender_friend_code"),
            recipientFriendCode =
                getString("recipient_friend_code"),
            body = getString("body"),
            createdAt =
                getObject("created_at").toString(),
            readAt =
                getObject("read_at")?.toString()
        )

    private fun ChatMessageRecord.toResponse() =
        ChatMessageResponse(
            id = id.toString(),
            senderFriendCode = senderFriendCode,
            recipientFriendCode = recipientFriendCode,
            body = body,
            createdAt = createdAt,
            readAt = readAt
        )
}

fun Route.chatRoutes(
    repository: ChatRepository
) {
    authenticate("auth-jwt") {
        route("/api/v1/chat") {
            get("/events") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val ownFriendCode =
                    repository.currentFriendCode(
                        userId
                    )

                val requestedFriend =
                    call.request
                        .queryParameters[
                            "friendCode"
                        ]
                        ?.trim()
                        ?.takeIf(
                            String::isNotBlank
                        )

                call.respondTextWriter(
                    ContentType.Text.EventStream
                ) {
                    repository
                        .eventFlow()
                        .filter { event ->
                            val message =
                                event.message

                            val relevantToUser =
                                message.senderFriendCode ==
                                    ownFriendCode ||
                                    message.recipientFriendCode ==
                                        ownFriendCode

                            val otherFriend =
                                if (
                                    message.senderFriendCode ==
                                        ownFriendCode
                                ) {
                                    message.recipientFriendCode
                                } else {
                                    message.senderFriendCode
                                }

                            relevantToUser &&
                                (
                                    requestedFriend ==
                                        null ||
                                        requestedFriend ==
                                            otherFriend
                                    )
                        }
                        .collect { event ->
                            write(
                                "event: direct\n"
                            )
                            write(
                                "data: " +
                                    Json.encodeToString(
                                        event
                                    ) +
                                    "\n\n"
                            )
                            flush()
                        }
                }
            }

            get("/threads") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    repository.threads(userId)
                )
            }

            route("/{friendCode}/messages") {
                get {
                    val userId =
                        call.authenticatedUserId()
                            ?: return@get call.respond(
                                HttpStatusCode.Unauthorized
                            )

                    val friendCode =
                        call.parameters["friendCode"]
                            ?.trim()
                            .orEmpty()

                    val messages =
                        repository.messages(
                            userId,
                            friendCode
                        )

                    if (messages == null) {
                        call.respond(
                            HttpStatusCode.Forbidden,
                            mapOf("error" to "friends_only")
                        )
                        return@get
                    }

                    call.respond(messages)
                }

                post {
                    val userId =
                        call.authenticatedUserId()
                            ?: return@post call.respond(
                                HttpStatusCode.Unauthorized
                            )

                    val friendCode =
                        call.parameters["friendCode"]
                            ?.trim()
                            .orEmpty()

                    val body =
                        call.receive<SendChatMessageRequest>()
                            .body
                            .trim()

                    if (
                        body.isBlank() ||
                        body.length > 2000
                    ) {
                        call.respond(
                            HttpStatusCode.BadRequest,
                            mapOf("error" to "invalid_message")
                        )
                        return@post
                    }

                    val message =
                        repository.send(
                            userId,
                            friendCode,
                            body
                        )

                    if (message == null) {
                        call.respond(
                            HttpStatusCode.Forbidden,
                            mapOf("error" to "friends_only")
                        )
                        return@post
                    }

                    call.respond(
                        HttpStatusCode.Created,
                        message
                    )
                }
            }
        }
    }
}
