package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.put
import io.ktor.server.routing.route
import kotlinx.serialization.Serializable
import java.util.UUID

@Serializable
data class ShowcaseItemResponse(
    val collectionItemId: String,
    val position: Int,
    val cardId: String,
    val name: String,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variant: String
)

@Serializable
data class UpdateShowcaseRequest(
    val collectionItemIds: List<String>
)

@Serializable
data class ShowcaseProfileResponse(
    val title: String,
    val theme: String,
    val likeCount: Int,
    val likedByMe: Boolean
)

@Serializable
data class UpdateShowcaseProfileRequest(
    val title: String,
    val theme: String
)

class ShowcaseRepository(
    private val dataSource: HikariDataSource
) {

    fun profile(
        showcaseUserId: UUID,
        viewerId: UUID
    ): ShowcaseProfileResponse =
        dataSource.connection.use {
            connection ->
            val stored =
                connection.prepareStatement(
                    """
                    SELECT title, theme
                    FROM showcase_profiles
                    WHERE user_id = ?
                    """.trimIndent()
                ).use {
                    statement ->
                    statement.setObject(
                        1,
                        showcaseUserId
                    )

                    statement.executeQuery()
                        .use {
                            result ->
                            if (
                                result.next()
                            ) {
                                result.getString(
                                    "title"
                                ) to
                                    result.getString(
                                        "theme"
                                    )
                            } else {
                                "Mein Showcase" to
                                    "OBSIDIAN"
                            }
                        }
                }

            val likes =
                connection.prepareStatement(
                    """
                    SELECT
                        COUNT(*) AS like_count,
                        BOOL_OR(user_id = ?) AS liked_by_me
                    FROM showcase_likes
                    WHERE showcase_user_id = ?
                    """.trimIndent()
                ).use {
                    statement ->
                    statement.setObject(
                        1,
                        viewerId
                    )
                    statement.setObject(
                        2,
                        showcaseUserId
                    )

                    statement.executeQuery()
                        .use {
                            result ->
                            if (
                                result.next()
                            ) {
                                result.getInt(
                                    "like_count"
                                ) to
                                    result.getBoolean(
                                        "liked_by_me"
                                    )
                            } else {
                                0 to false
                            }
                        }
                }

            ShowcaseProfileResponse(
                title =
                    stored.first,
                theme =
                    stored.second,
                likeCount =
                    likes.first,
                likedByMe =
                    likes.second
            )
        }

    fun updateProfile(
        userId: UUID,
        title: String,
        theme: String
    ): ShowcaseProfileResponse? {
        val cleanTitle =
            title
                .trim()
                .replace(
                    Regex("\\s+"),
                    " "
                )
                .takeIf {
                    it.length in
                        1..80
                }
                ?: return null

        val cleanTheme =
            theme
                .trim()
                .uppercase()
                .takeIf {
                    it in
                        setOf(
                            "OBSIDIAN",
                            "HOLO",
                            "GOLD",
                            "CYAN"
                        )
                }
                ?: return null

        dataSource.connection.use {
            connection ->
            connection.prepareStatement(
                """
                INSERT INTO showcase_profiles
                    (user_id, title, theme, updated_at)
                VALUES (?, ?, ?, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    theme = EXCLUDED.theme,
                    updated_at = NOW()
                """.trimIndent()
            ).use {
                statement ->
                statement.setObject(
                    1,
                    userId
                )
                statement.setString(
                    2,
                    cleanTitle
                )
                statement.setString(
                    3,
                    cleanTheme
                )
                statement.executeUpdate()
            }
        }

        return profile(
            showcaseUserId =
                userId,
            viewerId =
                userId
        )
    }

    fun toggleLike(
        viewerId: UUID,
        showcaseUserId: UUID
    ): ShowcaseProfileResponse? {
        if (
            viewerId ==
            showcaseUserId
        ) {
            return profile(
                showcaseUserId =
                    showcaseUserId,
                viewerId =
                    viewerId
            )
        }

        dataSource.connection.use {
            connection ->
            val removed =
                connection.prepareStatement(
                    """
                    DELETE FROM showcase_likes
                    WHERE showcase_user_id = ?
                      AND user_id = ?
                    """.trimIndent()
                ).use {
                    statement ->
                    statement.setObject(
                        1,
                        showcaseUserId
                    )
                    statement.setObject(
                        2,
                        viewerId
                    )
                    statement.executeUpdate() >
                        0
                }

            if (!removed) {
                connection.prepareStatement(
                    """
                    INSERT INTO showcase_likes
                        (showcase_user_id, user_id)
                    VALUES (?, ?)
                    ON CONFLICT DO NOTHING
                    """.trimIndent()
                ).use {
                    statement ->
                    statement.setObject(
                        1,
                        showcaseUserId
                    )
                    statement.setObject(
                        2,
                        viewerId
                    )
                    statement.executeUpdate()
                }
            }
        }

        return profile(
            showcaseUserId =
                showcaseUserId,
            viewerId =
                viewerId
        )
    }

    fun list(
        userId: UUID
    ): List<ShowcaseItemResponse> {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    c.id,
                    s.position,
                    c.card_id,
                    c.name,
                    c.set_name,
                    c.local_id,
                    c.image_base,
                    c.legacy_variant
                FROM showcase_items s
                JOIN collection_items c
                  ON c.id = s.collection_item_id
                WHERE s.user_id = ?
                  AND c.user_id = ?
                  AND c.deleted_at IS NULL
                ORDER BY s.position
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, userId)
                statement.setObject(2, userId)

                statement.executeQuery().use { result ->
                    val items =
                        mutableListOf<ShowcaseItemResponse>()

                    while (result.next()) {
                        items += ShowcaseItemResponse(
                            collectionItemId =
                                result.getString("id"),
                            position =
                                result.getInt("position"),
                            cardId =
                                result.getString("card_id"),
                            name =
                                result.getString("name"),
                            setName =
                                result.getString("set_name"),
                            localId =
                                result.getString("local_id"),
                            imageBase =
                                result.getString("image_base"),
                            variant =
                                result.getString("legacy_variant")
                        )
                    }

                    return items
                }
            }
        }
    }

    fun replace(
        userId: UUID,
        ids: List<UUID>,
        maxSize: Int
    ): Boolean {

        if (
            ids.size > maxSize ||
            ids.distinct().size != ids.size
        ) {
            return false
        }

        dataSource.connection.use { connection ->
            connection.autoCommit = false

            try {
                if (ids.isNotEmpty()) {
                    val placeholders =
                        ids.joinToString(",") { "?" }

                    val validCount =
                        connection.prepareStatement(
                            """
                            SELECT COUNT(*)
                            FROM collection_items
                            WHERE user_id = ?
                              AND deleted_at IS NULL
                              AND id IN ($placeholders)
                            """.trimIndent()
                        ).use { statement ->

                            statement.setObject(1, userId)

                            ids.forEachIndexed { index, id ->
                                statement.setObject(
                                    index + 2,
                                    id
                                )
                            }

                            statement.executeQuery().use {
                                it.next()
                                it.getInt(1)
                            }
                        }

                    if (validCount != ids.size) {
                        connection.rollback()
                        return false
                    }
                }

                connection.prepareStatement(
                    """
                    DELETE FROM showcase_items
                    WHERE user_id = ?
                    """.trimIndent()
                ).use {
                    it.setObject(1, userId)
                    it.executeUpdate()
                }

                ids.forEachIndexed { index, id ->
                    connection.prepareStatement(
                        """
                        INSERT INTO showcase_items (
                            user_id,
                            collection_item_id,
                            position
                        )
                        VALUES (?, ?, ?)
                        """.trimIndent()
                    ).use {
                        it.setObject(1, userId)
                        it.setObject(2, id)
                        it.setInt(3, index + 1)
                        it.executeUpdate()
                    }
                }

                connection.commit()
                return true

            } catch (e: Exception) {
                connection.rollback()
                throw e
            } finally {
                connection.autoCommit = true
            }
        }
    }
}

