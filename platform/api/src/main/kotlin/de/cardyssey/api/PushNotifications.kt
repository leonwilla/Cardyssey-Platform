package de.cardyssey.api

import com.google.auth.oauth2.GoogleCredentials
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.MulticastMessage
import com.zaxxer.hikari.HikariDataSource
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.patch
import io.ktor.server.routing.post
import io.ktor.server.routing.route
import kotlinx.serialization.Serializable
import java.io.ByteArrayInputStream
import java.util.UUID

@Serializable
data class RegisterPushDeviceRequest(
    val token: String,
    val platform: String = "ANDROID"
)

@Serializable
data class DeletePushDeviceRequest(
    val token: String
)

@Serializable
data class PushPreferencesResponse(
    val directMessages: Boolean = true,
    val groupMessages: Boolean = true,
    val communityMessages: Boolean = true
)

@Serializable
data class UpdatePushPreferencesRequest(
    val directMessages: Boolean? = null,
    val groupMessages: Boolean? = null,
    val communityMessages: Boolean? = null
)

class PushNotificationService(
    private val dataSource: HikariDataSource
) {
    private val messaging: FirebaseMessaging? =
        runCatching {
            val existing =
                FirebaseApp
                    .getApps()
                    .firstOrNull()

            val app =
                existing
                    ?: FirebaseApp.initializeApp(
                        FirebaseOptions
                            .builder()
                            .setCredentials(
                                firebaseCredentials()
                            )
                            .apply {
                                System.getenv(
                                    "FIREBASE_PROJECT_ID"
                                )
                                    ?.trim()
                                    ?.takeIf(
                                        String::isNotBlank
                                    )
                                    ?.let(
                                        ::setProjectId
                                    )
                            }
                            .build()
                    )

            FirebaseMessaging
                .getInstance(
                    app
                )
        }.getOrNull()

    val configured: Boolean
        get() =
            messaging != null

    private fun firebaseCredentials():
        GoogleCredentials {
        val raw =
            System.getenv(
                "FIREBASE_SERVICE_ACCOUNT_JSON"
            )
                ?.trim()
                ?.takeIf(
                    String::isNotBlank
                )

        return if (raw != null) {
            GoogleCredentials
                .fromStream(
                    ByteArrayInputStream(
                        raw.toByteArray(
                            Charsets.UTF_8
                        )
                    )
                )
        } else {
            GoogleCredentials
                .getApplicationDefault()
        }
    }

    fun register(
        userId: UUID,
        token: String,
        platform: String
    ): Boolean {
        val cleanToken =
            token.trim()

        if (
            cleanToken.length !in
            20..4096
        ) {
            return false
        }

        val cleanPlatform =
            platform
                .trim()
                .uppercase()
                .takeIf {
                    it in
                        setOf(
                            "ANDROID"
                        )
                }
                ?: return false

        return dataSource
            .connection
            .use { connection ->
                connection
                    .prepareStatement(
                        """
                        INSERT INTO push_devices
                            (user_id, token, platform, created_at, updated_at)
                        VALUES (?, ?, ?, NOW(), NOW())
                        ON CONFLICT (token) DO UPDATE SET
                            user_id = EXCLUDED.user_id,
                            platform = EXCLUDED.platform,
                            updated_at = NOW()
                        """.trimIndent()
                    )
                    .use {
                        it.setObject(
                            1,
                            userId
                        )

                        it.setString(
                            2,
                            cleanToken
                        )

                        it.setString(
                            3,
                            cleanPlatform
                        )

                        it.executeUpdate() >
                            0
                    }
            }
    }

    fun unregister(
        userId: UUID,
        token: String
    ): Boolean =
        dataSource
            .connection
            .use { connection ->
                connection
                    .prepareStatement(
                        """
                        DELETE FROM push_devices
                        WHERE user_id = ?
                          AND token = ?
                        """.trimIndent()
                    )
                    .use {
                        it.setObject(
                            1,
                            userId
                        )

                        it.setString(
                            2,
                            token.trim()
                        )

                        it.executeUpdate() >
                            0
                    }
            }

    fun preferences(
        userId: UUID
    ): PushPreferencesResponse =
        dataSource
            .connection
            .use { connection ->
                connection
                    .prepareStatement(
                        """
                        SELECT direct_messages,
                               group_messages,
                               community_messages
                        FROM push_preferences
                        WHERE user_id = ?
                        """.trimIndent()
                    )
                    .use {
                        it.setObject(
                            1,
                            userId
                        )

                        it.executeQuery()
                            .use { result ->
                                if (
                                    result.next()
                                ) {
                                    PushPreferencesResponse(
                                        directMessages =
                                            result.getBoolean(
                                                "direct_messages"
                                            ),
                                        groupMessages =
                                            result.getBoolean(
                                                "group_messages"
                                            ),
                                        communityMessages =
                                            result.getBoolean(
                                                "community_messages"
                                            )
                                    )
                                } else {
                                    PushPreferencesResponse()
                                }
                            }
                    }
            }

    fun updatePreferences(
        userId: UUID,
        request: UpdatePushPreferencesRequest
    ): PushPreferencesResponse {
        val current =
            preferences(
                userId
            )

        val updated =
            PushPreferencesResponse(
                directMessages =
                    request.directMessages
                        ?: current.directMessages,
                groupMessages =
                    request.groupMessages
                        ?: current.groupMessages,
                communityMessages =
                    request.communityMessages
                        ?: current.communityMessages
            )

        dataSource
            .connection
            .use { connection ->
                connection
                    .prepareStatement(
                        """
                        INSERT INTO push_preferences
                            (
                                user_id,
                                direct_messages,
                                group_messages,
                                community_messages,
                                updated_at
                            )
                        VALUES (?, ?, ?, ?, NOW())
                        ON CONFLICT (user_id) DO UPDATE SET
                            direct_messages = EXCLUDED.direct_messages,
                            group_messages = EXCLUDED.group_messages,
                            community_messages = EXCLUDED.community_messages,
                            updated_at = NOW()
                        """.trimIndent()
                    )
                    .use {
                        it.setObject(
                            1,
                            userId
                        )

                        it.setBoolean(
                            2,
                            updated.directMessages
                        )

                        it.setBoolean(
                            3,
                            updated.groupMessages
                        )

                        it.setBoolean(
                            4,
                            updated.communityMessages
                        )

                        it.executeUpdate()
                    }
            }

        return updated
    }

    fun directMessage(
        recipientId: UUID,
        senderFriendCode: String,
        senderName: String?,
        body: String
    ) {
        if (
            !preferences(
                recipientId
            ).directMessages
        ) {
            return
        }

        send(
            userIds =
                listOf(
                    recipientId
                ),
            title =
                senderName
                    ?.takeIf(
                        String::isNotBlank
                    )
                    ?: "Neue Nachricht",
            body =
                body.ifBlank {
                    "Neue Nachricht in Cardyssey"
                }
                    .take(
                        180
                    ),
            data =
                mapOf(
                    "type" to
                        "DIRECT",
                    "friendCode" to
                        senderFriendCode
                )
        )
    }

    fun groupMessage(
        groupId: UUID,
        senderId: UUID,
        groupName: String,
        senderName: String?,
        body: String
    ) {
        val recipients =
            dataSource
                .connection
                .use { connection ->
                    connection
                        .prepareStatement(
                            """
                            SELECT user_id
                            FROM chat_group_members
                            WHERE group_id = ?
                              AND user_id <> ?
                            """.trimIndent()
                        )
                        .use {
                            it.setObject(
                                1,
                                groupId
                            )

                            it.setObject(
                                2,
                                senderId
                            )

                            it.executeQuery()
                                .use { result ->
                                    buildList {
                                        while (
                                            result.next()
                                        ) {
                                            val userId =
                                                result.getObject(
                                                    "user_id",
                                                    UUID::class.java
                                                )

                                            if (
                                                preferences(
                                                    userId
                                                ).groupMessages
                                            ) {
                                                add(
                                                    userId
                                                )
                                            }
                                        }
                                    }
                                }
                        }
                }

        send(
            userIds =
                recipients,
            title =
                groupName,
            body =
                listOfNotNull(
                    senderName
                        ?.takeIf(
                            String::isNotBlank
                        ),
                    body
                        .ifBlank {
                            "Neue Gruppen-Nachricht"
                        }
                )
                    .joinToString(
                        ": "
                    )
                    .take(
                        180
                    ),
            data =
                mapOf(
                    "type" to
                        "GROUP",
                    "groupId" to
                        groupId.toString()
                )
        )
    }

    fun communityMessage(
        roomId: UUID,
        senderId: UUID,
        roomName: String,
        senderName: String?,
        body: String
    ) {
        val recipients =
            dataSource
                .connection
                .use { connection ->
                    connection
                        .prepareStatement(
                            """
                            SELECT user_id
                            FROM community_room_reads
                            WHERE room_id = ?
                              AND user_id <> ?
                            """.trimIndent()
                        )
                        .use {
                            it.setObject(
                                1,
                                roomId
                            )

                            it.setObject(
                                2,
                                senderId
                            )

                            it.executeQuery()
                                .use { result ->
                                    buildList {
                                        while (
                                            result.next()
                                        ) {
                                            val userId =
                                                result.getObject(
                                                    "user_id",
                                                    UUID::class.java
                                                )

                                            if (
                                                preferences(
                                                    userId
                                                ).communityMessages
                                            ) {
                                                add(
                                                    userId
                                                )
                                            }
                                        }
                                    }
                                }
                        }
                }

        send(
            userIds =
                recipients,
            title =
                roomName,
            body =
                listOfNotNull(
                    senderName
                        ?.takeIf(
                            String::isNotBlank
                        ),
                    body
                        .ifBlank {
                            "Neue Community-Nachricht"
                        }
                )
                    .joinToString(
                        ": "
                    )
                    .take(
                        180
                    ),
            data =
                mapOf(
                    "type" to
                        "COMMUNITY",
                    "roomId" to
                        roomId.toString()
                )
        )
    }

    private fun send(
        userIds: List<UUID>,
        title: String,
        body: String,
        data: Map<String, String>
    ) {
        val firebase =
            messaging
                ?: return

        if (
            userIds.isEmpty()
        ) {
            return
        }

        val tokens =
            tokensFor(
                userIds
            )

        if (
            tokens.isEmpty()
        ) {
            return
        }

        tokens
            .chunked(
                500
            )
            .forEach { batch ->
                val message =
                    MulticastMessage
                        .builder()
                        .addAllTokens(
                            batch
                        )
                        .putAllData(
                            data
                        )
                        .putData(
                            "title",
                            title
                        )
                        .putData(
                            "body",
                            body
                        )
                        .build()

                firebase
                    .sendEachForMulticastAsync(
                        message
                    )
            }
    }

    private fun tokensFor(
        userIds: List<UUID>
    ): List<String> {
        val uniqueIds =
            userIds.distinct()

        if (
            uniqueIds.isEmpty()
        ) {
            return emptyList()
        }

        val placeholders =
            uniqueIds
                .joinToString(
                    ","
                ) {
                    "?"
                }

        return dataSource
            .connection
            .use { connection ->
                connection
                    .prepareStatement(
                        """
                        SELECT token
                        FROM push_devices
                        WHERE user_id IN ($placeholders)
                        """.trimIndent()
                    )
                    .use { statement ->
                        uniqueIds
                            .forEachIndexed {
                                index,
                                userId ->
                                statement.setObject(
                                    index + 1,
                                    userId
                                )
                            }

                        statement
                            .executeQuery()
                            .use { result ->
                                buildList {
                                    while (
                                        result.next()
                                    ) {
                                        add(
                                            result.getString(
                                                "token"
                                            )
                                        )
                                    }
                                }
                            }
                    }
            }
    }
}

