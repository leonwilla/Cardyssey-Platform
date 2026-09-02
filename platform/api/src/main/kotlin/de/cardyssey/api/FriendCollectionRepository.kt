package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import java.util.UUID

data class FriendCollectionCard(
    val cardId: String,
    val name: String,
    val setId: String?,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variant: String,
    val quantity: Int?
)

data class FriendCollectionData(
    val cards: List<FriendCollectionCard>,
    val totalValueEur: Double?
)

class FriendCollectionRepository(
    private val dataSource: HikariDataSource
) {

    fun load(
        userId: UUID,
        showQuantity: Boolean,
        showValue: Boolean
    ): FriendCollectionData {

        val cards =
            dataSource.connection.use { connection ->

                connection.prepareStatement(
                    """
                    SELECT
                        card_id,
                        name,
                        set_id,
                        set_name,
                        local_id,
                        image_base,
                        legacy_variant,
                        quantity
                    FROM collection_items
                    WHERE user_id = ?
                      AND deleted_at IS NULL
                    ORDER BY
                        set_name NULLS LAST,
                        local_id NULLS LAST,
                        name
                    """.trimIndent()
                ).use { statement ->

                    statement.setObject(
                        1,
                        userId
                    )

                    statement.executeQuery().use { result ->

                        val list =
                            mutableListOf<
                                FriendCollectionCard
                            >()

                        while (result.next()) {
                            list +=
                                FriendCollectionCard(
                                    cardId =
                                        result.getString(
                                            "card_id"
                                        ),
                                    name =
                                        result.getString(
                                            "name"
                                        ),
                                    setId =
                                        result.getString(
                                            "set_id"
                                        ),
                                    setName =
                                        result.getString(
                                            "set_name"
                                        ),
                                    localId =
                                        result.getString(
                                            "local_id"
                                        ),
                                    imageBase =
                                        result.getString(
                                            "image_base"
                                        ),
                                    variant =
                                        result.getString(
                                            "legacy_variant"
                                        ),
                                    quantity =
                                        if (showQuantity) {
                                            result.getInt(
                                                "quantity"
                                            )
                                        } else {
                                            null
                                        }
                                )
                        }

                        list
                    }
                }
            }

        val value =
            if (showValue) {
                calculateValue(userId)
            } else {
                null
            }

        return FriendCollectionData(
            cards = cards,
            totalValueEur = value
        )
    }

    private fun calculateValue(
        userId: UUID
    ): Double? {

        dataSource.connection.use { connection ->

            connection.prepareStatement(
                """
                SELECT
                    SUM(
                        COALESCE(
                            mp.value_eur,
                            c.unit_eur
                        )
                        * c.quantity
                        *
                        CASE c.condition
                            WHEN 'MINT' THEN 1.00
                            WHEN 'NEAR_MINT' THEN 0.92
                            WHEN 'EXCELLENT' THEN 0.80
                            WHEN 'GOOD' THEN 0.65
                            WHEN 'PLAYED' THEN 0.45
                            ELSE 1.00
                        END
                    ) AS total_value
                FROM collection_items c
                LEFT JOIN market_prices mp
                  ON mp.collection_item_id = c.id
                 AND mp.market = 'TCG'
                WHERE c.user_id = ?
                  AND c.deleted_at IS NULL
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    userId
                )

                statement.executeQuery().use { result ->

                    if (!result.next()) {
                        return null
                    }

                    val value =
                        result.getDouble(
                            "total_value"
                        )

                    return if (
                        result.wasNull()
                    ) {
                        null
                    } else {
                        value
                    }
                }
            }
        }
    }
}
