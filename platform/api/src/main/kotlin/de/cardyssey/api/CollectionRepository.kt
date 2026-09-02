package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.math.BigDecimal
import java.sql.Connection
import java.sql.ResultSet
import java.sql.Types
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.util.UUID

class CollectionRepository(
    private val dataSource: HikariDataSource
) {
    private val json =
        Json {
            ignoreUnknownKeys = true
        }

    fun importCollection(
        userId: UUID,
        items: List<CollectionItemDto>
    ): Int {
        dataSource.connection.use { connection ->
            connection.autoCommit = false

            try {
                for (item in items) {
                    val collectionItemId =
                        upsertItem(
                            connection,
                            userId,
                            item
                        )

                    replaceMarketPrices(
                        connection,
                        collectionItemId,
                        item
                    )
                }

                connection.commit()

                return items.size

            } catch (throwable: Throwable) {
                connection.rollback()
                throw throwable
            } finally {
                connection.autoCommit = true
            }
        }
    }

    fun list(
        userId: UUID
    ): List<CollectionItemDto> {

        dataSource.connection.use { connection ->

            connection.prepareStatement(
                """
                SELECT
                    ci.*,

                    COALESCE(
                        (
                            SELECT jsonb_object_agg(
                                mp.market,
                                mp.value_eur
                            )
                            FROM market_prices mp
                            WHERE mp.collection_item_id = ci.id
                              AND mp.value_eur IS NOT NULL
                        ),
                        '{}'::jsonb
                    )::text AS market_values,

                    COALESCE(
                        (
                            SELECT jsonb_object_agg(
                                mp.market,
                                mp.sample_count
                            )
                            FILTER (
                                WHERE mp.sample_count IS NOT NULL
                            )
                            FROM market_prices mp
                            WHERE mp.collection_item_id = ci.id
                        ),
                        '{}'::jsonb
                    )::text AS market_samples,

                    COALESCE(
                        (
                            SELECT jsonb_object_agg(
                                mp.market,
                                (
                                    EXTRACT(
                                        EPOCH FROM mp.updated_at
                                    ) * 1000
                                )::bigint
                            )
                            FROM market_prices mp
                            WHERE mp.collection_item_id = ci.id
                        ),
                        '{}'::jsonb
                    )::text AS market_updated

                FROM collection_items ci
                WHERE ci.user_id = ?
                  AND ci.deleted_at IS NULL
                ORDER BY ci.created_at ASC
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    userId
                )

                statement.executeQuery().use { result ->

                    val items =
                        mutableListOf<CollectionItemDto>()

                    while (result.next()) {
                        items +=
                            mapCollectionItem(result)
                    }

                    return items
                }
            }
        }
    }

    fun deleteByClientKey(
        userId: UUID,
        clientKey: String
    ): Boolean {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE collection_items
                SET
                    deleted_at = NOW(),
                    updated_at = NOW()
                WHERE user_id = ?
                  AND client_key = ?
                  AND deleted_at IS NULL
                """.trimIndent()
            ).use { statement ->

                statement.setObject(1, userId)
                statement.setString(2, clientKey)

                return statement.executeUpdate() > 0
            }
        }
    }

    private fun upsertItem(
        connection: Connection,
        userId: UUID,
        item: CollectionItemDto
    ): UUID {

        val newId =
            UUID.randomUUID()

        val variantIdentity =
            item.variantSpec
                ?.id
                ?.takeIf {
                    it.isNotBlank()
                }
                ?: "legacy:${item.variant.uppercase()}"

        connection.prepareStatement(
            """
            INSERT INTO collection_items (
                id,
                user_id,
                client_key,

                card_id,
                language_code,
                name,

                set_id,
                set_name,
                local_id,

                image_base,
                image_language,

                legacy_variant,
                variant_identity,

                variant_id,
                variant_type,
                variant_subtype,
                variant_foil,
                variant_size,
                variant_stamps,

                condition,
                quantity,

                unit_eur,
                unit_usd
            )
            VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?, ?::jsonb,
                ?, ?,
                ?, ?
            )

            ON CONFLICT (user_id, client_key)
            DO UPDATE SET
                card_id = EXCLUDED.card_id,
                language_code = EXCLUDED.language_code,
                name = EXCLUDED.name,

                set_id = EXCLUDED.set_id,
                set_name = EXCLUDED.set_name,
                local_id = EXCLUDED.local_id,

                image_base = EXCLUDED.image_base,
                image_language = EXCLUDED.image_language,

                legacy_variant = EXCLUDED.legacy_variant,
                variant_identity = EXCLUDED.variant_identity,

                variant_id = EXCLUDED.variant_id,
                variant_type = EXCLUDED.variant_type,
                variant_subtype = EXCLUDED.variant_subtype,
                variant_foil = EXCLUDED.variant_foil,
                variant_size = EXCLUDED.variant_size,
                variant_stamps = EXCLUDED.variant_stamps,

                condition = EXCLUDED.condition,
                quantity = EXCLUDED.quantity,

                unit_eur = EXCLUDED.unit_eur,
                unit_usd = EXCLUDED.unit_usd,

                deleted_at = NULL,
                updated_at = NOW()

            RETURNING id
            """.trimIndent()
        ).use { statement ->

            statement.setObject(1, newId)
            statement.setObject(2, userId)
            statement.setString(
                3,
                item.key.take(100)
            )

            statement.setString(
                4,
                item.cardId
            )

            statement.setString(
                5,
                item.languageCode
            )

            statement.setString(
                6,
                item.name
            )

            setNullableString(
                statement,
                7,
                item.setId
            )

            setNullableString(
                statement,
                8,
                item.setName
            )

            setNullableString(
                statement,
                9,
                item.localId
            )

            setNullableString(
                statement,
                10,
                item.imageBase
            )

            setNullableString(
                statement,
                11,
                item.imageLanguage
            )

            statement.setString(
                12,
                item.variant
            )

            statement.setString(
                13,
                variantIdentity
            )

            setNullableString(
                statement,
                14,
                item.variantSpec?.id
            )

            setNullableString(
                statement,
                15,
                item.variantSpec?.type
            )

            setNullableString(
                statement,
                16,
                item.variantSpec?.subtype
            )

            setNullableString(
                statement,
                17,
                item.variantSpec?.foil
            )

            setNullableString(
                statement,
                18,
                item.variantSpec?.size
            )

            statement.setString(
                19,
                json.encodeToString(
                    item.variantSpec
                        ?.stamps
                        ?: emptyList()
                )
            )

            statement.setString(
                20,
                item.condition
            )

            statement.setInt(
                21,
                item.quantity
            )

            setNullableDecimal(
                statement,
                22,
                item.unitEur
            )

            setNullableDecimal(
                statement,
                23,
                item.unitUsd
            )

            statement.executeQuery().use {
                    result ->

                check(result.next()) {
                    "Collection item insert returned no ID"
                }

                return UUID.fromString(
                    result.getString("id")
                )
            }
        }
    }

    private fun replaceMarketPrices(
        connection: Connection,
        collectionItemId: UUID,
        item: CollectionItemDto
    ) {

        connection.prepareStatement(
            """
            DELETE FROM market_prices
            WHERE collection_item_id = ?
            """.trimIndent()
        ).use { statement ->

            statement.setObject(
                1,
                collectionItemId
            )

            statement.executeUpdate()
        }

        for (
            (market, value)
            in item.marketUnitEur
        ) {

            val timestamp =
                item.marketUpdatedAtMs[
                    market
                ]
                    ?.takeIf {
                        it > 0L
                    }
                    ?.let {
                        OffsetDateTime.ofInstant(
                            Instant.ofEpochMilli(it),
                            ZoneOffset.UTC
                        )
                    }
                    ?: OffsetDateTime.now(
                        ZoneOffset.UTC
                    )

            connection.prepareStatement(
                """
                INSERT INTO market_prices (
                    id,
                    collection_item_id,
                    market,
                    value_eur,
                    sample_count,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """.trimIndent()
            ).use { statement ->

                statement.setObject(
                    1,
                    UUID.randomUUID()
                )

                statement.setObject(
                    2,
                    collectionItemId
                )

                statement.setString(
                    3,
                    market
                )

                statement.setBigDecimal(
                    4,
                    BigDecimal.valueOf(
                        value
                    )
                )

                val sample =
                    item.marketSampleCount[
                        market
                    ]

                if (sample == null) {
                    statement.setNull(
                        5,
                        Types.INTEGER
                    )
                } else {
                    statement.setInt(
                        5,
                        sample
                    )
                }

                statement.setObject(
                    6,
                    timestamp
                )

                statement.executeUpdate()
            }
        }
    }

    private fun mapCollectionItem(
        result: ResultSet
    ): CollectionItemDto {

        val stamps =
            json.decodeFromString<List<String>>(
                result.getString(
                    "variant_stamps"
                )
            )

        val variantId =
            result.getString(
                "variant_id"
            )

        val variantType =
            result.getString(
                "variant_type"
            )

        val variantSubtype =
            result.getString(
                "variant_subtype"
            )

        val variantFoil =
            result.getString(
                "variant_foil"
            )

        val variantSize =
            result.getString(
                "variant_size"
            )

        val hasExactVariant =
            variantId != null ||
                variantType != null ||
                variantSubtype != null ||
                variantFoil != null ||
                variantSize != null ||
                stamps.isNotEmpty()

        return CollectionItemDto(
            id =
                result.getString("id"),

            key =
                result.getString(
                    "client_key"
                )
                    ?: result.getString(
                        "id"
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

            imageLanguage =
                result.getString(
                    "image_language"
                ),

            variant =
                result.getString(
                    "legacy_variant"
                ),

            variantSpec =
                if (hasExactVariant) {
                    VariantSpecDto(
                        id =
                            variantId
                                ?: result.getString(
                                    "variant_identity"
                                ),

                        type =
                            variantType
                                ?: result.getString(
                                    "legacy_variant"
                                ),

                        foil =
                            variantFoil,

                        size =
                            variantSize,

                        subtype =
                            variantSubtype,

                        stamps =
                            stamps
                    )
                } else {
                    null
                },

            condition =
                result.getString(
                    "condition"
                ),

            quantity =
                result.getInt(
                    "quantity"
                ),

            unitEur =
                result.getBigDecimal(
                    "unit_eur"
                )?.toDouble(),

            unitUsd =
                result.getBigDecimal(
                    "unit_usd"
                )?.toDouble(),

            marketUnitEur =
                json.decodeFromString(
                    result.getString(
                        "market_values"
                    )
                ),

            marketUpdatedAtMs =
                json.decodeFromString(
                    result.getString(
                        "market_updated"
                    )
                ),

            marketSampleCount =
                json.decodeFromString(
                    result.getString(
                        "market_samples"
                    )
                )
        )
    }

    private fun setNullableString(
        statement: java.sql.PreparedStatement,
        index: Int,
        value: String?
    ) {
        if (value == null) {
            statement.setNull(
                index,
                Types.VARCHAR
            )
        } else {
            statement.setString(
                index,
                value
            )
        }
    }

    private fun setNullableDecimal(
        statement: java.sql.PreparedStatement,
        index: Int,
        value: Double?
    ) {
        if (value == null) {
            statement.setNull(
                index,
                Types.NUMERIC
            )
        } else {
            statement.setBigDecimal(
                index,
                BigDecimal.valueOf(
                    value
                )
            )
        }
    }
}
