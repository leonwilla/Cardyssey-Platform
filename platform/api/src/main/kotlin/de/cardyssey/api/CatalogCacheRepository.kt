package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource

class CatalogCacheRepository(
    private val dataSource: HikariDataSource
) {

    fun read(key: String, maxAgeHours: Long? = null): String? =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT payload
                FROM catalog_cache
                WHERE cache_key = ?
                  AND (CAST(? AS BIGINT) IS NULL OR updated_at >= NOW() - CAST(? AS BIGINT) * INTERVAL '1 hour')
                """.trimIndent()
            ).use { statement ->

                statement.setString(1, key)
                statement.setObject(2, maxAgeHours)
                statement.setObject(3, maxAgeHours)

                statement.executeQuery().use { result ->
                    if (result.next()) {
                        result.getString("payload")
                    } else {
                        null
                    }
                }
            }
        }

    fun write(
        key: String,
        payload: String
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO catalog_cache (
                    cache_key,
                    payload,
                    updated_at
                )
                VALUES (?, ?, NOW())
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
                """.trimIndent()
            ).use { statement ->

                statement.setString(1, key)
                statement.setString(2, payload)
                statement.executeUpdate()
            }
        }
    }
}