fun Route.pushNotificationRoutes(
    service: PushNotificationService
) {
    authenticate(
        "auth-jwt"
    ) {
        route(
            "/api/v1/push"
        ) {
            post(
                "/devices"
            ) {
                val userId =
                    call.authenticatedUserId()
                        ?: return@post call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val request =
                    call.receive<RegisterPushDeviceRequest>()

                if (
                    !service.register(
                        userId =
                            userId,
                        token =
                            request.token,
                        platform =
                            request.platform
                    )
                ) {
                    return@post call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf(
                            "error" to
                                "invalid_push_device"
                        )
                    )
                }

                call.respond(
                    HttpStatusCode.NoContent
                )
            }

            delete(
                "/devices"
            ) {
                val userId =
                    call.authenticatedUserId()
                        ?: return@delete call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val request =
                    call.receive<DeletePushDeviceRequest>()

                service.unregister(
                    userId =
                        userId,
                    token =
                        request.token
                )

                call.respond(
                    HttpStatusCode.NoContent
                )
            }

            get(
                "/preferences"
            ) {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    service.preferences(
                        userId
                    )
                )
            }

            patch(
                "/preferences"
            ) {
                val userId =
                    call.authenticatedUserId()
                        ?: return@patch call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    service.updatePreferences(
                        userId =
                            userId,
                        request =
                            call.receive()
                    )
                )
            }
        }
    }
}
