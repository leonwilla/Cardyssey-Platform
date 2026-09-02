package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import java.util.UUID

data class WishlistItem(
    val id: UUID,
    val cardId: String,
    val languageCode: String,
    val name: String,
    val setId: String?,
    val setName: String?,
    val localId: String?,
    val imageBase: String?,
    val variantId: String?,
    val variantType: String?,
    val variantSubtype: String?,
    val foil: String?,
    val size: String?,
    val stamps: List<String>
)

class WishlistRepository(
    private val dataSource: HikariDataSource
) {
    fun list(userId: UUID): List<WishlistItem> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT *
                FROM wishlist_items
                WHERE user_id = ?
                ORDER BY created_at DESC
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, userId)

                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            add(
                                WishlistItem(
                                    id = result.getObject("id", UUID::class.java),
                                    cardId = result.getString("card_id"),
                                    languageCode = result.getString("language_code"),
                                    name = result.getString("name"),
                                    setId = result.getString("set_id"),
                                    setName = result.getString("set_name"),
                                    localId = result.getString("local_id"),
                                    imageBase = result.getString("image_base"),
                                    variantId = result.getString("variant_id"),
                                    variantType = result.getString("variant_type"),
                                    variantSubtype = result.getString("variant_subtype"),
                                    foil = result.getString("foil"),
                                    size = result.getString("size"),
                                    stamps = result.getArray("stamps")
                                        ?.array
                                        ?.let {
                                            @Suppress("UNCHECKED_CAST")
                                            (it as Array<String>).toList()
                                        }
                                        ?: emptyList()
                                )
                            )
                        }
                    }
                }
            }
        }

    fun create(userId: UUID, item: WishlistItem): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO wishlist_items (
                    id, user_id, card_id, language_code,
                    name, set_id, set_name, local_id,
                    image_base, variant_id, variant_type,
                    variant_subtype, foil, size, stamps
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, item.id)
                statement.setObject(2, userId)
                statement.setString(3, item.cardId)
                statement.setString(4, item.languageCode)
                statement.setString(5, item.name)
                statement.setString(6, item.setId)
                statement.setString(7, item.setName)
                statement.setString(8, item.localId)
                statement.setString(9, item.imageBase)
                statement.setString(10, item.variantId)
                statement.setString(11, item.variantType)
                statement.setString(12, item.variantSubtype)
                statement.setString(13, item.foil)
                statement.setString(14, item.size)
                statement.setArray(
                    15,
                    connection.createArrayOf(
                        "text",
                        item.stamps.toTypedArray()
                    )
                )

                statement.executeUpdate() > 0
            }
        }

    fun delete(userId: UUID, id: UUID): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                DELETE FROM wishlist_items
                WHERE id = ?
                  AND user_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setObject(1, id)
                statement.setObject(2, userId)
                statement.executeUpdate() > 0
            }
        }
}
