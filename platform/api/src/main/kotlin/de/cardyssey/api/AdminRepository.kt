package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.Serializable
import java.sql.ResultSet
import java.util.UUID

@Serializable
data class AdminOverviewResponse(
    val registeredUsers: Long,
    val activeUsers: Long,
    val collectionItems: Long,
    val collectionCards: Long,
    val wishlistItems: Long,
    val activeListings: Long,
    val pendingOffers: Long
)

@Serializable
data class AdminUserSummaryResponse(
    val id: String,
    val email: String,
    val displayName: String?,
    val friendCode: String,
    val role: UserRole,
    val disabled: Boolean,
    val createdAt: String,
    val collectionItems: Long,
    val collectionCards: Long,
    val wishlistItems: Long,
    val activeListings: Long,
    val pendingOffers: Long
)

@Serializable
data class AdminCollectionItemResponse(
    val id: String,
    val cardId: String,
    val languageCode: String,
    val name: String,
    val setName: String?,
    val localId: String?,
    val variant: String,
    val condition: String,
    val quantity: Int,
    val valuedUnitEur: Double?,
    val positionValueEur: Double?
)

@Serializable
data class AdminDuplicateCardResponse(
    val cardId: String,
    val languageCode: String,
    val name: String,
    val setName: String?,
    val localId: String?,
    val variantKey: String,
    val variant: String,
    val quantity: Int
)

@Serializable
data class AdminWishlistItemResponse(
    val id: String,
    val cardId: String,
    val languageCode: String,
    val name: String,
    val setName: String?,
    val localId: String?,
    val variantId: String?,
    val createdAt: String
)

@Serializable
data class AdminListingResponse(
    val id: String,
    val collectionItemId: String,
    val cardId: String,
    val name: String,
    val quantity: Int,
    val priceEur: Double?,
    val negotiable: Boolean,
    val status: String,
    val createdAt: String
)

@Serializable
data class AdminUserDetailResponse(
    val user: AdminUserSummaryResponse,
    val collection: List<AdminCollectionItemResponse>,
    val wishlist: List<AdminWishlistItemResponse>,
    val listings: List<AdminListingResponse>
)

@Serializable
data class FounderSystemResponse(
    val database: String,
    val service: String,
    val version: String,
    val justTcgConfigured: Boolean,
    val soldCompsConfigured: Boolean,
    val registeredUsers: Long,
    val collectionItems: Long
)

