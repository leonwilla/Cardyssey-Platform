package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
data class ChatReactionResponse(
    val emoji: String,
    val count: Int,
    val reactedByMe: Boolean
)

class ChatReactionRepository(
    private val dataSource: HikariDataSource
) {
    private val allowedEmoji =
        setOf(
            "❤️",
            "👍",
            "🔥",
            "😂",
            "😮"
        )

    fun reactions(
        scope: String,
        messageIds: Collection<UUID>,
        viewerId: UUID
    ): Map<UUID, List<ChatReactionResponse>> {
        val normalizedScope =
            normalizeScope(
                scope
            ) ?: return emptyMap()

        val ids =
            messageIds
                .distinct()

        if (ids.isEmpty()) {
            return emptyMap()
        }

        val placeholders =
            ids.joinToString(
                ","
            ) {
                "?"
            }

        return dataSource.connection.use {
            connection ->
            connection.prepareStatement(
                """
                SELECT
                    message_id,
                    emoji,
                    COUNT(*) AS reaction_count,
                    BOOL_OR(user_id = ?) AS reacted_by_me
                FROM chat_message_reactions
                WHERE scope = ?
                  AND message_id IN ($placeholders)
                GROUP BY message_id, emoji
                ORDER BY message_id, emoji
                """.trimIndent()
            ).use {
                statement ->
                statement.setObject(
                    1,
                    viewerId
                )
                statement.setString(
                    2,
                    normalizedScope
                )

                ids.forEachIndexed {
                    index,
                    id ->
                    statement.setObject(
                        index + 3,
                        id
                    )
                }

                statement.executeQuery()
                    .use {
                        result ->
                        buildMap<
                            UUID,
                            MutableList<
                                ChatReactionResponse
                            >
                        > {
                            while (
                                result.next()
                            ) {
                                val messageId =
                                    result.getObject(
                                        "message_id",
                                        UUID::class.java
                                    )

                                getOrPut(
                                    messageId
                                ) {
                                    mutableListOf()
                                }
                                    .add(
                                        ChatReactionResponse(
                                            emoji =
                                                result.getString(
                                                    "emoji"
                                                ),
                                            count =
                                                result.getInt(
                                                    "reaction_count"
                                                ),
                                            reactedByMe =
                                                result.getBoolean(
                                                    "reacted_by_me"
                                                )
                                        )
                                    )
                            }
                        }
                    }
            }
        }
    }

    fun toggle(
        scope: String,
        messageId: UUID,
        userId: UUID,
        emoji: String
    ): List<ChatReactionResponse>? {
        val normalizedScope =
            normalizeScope(
                scope
            ) ?: return null

        val normalizedEmoji =
            emoji.trim()
                .takeIf {
                    it in allowedEmoji
                }
                ?: return null

        dataSource.connection.use {
            connection ->
            connection.autoCommit =
                false

            try {
                val removed =
                    connection.prepareStatement(
                        """
                        DELETE FROM chat_message_reactions
                        WHERE scope = ?
                          AND message_id = ?
                          AND user_id = ?
                          AND emoji = ?
                        """.trimIndent()
                    ).use {
                        statement ->
                        statement.setString(
                            1,
                            normalizedScope
                        )
                        statement.setObject(
                            2,
                            messageId
                        )
                        statement.setObject(
                            3,
                            userId
                        )
                        statement.setString(
                            4,
                            normalizedEmoji
                        )

                        statement.executeUpdate() >
                            0
                    }

                if (!removed) {
                    connection.prepareStatement(
                        """
                        INSERT INTO chat_message_reactions (
                            scope,
                            message_id,
                            user_id,
                            emoji
                        )
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT DO NOTHING
                        """.trimIndent()
                    ).use {
                        statement ->
                        statement.setString(
                            1,
                            normalizedScope
                        )
                        statement.setObject(
                            2,
                            messageId
                        )
                        statement.setObject(
                            3,
                            userId
                        )
                        statement.setString(
                            4,
                            normalizedEmoji
                        )
                        statement.executeUpdate()
                    }
                }

                connection.commit()
            } catch (
                error: Throwable
            ) {
                connection.rollback()
                throw error
            } finally {
                connection.autoCommit =
                    true
            }
        }

        return reactions(
            scope =
                normalizedScope,
            messageIds =
                listOf(
                    messageId
                ),
            viewerId =
                userId
        )[
            messageId
        ].orEmpty()
    }

    private fun normalizeScope(
        value: String
    ): String? =
        value
            .trim()
            .uppercase()
            .takeIf {
                it == "GROUP" ||
                    it == "COMMUNITY"
            }
}
