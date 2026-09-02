package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import java.util.UUID

data class FriendSetProgress(
    val setId: String,
    val setName: String?,
    val ownedCards: Int,
    val totalCards: Int?
)

class FriendSetRepository(
    private val dataSource: HikariDataSource
) {

    fun list(
        userId: UUID
    ): List<FriendSetProgress> {

        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    c.set_id,
                    MAX(c.set_name) AS set_name,
                    COUNT(DISTINCT c.card_id) AS owned_cards,

                    (
                        SELECT
                            jsonb_array_length(
                                cc.payload::jsonb -> 'cards'
                            )
                        FROM catalog_cache cc
                        WHERE cc.cache_key LIKE
                            '%/sets/' || c.set_id
                        ORDER BY cc.updated_at DESC
                        LIMIT 1
                    ) AS total_cards

                FROM collection_items c

                WHERE c.user_id = ?
                  AND c.deleted_at IS NULL
                  AND c.set_id IS NOT NULL
                  AND c.set_id <> ''

                GROUP BY c.set_id

                ORDER BY
                    MAX(c.set_name) NULLS LAST,
                    c.set_id
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    userId
                )

                statement.executeQuery().use { result ->

                    val sets =
                        mutableListOf<
                            FriendSetProgress
                        >()

                    while (result.next()) {

                        val total =
                            result.getInt(
                                "total_cards"
                            )

                        sets += FriendSetProgress(
                            setId =
                                result.getString(
                                    "set_id"
                                ),

                            setName =
                                result.getString(
                                    "set_name"
                                ),

                            ownedCards =
                                result.getInt(
                                    "owned_cards"
                                ),

                            totalCards =
                                if (
                                    result.wasNull()
                                ) {
                                    null
                                } else {
                                    total
                                }
                        )
                    }

                    return sets
                }
            }
        }
    }
}