class AdminRepository(
    private val dataSource: HikariDataSource
) {

    fun overview(): AdminOverviewResponse =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    (SELECT COUNT(*) FROM users) AS registered_users,
                    (SELECT COUNT(*) FROM users WHERE disabled_at IS NULL) AS active_users,
                    (SELECT COUNT(*) FROM collection_items WHERE deleted_at IS NULL) AS collection_items,
                    (SELECT COALESCE(SUM(quantity), 0) FROM collection_items WHERE deleted_at IS NULL) AS collection_cards,
                    (SELECT COUNT(*) FROM wishlist_items) AS wishlist_items,
                    (SELECT COUNT(*) FROM sale_listings WHERE status = 'ACTIVE') AS active_listings,
                    (SELECT COUNT(*) FROM marketplace_offers WHERE status = 'PENDING') AS pending_offers
                """.trimIndent()
            ).use { statement ->
                statement.executeQuery().use { result ->
                    check(result.next())

                    AdminOverviewResponse(
                        registeredUsers = result.getLong("registered_users"),
                        activeUsers = result.getLong("active_users"),
                        collectionItems = result.getLong("collection_items"),
                        collectionCards = result.getLong("collection_cards"),
                        wishlistItems = result.getLong("wishlist_items"),
                        activeListings = result.getLong("active_listings"),
                        pendingOffers = result.getLong("pending_offers")
                    )
                }
            }
        }

    fun users(query: String?): List<AdminUserSummaryResponse> {
        val normalized =
            query?.trim()
                ?.takeIf(String::isNotBlank)
                ?.take(120)

        val sql =
            """
            SELECT
                u.id,
                u.email,
                u.display_name,
                u.friend_code,
                u.role,
                u.disabled_at,
                u.created_at,
                (SELECT COUNT(*) FROM collection_items c WHERE c.user_id = u.id AND c.deleted_at IS NULL) AS collection_items,
                (SELECT COALESCE(SUM(c.quantity), 0) FROM collection_items c WHERE c.user_id = u.id AND c.deleted_at IS NULL) AS collection_cards,
                (SELECT COUNT(*) FROM wishlist_items w WHERE w.user_id = u.id) AS wishlist_items,
                (SELECT COUNT(*) FROM sale_listings s WHERE s.user_id = u.id AND s.status = 'ACTIVE') AS active_listings,
                (SELECT COUNT(*) FROM marketplace_offers o WHERE o.buyer_user_id = u.id AND o.status = 'PENDING') AS pending_offers
            FROM users u
            WHERE (
                ? IS NULL
                OR LOWER(u.email) LIKE LOWER(?)
                OR LOWER(COALESCE(u.display_name, '')) LIKE LOWER(?)
                OR LOWER(u.friend_code) LIKE LOWER(?)
            )
            ORDER BY
                CASE u.role
                    WHEN 'FOUNDER' THEN 0
                    WHEN 'ADMIN' THEN 1
                    ELSE 2
                END,
                u.created_at DESC
            LIMIT 100
            """.trimIndent()

        return dataSource.connection.use { connection ->
            connection.prepareStatement(sql).use { statement ->
                val pattern = normalized?.let { "%$it%" }
                statement.setString(1, normalized)
                statement.setString(2, pattern)
                statement.setString(3, pattern)
                statement.setString(4, pattern)

                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            add(result.toUserSummary())
                        }
                    }
                }
            }
        }
    }

    fun user(userId: UUID): AdminUserDetailResponse? {
        val summary = userSummary(userId)
            ?: return null

        return AdminUserDetailResponse(
            user = summary,
            collection = collection(userId),
            wishlist = wishlist(userId),
            listings = listings(userId)
        )
    }

    fun system(
        justTcgConfigured: Boolean,
        soldCompsConfigured: Boolean
    ): FounderSystemResponse {
        val overview = overview()

        val databaseHealthy =
            runCatching {
                dataSource.connection.use { connection ->
                    connection.prepareStatement("SELECT 1").use { statement ->
                        statement.executeQuery().use { result ->
                            result.next()
                        }
                    }
                }
            }.getOrDefault(false)

        return FounderSystemResponse(
            database = if (databaseHealthy) "connected" else "unavailable",
            service = "cardyssey-api",
            version = "0.2.0",
            justTcgConfigured = justTcgConfigured,
            soldCompsConfigured = soldCompsConfigured,
            registeredUsers = overview.registeredUsers,
            collectionItems = overview.collectionItems
        )
    }

    private fun userSummary(
        userId: UUID
    ): AdminUserSummaryResponse? =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    u.id,
                    u.email,
                    u.display_name,
                    u.friend_code,
                    u.role,
                    u.disabled_at,
                    u.created_at,
                    (SELECT COUNT(*) FROM collection_items c WHERE c.user_id = u.id AND c.deleted_at IS NULL) AS collection_items,
                    (SELECT COALESCE(SUM(c.quantity), 0) FROM collection_items c WHERE c.user_id = u.id AND c.deleted_at IS NULL) AS collection_cards,
                    (SELECT COUNT(*) FROM wishlist_items w WHERE w.user_id = u.id) AS wishlist_items,
                    (SELECT COUNT(*) FROM sale_listings s WHERE s.user_id = u.id AND s.status = 'ACTIVE') AS active_listings,
                    (SELECT COUNT(*) FROM marketplace_offers o WHERE o.buyer_user_id = u.id AND o.status = 'PENDING') AS pending_offers
                FROM users u
                WHERE u.id = ?
                LIMIT 1
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        null
                    } else {
                        result.toUserSummary()
                    }
                }
            }
        }

    fun collection(
        userId: UUID,
        search: String? = null
    ): List<AdminCollectionItemResponse> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    c.id,
                    c.card_id,
                    c.language_code,
                    c.name,
                    c.set_name,
                    c.local_id,
                    c.legacy_variant,
                    c.condition,
                    c.quantity,
                    COALESCE(mp.value_eur, c.unit_eur) AS base_eur
                FROM collection_items c
                LEFT JOIN market_prices mp
                  ON mp.collection_item_id = c.id
                 AND mp.market = 'TCG'
                WHERE c.user_id = ?
                  AND c.deleted_at IS NULL
                  AND (
                    ? IS NULL
                    OR POSITION(
                        LOWER(?) IN LOWER(CONCAT_WS(' ',
                            c.name, c.set_name, c.local_id,
                            c.card_id, c.legacy_variant, c.language_code
                        ))
                    ) > 0
                  )
                ORDER BY c.updated_at DESC, c.id
                LIMIT 10
                """.trimIndent()
            ).use { statement ->
                val query = search?.trim()?.takeIf { it.isNotEmpty() }
                statement.setObject(1, userId)
                statement.setString(2, query)
                statement.setString(3, query)

                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            val base = result.getDouble("base_eur")
                                .let { if (result.wasNull()) null else it }
                            val condition = PricingCondition.parse(
                                result.getString("condition")
                            )
                            val valued =
                                if (
                                    base != null &&
                                    base.isFinite() &&
                                    base > 0.0 &&
                                    condition != null
                                ) {
                                    base * condition.factor
                                } else {
                                    null
                                }
                            val quantity = result.getInt("quantity")

                            add(
                                AdminCollectionItemResponse(
                                    id = result.getString("id"),
                                    cardId = result.getString("card_id"),
                                    languageCode = result.getString("language_code"),
                                    name = result.getString("name"),
                                    setName = result.getString("set_name"),
                                    localId = result.getString("local_id"),
                                    variant = result.getString("legacy_variant"),
                                    condition = result.getString("condition"),
                                    quantity = quantity,
                                    valuedUnitEur = valued,
                                    positionValueEur = valued?.times(quantity)
                                )
                            )
                        }
                    }
                }
            }
        }

    fun duplicates(
        userId: UUID
    ): List<AdminDuplicateCardResponse> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                WITH grouped AS (
                    SELECT
                        c.card_id,
                        c.language_code,
                        CASE
                            WHEN COALESCE(c.variant_subtype, '') <> ''
                              OR COALESCE(c.variant_foil, '') <> ''
                              OR (
                                    COALESCE(c.variant_size, '') <> ''
                                    AND LOWER(c.variant_size) <> 'standard'
                                 )
                              OR jsonb_array_length(COALESCE(c.variant_stamps, '[]'::jsonb)) > 0
                            THEN COALESCE(
                                NULLIF(c.variant_id, ''),
                                NULLIF(c.variant_identity, ''),
                                UPPER(COALESCE(NULLIF(c.legacy_variant, ''), 'NORMAL'))
                            )
                            ELSE UPPER(COALESCE(NULLIF(c.legacy_variant, ''), 'NORMAL'))
                        END AS duplicate_key,
                        UPPER(COALESCE(NULLIF(c.legacy_variant, ''), 'NORMAL')) AS legacy_variant,
                        SUM(c.quantity) AS quantity
                    FROM collection_items c
                    WHERE c.user_id = ?
                      AND c.deleted_at IS NULL
                    GROUP BY
                        c.card_id,
                        c.language_code,
                        CASE
                            WHEN COALESCE(c.variant_subtype, '') <> ''
                              OR COALESCE(c.variant_foil, '') <> ''
                              OR (
                                    COALESCE(c.variant_size, '') <> ''
                                    AND LOWER(c.variant_size) <> 'standard'
                                 )
                              OR jsonb_array_length(COALESCE(c.variant_stamps, '[]'::jsonb)) > 0
                            THEN COALESCE(
                                NULLIF(c.variant_id, ''),
                                NULLIF(c.variant_identity, ''),
                                UPPER(COALESCE(NULLIF(c.legacy_variant, ''), 'NORMAL'))
                            )
                            ELSE UPPER(COALESCE(NULLIF(c.legacy_variant, ''), 'NORMAL'))
                        END,
                        UPPER(COALESCE(NULLIF(c.legacy_variant, ''), 'NORMAL'))
                    HAVING SUM(c.quantity) > 1
                )
                SELECT
                    g.card_id,
                    g.language_code,
                    COALESCE(m.name, g.card_id) AS name,
                    COALESCE(s.name, m.set_id) AS set_name,
                    m.local_id,
                    g.duplicate_key,
                    g.legacy_variant,
                    g.quantity
                FROM grouped g
                LEFT JOIN catalog_cards_mirror m
                  ON m.card_id = g.card_id
                 AND m.language_code = g.language_code
                LEFT JOIN catalog_sets_mirror s
                  ON s.set_id = m.set_id
                 AND s.language_code = g.language_code
                ORDER BY
                    g.quantity DESC,
                    COALESCE(s.name, m.set_id, ''),
                    COALESCE(m.local_id, ''),
                    COALESCE(m.name, g.card_id),
                    g.legacy_variant
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            add(
                                AdminDuplicateCardResponse(
                                    cardId = result.getString("card_id"),
                                    languageCode = result.getString("language_code"),
                                    name = result.getString("name"),
                                    setName = result.getString("set_name"),
                                    localId = result.getString("local_id"),
                                    variantKey = result.getString("duplicate_key"),
                                    variant = result.getString("legacy_variant"),
                                    quantity = result.getInt("quantity")
                                )
                            )
                        }
                    }
                }
            }
        }

    private fun wishlist(
        userId: UUID
    ): List<AdminWishlistItemResponse> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    id,
                    card_id,
                    language_code,
                    name,
                    set_name,
                    local_id,
                    variant_id,
                    created_at
                FROM wishlist_items
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 500
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            add(
                                AdminWishlistItemResponse(
                                    id = result.getString("id"),
                                    cardId = result.getString("card_id"),
                                    languageCode = result.getString("language_code"),
                                    name = result.getString("name"),
                                    setName = result.getString("set_name"),
                                    localId = result.getString("local_id"),
                                    variantId = result.getString("variant_id"),
                                    createdAt = result.getTimestamp("created_at").toInstant().toString()
                                )
                            )
                        }
                    }
                }
            }
        }

    private fun listings(
        userId: UUID
    ): List<AdminListingResponse> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    s.id,
                    s.collection_item_id,
                    c.card_id,
                    c.name,
                    s.quantity,
                    s.price_eur,
                    s.negotiable,
                    s.status,
                    s.created_at
                FROM sale_listings s
                JOIN collection_items c
                  ON c.id = s.collection_item_id
                WHERE s.user_id = ?
                ORDER BY s.updated_at DESC
                LIMIT 500
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            val price = result.getDouble("price_eur")
                                .let { if (result.wasNull()) null else it }

                            add(
                                AdminListingResponse(
                                    id = result.getString("id"),
                                    collectionItemId = result.getString("collection_item_id"),
                                    cardId = result.getString("card_id"),
                                    name = result.getString("name"),
                                    quantity = result.getInt("quantity"),
                                    priceEur = price,
                                    negotiable = result.getBoolean("negotiable"),
                                    status = result.getString("status"),
                                    createdAt = result.getTimestamp("created_at").toInstant().toString()
                                )
                            )
                        }
                    }
                }
            }
        }

    private fun ResultSet.toUserSummary(): AdminUserSummaryResponse =
        AdminUserSummaryResponse(
            id = getString("id"),
            email = getString("email"),
            displayName = getString("display_name"),
            friendCode = getString("friend_code"),
            role = UserRole.parse(getString("role")) ?: UserRole.USER,
            disabled = getTimestamp("disabled_at") != null,
            createdAt = getTimestamp("created_at").toInstant().toString(),
            collectionItems = getLong("collection_items"),
            collectionCards = getLong("collection_cards"),
            wishlistItems = getLong("wishlist_items"),
            activeListings = getLong("active_listings"),
            pendingOffers = getLong("pending_offers")
        )
}
