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
data class ReportMessageRequest(
    val reason: String = ""
)

@Serializable
data class AdminChatMessageResponse(
    val id: String,
    val senderFriendCode: String,
    val senderDisplayName: String?,
    val recipientFriendCode: String,
    val recipientDisplayName: String?,
    val body: String,
    val createdAt: String,
    val readAt: String?
)

@Serializable
data class AdminMessageReportResponse(
    val id: String,
    val message: AdminChatMessageResponse,
    val reporterFriendCode: String,
    val reporterDisplayName: String?,
    val reason: String?,
    val status: String,
    val createdAt: String
)

class ChatModerationRepository(
    private val dataSource: HikariDataSource
) {
    fun report(
        reporterId: UUID,
        messageId: UUID,
        reason: String
    ): Boolean {
        dataSource.connection.use { connection ->
            val allowed =
                connection.prepareStatement(
                    """
                    SELECT 1
                    FROM direct_messages
                    WHERE id = ?
                      AND (
                          sender_id = ?
                          OR recipient_id = ?
                      )
                    """.trimIndent()
                ).use { statement ->
                    statement.setObject(1, messageId)
                    statement.setObject(2, reporterId)
                    statement.setObject(3, reporterId)
                    statement.executeQuery().use { it.next() }
                }

            if (!allowed) return false

            connection.prepareStatement(
                """
                INSERT INTO message_reports (
                    id,
                    message_id,
                    reporter_id,
                    reason
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT (message_id, reporter_id)
                DO UPDATE SET
                    reason = EXCLUDED.reason,
                    status = 'OPEN',
                    created_at = NOW()
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, UUID.randomUUID())
                statement.setObject(2, messageId)
                statement.setObject(3, reporterId)
                statement.setString(
                    4,
                    reason
                        .trim()
                        .take(500)
                        .takeIf(String::isNotBlank)
                )
                statement.executeUpdate()
            }

            return true
        }
    }

    fun reports(
        actorUserId: UUID
    ): List<AdminMessageReportResponse> {
        audit(
            actorUserId = actorUserId,
            action = "LIST_REPORTS",
            query = null
        )

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    r.id AS report_id,
                    r.reason,
                    r.status,
                    r.created_at AS report_created_at,
                    reporter.friend_code AS reporter_friend_code,
                    reporter.display_name AS reporter_display_name,
                    m.id AS message_id,
                    sender.friend_code AS sender_friend_code,
                    sender.display_name AS sender_display_name,
                    recipient.friend_code AS recipient_friend_code,
                    recipient.display_name AS recipient_display_name,
                    m.body,
                    m.created_at,
                    m.read_at
                FROM message_reports r
                JOIN direct_messages m
                  ON m.id = r.message_id
                JOIN users reporter
                  ON reporter.id = r.reporter_id
                JOIN users sender
                  ON sender.id = m.sender_id
                JOIN users recipient
                  ON recipient.id = m.recipient_id
                ORDER BY
                    CASE
                        WHEN r.status = 'OPEN' THEN 0
                        ELSE 1
                    END,
                    r.created_at DESC
                LIMIT 250
                """.trimIndent()
            ).use { statement ->
                statement.executeQuery().use { result ->
                    val reports =
                        mutableListOf<AdminMessageReportResponse>()

                    while (result.next()) {
                        reports +=
                            AdminMessageReportResponse(
                                id =
                                    result.getString("report_id"),
                                message =
                                    result.toAdminMessage(),
                                reporterFriendCode =
                                    result.getString(
                                        "reporter_friend_code"
                                    ),
                                reporterDisplayName =
                                    result.getString(
                                        "reporter_display_name"
                                    ),
                                reason =
                                    result.getString("reason"),
                                status =
                                    result.getString("status"),
                                createdAt =
                                    result.getObject(
                                        "report_created_at"
                                    ).toString()
                            )
                    }

                    return reports
                }
            }
        }
    }

    fun messages(
        actorUserId: UUID,
        query: String?
    ): List<AdminChatMessageResponse> {
        val normalized =
            query
                ?.trim()
                ?.take(100)
                .orEmpty()

        audit(
            actorUserId = actorUserId,
            action = "SEARCH_MESSAGES",
            query = normalized
        )

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    m.id AS message_id,
                    sender.friend_code AS sender_friend_code,
                    sender.display_name AS sender_display_name,
                    recipient.friend_code AS recipient_friend_code,
                    recipient.display_name AS recipient_display_name,
                    m.body,
                    m.created_at,
                    m.read_at
                FROM direct_messages m
                JOIN users sender
                  ON sender.id = m.sender_id
                JOIN users recipient
                  ON recipient.id = m.recipient_id
                WHERE (
                    ? = ''
                    OR sender.friend_code ILIKE ?
                    OR sender.display_name ILIKE ?
                    OR sender.email ILIKE ?
                    OR recipient.friend_code ILIKE ?
                    OR recipient.display_name ILIKE ?
                    OR recipient.email ILIKE ?
                    OR m.body ILIKE ?
                )
                ORDER BY m.created_at DESC
                LIMIT 250
                """.trimIndent()
            ).use { statement ->
                val like = "%$normalized%"
                statement.setString(1, normalized)
                for (index in 2..8) {
                    statement.setString(index, like)
                }

                statement.executeQuery().use { result ->
                    val messages =
                        mutableListOf<AdminChatMessageResponse>()

                    while (result.next()) {
                        messages +=
                            result.toAdminMessage()
                    }

                    return messages
                }
            }
        }
    }

    private fun java.sql.ResultSet.toAdminMessage() =
        AdminChatMessageResponse(
            id = getString("message_id"),
            senderFriendCode =
                getString("sender_friend_code"),
            senderDisplayName =
                getString("sender_display_name"),
            recipientFriendCode =
                getString("recipient_friend_code"),
            recipientDisplayName =
                getString("recipient_display_name"),
            body = getString("body"),
            createdAt =
                getObject("created_at").toString(),
            readAt =
                getObject("read_at")?.toString()
        )

    private fun audit(
        actorUserId: UUID,
        action: String,
        query: String?
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO admin_chat_audit (
                    id,
                    actor_user_id,
                    action,
                    query
                )
                VALUES (?, ?, ?, ?)
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, UUID.randomUUID())
                statement.setObject(2, actorUserId)
                statement.setString(3, action)
                statement.setString(4, query)
                statement.executeUpdate()
            }
        }
    }
}

fun Route.chatModerationRoutes(
    repository: ChatModerationRepository,
    roles: RoleRepository
) {
    authenticate("auth-jwt") {
        post("/api/v1/chat/messages/{id}/report") {
            val userId =
                call.authenticatedUserId()
                    ?: return@post call.respond(
                        HttpStatusCode.Unauthorized
                    )

            val messageId =
                call.parameters["id"]
                    ?.let {
                        runCatching {
                            UUID.fromString(it)
                        }.getOrNull()
                    }

            if (messageId == null) {
                call.respond(
                    HttpStatusCode.BadRequest,
                    mapOf("error" to "invalid_message_id")
                )
                return@post
            }

            val request =
                call.receive<ReportMessageRequest>()

            if (
                !repository.report(
                    userId,
                    messageId,
                    request.reason
                )
            ) {
                call.respond(
                    HttpStatusCode.NotFound,
                    mapOf("error" to "message_not_found")
                )
                return@post
            }

            call.respond(
                HttpStatusCode.Created,
                mapOf("status" to "reported")
            )
        }

        route("/api/v1/admin/chat") {
            get("/reports") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                if (
                    roles.roleFor(userId)
                        ?.canAdmin != true
                ) {
                    call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf("error" to "admin_required")
                    )
                    return@get
                }

                call.respond(
                    repository.reports(userId)
                )
            }

            get("/messages") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                if (
                    roles.roleFor(userId)
                        ?.canAdmin != true
                ) {
                    call.respond(
                        HttpStatusCode.Forbidden,
                        mapOf("error" to "admin_required")
                    )
                    return@get
                }

                call.respond(
                    repository.messages(
                        actorUserId = userId,
                        query =
                            call.request
                                .queryParameters["q"]
                    )
                )
            }
        }
    }
}
