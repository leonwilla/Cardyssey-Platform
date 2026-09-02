package de.cardyssey.api

import java.sql.Connection
import java.sql.ResultSet
import java.time.OffsetDateTime
import java.util.UUID
import javax.sql.DataSource

data class MarketplaceOffer(
    val id: UUID,
    val listingId: UUID,

    val buyerFriendCode: String,
    val buyerDisplayName: String?,

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
    val offerPriceEur: Double,
    val listingPriceEur: Double?,
    val message: String?,
    val status: String,

    val createdAt: String,
    val updatedAt: String
)

data class CreateMarketplaceOfferResult(
    val offer: MarketplaceOffer? = null,
    val error: String? = null
)

class MarketplaceOfferRepository(
    private val dataSource: DataSource
) {

    private val offerSelect =
        """
        SELECT
            o.id,
            o.listing_id,

            buyer.friend_code
                AS buyer_friend_code,
            buyer.display_name
                AS buyer_display_name,

            seller.friend_code
                AS seller_friend_code,
            seller.display_name
                AS seller_display_name,

            c.card_id,
            c.language_code,
            c.name,
            c.set_name,
            c.local_id,
            c.image_base,
            c.legacy_variant,
            c.condition,

            o.quantity,
            o.price_eur
                AS offer_price_eur,
            s.price_eur
                AS listing_price_eur,

            o.message,
            o.status,
            o.created_at,
            o.updated_at

        FROM marketplace_offers o

        JOIN sale_listings s
          ON s.id = o.listing_id

        JOIN collection_items c
          ON c.id = s.collection_item_id

        JOIN users buyer
          ON buyer.id = o.buyer_user_id

        JOIN users seller
          ON seller.id = s.user_id
        """.trimIndent()


    fun incoming(
        sellerUserId: UUID
    ): List<MarketplaceOffer> =
        dataSource.connection.use {
            connection ->

            connection.prepareStatement(
                """
                $offerSelect

                WHERE s.user_id = ?

                ORDER BY
                    CASE o.status
                        WHEN 'PENDING' THEN 0
                        ELSE 1
                    END,
                    o.updated_at DESC
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    sellerUserId
                )

                statement.executeQuery().use {
                    result ->
                    readOffers(result)
                }
            }
        }


    fun outgoing(
        buyerUserId: UUID
    ): List<MarketplaceOffer> =
        dataSource.connection.use {
            connection ->

            connection.prepareStatement(
                """
                $offerSelect

                WHERE o.buyer_user_id = ?

                ORDER BY
                    CASE o.status
                        WHEN 'PENDING' THEN 0
                        ELSE 1
                    END,
                    o.updated_at DESC
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    buyerUserId
                )

                statement.executeQuery().use {
                    result ->
                    readOffers(result)
                }
            }
        }


    fun create(
        buyerUserId: UUID,
        listingId: UUID,
        quantity: Int,
        priceEur: Double,
        message: String?
    ): CreateMarketplaceOfferResult {

        dataSource.connection.use {
            connection ->

            connection.autoCommit = false

            try {
                val listing =
                    connection.prepareStatement(
                        """
                        SELECT
                            s.user_id,
                            s.quantity,
                            s.price_eur,
                            s.negotiable,
                            s.status,
                            c.quantity
                                AS owned_quantity,
                            c.deleted_at

                        FROM sale_listings s

                        JOIN collection_items c
                          ON c.id =
                             s.collection_item_id

                        WHERE s.id = ?

                        FOR UPDATE
                        """.trimIndent()
                    ).use { statement ->

                        statement.setObject(
                            1,
                            listingId
                        )

                        statement
                            .executeQuery()
                            .use { result ->

                                if (
                                    !result.next()
                                ) {
                                    null
                                } else {
                                    ListingCheck(
                                        sellerUserId =
                                            result.getObject(
                                                "user_id",
                                                UUID::class.java
                                            ),

                                        listedQuantity =
                                            result.getInt(
                                                "quantity"
                                            ),

                                        ownedQuantity =
                                            result.getInt(
                                                "owned_quantity"
                                            ),

                                        negotiable =
                                            result.getBoolean(
                                                "negotiable"
                                            ),

                                        status =
                                            result.getString(
                                                "status"
                                            ),

                                        deleted =
                                            result.getObject(
                                                "deleted_at"
                                            ) != null
                                    )
                                }
                            }
                    }

                if (listing == null) {
                    connection.rollback()

                    return CreateMarketplaceOfferResult(
                        error =
                            "listing_not_found"
                    )
                }

                if (
                    listing.sellerUserId ==
                    buyerUserId
                ) {
                    connection.rollback()

                    return CreateMarketplaceOfferResult(
                        error =
                            "own_listing"
                    )
                }

                if (
                    listing.status != "ACTIVE" ||
                    listing.deleted
                ) {
                    connection.rollback()

                    return CreateMarketplaceOfferResult(
                        error =
                            "listing_not_active"
                    )
                }

                if (!listing.negotiable) {
                    connection.rollback()

                    return CreateMarketplaceOfferResult(
                        error =
                            "listing_not_negotiable"
                    )
                }

                val available =
                    minOf(
                        listing.listedQuantity,
                        listing.ownedQuantity
                    )

                if (
                    quantity < 1 ||
                    quantity > available
                ) {
                    connection.rollback()

                    return CreateMarketplaceOfferResult(
                        error =
                            "invalid_quantity"
                    )
                }

                val duplicate =
                    connection.prepareStatement(
                        """
                        SELECT 1

                        FROM marketplace_offers

                        WHERE listing_id = ?
                          AND buyer_user_id = ?
                          AND status = 'PENDING'

                        LIMIT 1
                        """.trimIndent()
                    ).use { statement ->

                        statement.setObject(
                            1,
                            listingId
                        )

                        statement.setObject(
                            2,
                            buyerUserId
                        )

                        statement
                            .executeQuery()
                            .use {
                                it.next()
                            }
                    }

                if (duplicate) {
                    connection.rollback()

                    return CreateMarketplaceOfferResult(
                        error =
                            "pending_offer_exists"
                    )
                }

                val id =
                    UUID.randomUUID()

                connection.prepareStatement(
                    """
                    INSERT INTO marketplace_offers (
                        id,
                        listing_id,
                        buyer_user_id,
                        quantity,
                        price_eur,
                        message,
                        status
                    )
                    VALUES (
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        'PENDING'
                    )
                    """.trimIndent()
                ).use { statement ->

                    statement.setObject(
                        1,
                        id
                    )

                    statement.setObject(
                        2,
                        listingId
                    )

                    statement.setObject(
                        3,
                        buyerUserId
                    )

                    statement.setInt(
                        4,
                        quantity
                    )

                    statement.setDouble(
                        5,
                        priceEur
                    )

                    statement.setString(
                        6,
                        message
                    )

                    statement.executeUpdate()
                }

                connection.commit()

                return CreateMarketplaceOfferResult(
                    offer =
                        findById(id)
                )

            } catch (error: Exception) {
                connection.rollback()
                throw error

            } finally {
                connection.autoCommit = true
            }
        }
    }


    fun accept(
        sellerUserId: UUID,
        offerId: UUID
    ): MarketplaceOffer? =
        sellerDecision(
            sellerUserId,
            offerId,
            "ACCEPTED"
        )


    fun reject(
        sellerUserId: UUID,
        offerId: UUID
    ): MarketplaceOffer? =
        sellerDecision(
            sellerUserId,
            offerId,
            "REJECTED"
        )


    fun withdraw(
        buyerUserId: UUID,
        offerId: UUID
    ): Boolean =
        dataSource.connection.use {
            connection ->

            connection.prepareStatement(
                """
                UPDATE marketplace_offers

                SET
                    status = 'WITHDRAWN',
                    updated_at = NOW()

                WHERE id = ?
                  AND buyer_user_id = ?
                  AND status = 'PENDING'
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    offerId
                )

                statement.setObject(
                    2,
                    buyerUserId
                )

                statement.executeUpdate() > 0
            }
        }


    private fun sellerDecision(
        sellerUserId: UUID,
        offerId: UUID,
        status: String
    ): MarketplaceOffer? {

        val updated =
            dataSource.connection.use {
                connection ->

                connection.prepareStatement(
                    """
                    UPDATE marketplace_offers o

                    SET
                        status = ?,
                        updated_at = NOW()

                    FROM sale_listings s

                    WHERE o.id = ?
                      AND o.listing_id = s.id
                      AND s.user_id = ?
                      AND o.status = 'PENDING'
                    """.trimIndent()
                ).use { statement ->

                    statement.setString(
                        1,
                        status
                    )

                    statement.setObject(
                        2,
                        offerId
                    )

                    statement.setObject(
                        3,
                        sellerUserId
                    )

                    statement.executeUpdate() > 0
                }
            }

        return if (updated) {
            findById(offerId)
        } else {
            null
        }
    }


    private fun findById(
        offerId: UUID
    ): MarketplaceOffer? =
        dataSource.connection.use {
            connection ->

            connection.prepareStatement(
                """
                $offerSelect

                WHERE o.id = ?
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    offerId
                )

                statement
                    .executeQuery()
                    .use { result ->

                        if (result.next()) {
                            readOffer(result)
                        } else {
                            null
                        }
                    }
            }
        }


    private fun readOffers(
        result: ResultSet
    ): List<MarketplaceOffer> =
        buildList {
            while (result.next()) {
                add(
                    readOffer(result)
                )
            }
        }


    private fun readOffer(
        result: ResultSet
    ): MarketplaceOffer {

        val listingPrice =
            result.getDouble(
                "listing_price_eur"
            )

        return MarketplaceOffer(
            id =
                result.getObject(
                    "id",
                    UUID::class.java
                ),

            listingId =
                result.getObject(
                    "listing_id",
                    UUID::class.java
                ),

            buyerFriendCode =
                result.getString(
                    "buyer_friend_code"
                ),

            buyerDisplayName =
                result.getString(
                    "buyer_display_name"
                ),

            sellerFriendCode =
                result.getString(
                    "seller_friend_code"
                ),

            sellerDisplayName =
                result.getString(
                    "seller_display_name"
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
                    "quantity"
                ),

            offerPriceEur =
                result.getDouble(
                    "offer_price_eur"
                ),

            listingPriceEur =
                if (
                    result.wasNull()
                ) {
                    null
                } else {
                    listingPrice
                },

            message =
                result.getString(
                    "message"
                ),

            status =
                result.getString(
                    "status"
                ),

            createdAt =
                result
                    .getObject(
                        "created_at",
                        OffsetDateTime::class.java
                    )
                    .toString(),

            updatedAt =
                result
                    .getObject(
                        "updated_at",
                        OffsetDateTime::class.java
                    )
                    .toString()
        )
    }


    private data class ListingCheck(
        val sellerUserId: UUID,
        val listedQuantity: Int,
        val ownedQuantity: Int,
        val negotiable: Boolean,
        val status: String,
        val deleted: Boolean
    )
}