fun Route.showcaseRoutes(
    repository: ShowcaseRepository,
    privacyRepository: PrivacyRepository
) {
    authenticate("auth-jwt") {

        route("/api/v1/me/showcase") {

            get("/profile") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    repository.profile(
                        showcaseUserId =
                            userId,
                        viewerId =
                            userId
                    )
                )
            }

            put("/profile") {
                val userId =
                    call.authenticatedUserId()
                        ?: return@put call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val request =
                    call.receive<
                        UpdateShowcaseProfileRequest
                    >()

                val profile =
                    repository.updateProfile(
                        userId =
                            userId,
                        title =
                            request.title,
                        theme =
                            request.theme
                    )
                        ?: return@put call.respond(
                            HttpStatusCode.BadRequest,
                            mapOf(
                                "error" to
                                    "invalid_showcase_profile"
                            )
                        )

                call.respond(
                    profile
                )
            }

            get {
                val userId =
                    call.authenticatedUserId()
                        ?: return@get call.respond(
                            HttpStatusCode.Unauthorized
                        )

                call.respond(
                    repository.list(userId)
                )
            }

            put {
                val userId =
                    call.authenticatedUserId()
                        ?: return@put call.respond(
                            HttpStatusCode.Unauthorized
                        )

                val request =
                    call.receive<UpdateShowcaseRequest>()

                val ids =
                    request.collectionItemIds
                        .mapNotNull {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }

                if (
                    ids.size !=
                    request.collectionItemIds.size
                ) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_showcase")
                    )
                    return@put
                }

                val maxSize =
                    privacyRepository
                        .get(userId)
                        .showcaseSize

                if (
                    !repository.replace(
                        userId,
                        ids,
                        maxSize
                    )
                ) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_showcase")
                    )
                    return@put
                }

                call.respond(
                    repository.list(userId)
                )
            }
        }
    }
}
