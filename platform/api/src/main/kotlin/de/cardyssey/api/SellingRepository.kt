package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import java.math.BigDecimal
import java.util.UUID

data class SaleListing(
    val id: UUID,
    val collectionItemId: UUID,
    val cardId: String,
    val name: String,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variant: String,
    val condition: String,
    val ownedQuantity: Int,
    val quantity: Int,
    val priceEur: Double?,
    val negotiable: Boolean,
    val status: String
)

data class MarketplaceListing(
    val id: UUID,
    val sellerFriendCode: String,
    val sellerDisplayName: String?,
    val cardId: String,
    val languageCode: String,
    val name: String,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variant: String,
    val condition: String,
    val quantity: Int,
    val priceEur: Double?,
    val negotiable: Boolean
)

class SellingRepository(
    private val dataSource: HikariDataSource
) {

    fun list(userId: UUID): List<SaleListing> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    s.id,
                    s.collection_item_id,
                    c.card_id,
                    c.name,
                    c.set_name,
                    c.local_id,
                    c.image_base,
                    c.legacy_variant,
                    c.condition,
                    c.quantity AS owned_quantity,
                    s.quantity,
                    s.price_eur,
                    s.negotiable,
                    s.status
                FROM sale_listings s
                JOIN collection_items c
                  ON c.id = s.collection_item_id
                WHERE s.user_id = ?
                  AND c.deleted_at IS NULL
                ORDER BY
                    CASE s.status
                        WHEN 'ACTIVE' THEN 1
                        WHEN 'PAUSED' THEN 2
                        ELSE 3
                    END,
                    s.updated_at DESC
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            val price =
                                result.getDouble("price_eur")

                            val priceEur =
                                if (result.wasNull())
                                    null
                                else
                                    price

                            add(
                                SaleListing(
                                    id = result.getObject(
                                        "id",
                                        UUID::class.java
                                    ),
                                    collectionItemId = result.getObject(
                                        "collection_item_id",
                                        UUID::class.java
                                    ),
                                    cardId = result.getString("card_id"),
                                    name = result.getString("name"),
                                    setName = result.getString("set_name"),
                                    localId = result.getString("local_id"),
                                    imageBase = result.getString("image_base"),
                                    variant = result.getString("legacy_variant"),
                                    condition = result.getString("condition"),
                                    ownedQuantity = result.getInt("owned_quantity"),
                                    quantity = result.getInt("quantity"),
                                    priceEur = priceEur,
                                    negotiable = result.getBoolean("negotiable"),
                                    status = result.getString("status")
                                )
                            )
                        }
                    }
                }
            }
        }

    fun create(
        userId: UUID,
        collectionItemId: UUID,
        quantity: Int,
        priceEur: Double?,
        negotiable: Boolean
    ): Boolean =
        save(
            userId,
            null,
            collectionItemId,
            quantity,
            priceEur,
            negotiable,
            "ACTIVE"
        )

    fun update(
        userId: UUID,
        listingId: UUID,
        collectionItemId: UUID,
        quantity: Int,
        priceEur: Double?,
        negotiable: Boolean,
        status: String
    ): Boolean =
        save(
            userId,
            listingId,
            collectionItemId,
            quantity,
            priceEur,
            negotiable,
            status
        )

    private fun save(
        userId: UUID,
        listingId: UUID?,
        collectionItemId: UUID,
        quantity: Int,
        priceEur: Double?,
        negotiable: Boolean,
        status: String
    ): Boolean {

        if (quantity < 1) return false

        dataSource.connection.use { connection ->
            connection.autoCommit = false

            try {
                val ownedQuantity =
                    connection.prepareStatement(
                        """
                        SELECT quantity
                        FROM collection_items
                        WHERE id = ?
                          AND user_id = ?
                          AND deleted_at IS NULL
                        FOR UPDATE
                        """.trimIndent()
                    ).use { statement ->

                        statement.setObject(1, collectionItemId)
                        statement.setObject(2, userId)

                        statement.executeQuery().use { result ->
                            if (!result.next()) {
                                connection.rollback()
                                return false
                            }

                            result.getInt("quantity")
                        }
                    }

                if (quantity > ownedQuantity) {
                    connection.rollback()
                    return false
                }

                val changed =
                    if (listingId == null) {
                        connection.prepareStatement(
                            """
                            INSERT INTO sale_listings (
                                id,
                                user_id,
                                collection_item_id,
                                quantity,
                                price_eur,
                                negotiable,
                                status
                            )
                            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
                            ON CONFLICT DO NOTHING
                            """.trimIndent()
                        ).use { statement ->

                            statement.setObject(1, UUID.randomUUID())
                            statement.setObject(2, userId)
                            statement.setObject(3, collectionItemId)
                            statement.setInt(4, quantity)

                            if (priceEur == null) {
                                statement.setNull(
                                    5,
                                    java.sql.Types.NUMERIC
                                )
                            } else {
                                statement.setBigDecimal(
                                    5,
                                    BigDecimal.valueOf(priceEur)
                                )
                            }

                            statement.setBoolean(6, negotiable)

                            statement.executeUpdate() > 0
                        }
                    } else {
                        connection.prepareStatement(
                            """
                            UPDATE sale_listings
                            SET
                                quantity = ?,
                                price_eur = ?,
                                negotiable = ?,
                                status = ?,
                                updated_at = NOW()
                            WHERE id = ?
                              AND user_id = ?
                              AND collection_item_id = ?
                            """.trimIndent()
                        ).use { statement ->

                            statement.setInt(1, quantity)

                            if (priceEur == null) {
                                statement.setNull(
                                    2,
                                    java.sql.Types.NUMERIC
                                )
                            } else {
                                statement.setBigDecimal(
                                    2,
                                    BigDecimal.valueOf(priceEur)
                                )
                            }

                            statement.setBoolean(3, negotiable)
                            statement.setString(4, status)
                            statement.setObject(5, listingId)
                            statement.setObject(6, userId)
                            statement.setObject(7, collectionItemId)

                            statement.executeUpdate() > 0
                        }
                    }

                if (!changed) {
                    connection.rollback()
                    return false
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

    fun marketplace(
        currentUserId: UUID
    ): List<MarketplaceListing> =
        dataSource.connection.use { connection ->

            connection.prepareStatement(
                """
                SELECT
                    s.id,
                    u.friend_code,
                    u.display_name,
                    c.card_id,
                    c.language_code,
                    c.name,
                    c.set_name,
                    c.local_id,
                    c.image_base,
                    c.legacy_variant,
                    c.condition,
                    LEAST(
                        s.quantity,
                        c.quantity
                    ) AS available_quantity,
                    s.price_eur,
                    s.negotiable

                FROM sale_listings s

                JOIN collection_items c
                  ON c.id = s.collection_item_id

                JOIN users u
                  ON u.id = s.user_id

                WHERE s.status = 'ACTIVE'
                  AND s.user_id <> ?
                  AND c.deleted_at IS NULL
                  AND c.quantity > 0
                  AND u.disabled_at IS NULL

                ORDER BY s.updated_at DESC
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    currentUserId
                )

                statement.executeQuery().use { result ->

                    buildList {
                        while (result.next()) {

                            val price =
                                result.getDouble(
                                    "price_eur"
                                )

                            val priceEur =
                                if (result.wasNull())
                                    null
                                else
                                    price

                            add(
                                MarketplaceListing(
                                    id =
                                        result.getObject(
                                            "id",
                                            UUID::class.java
                                        ),

                                    sellerFriendCode =
                                        result.getString(
                                            "friend_code"
                                        ),

                                    sellerDisplayName =
                                        result.getString(
                                            "display_name"
                                        ),

                                    cardId =
                                        result.getString(
                                            "card_id"
                                        ),

                                    languageCode =
                                        result.getString(
                                            "language_code"
                                        ),

                                    name =
                                        result.getString(
                                            "name"
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

                                    condition =
                                        result.getString(
                                            "condition"
                                        ),

                                    quantity =
                                        result.getInt(
                                            "available_quantity"
                                        ),

                                    priceEur =
                                        priceEur,

                                    negotiable =
                                        result.getBoolean(
                                            "negotiable"
                                        )
                                )
                            )
                        }
                    }
                }
            }
        }

    fun delete(
        userId: UUID,
        listingId: UUID
    ): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                DELETE FROM sale_listings
                WHERE id = ?
                  AND user_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, listingId)
                statement.setObject(2, userId)

                statement.executeUpdate() > 0
            }
        }
}
