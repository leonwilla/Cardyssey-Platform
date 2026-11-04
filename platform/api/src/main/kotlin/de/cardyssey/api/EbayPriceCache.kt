package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

data class CachedEbayPrice(
    val cardId: String,
    val languageCode: String,
    val variantId: String,
    val source: String,
    val baseEur: Double,
    val rangeLowEur: Double,
    val rangeHighEur: Double,
    val sampleCount: Int,
    val updatedAtMs: Long,
    val recentSales: List<EbayRecentSaleResponse> = emptyList(),
    val priceWindowDays: Int = 30,
    val priceWindowLabel: String = "30 Tage",
    val lowSample: Boolean = false
)

class EbayPriceCacheRepository(
    private val dataSource: HikariDataSource
) {
    private val json = Json { ignoreUnknownKeys = true }

    fun read(
        cardId: String,
        languageCode: String,
        variantId: String
    ): CachedEbayPrice? =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    card_id,
                    language_code,
                    variant_id,
                    source,
                    base_eur,
                    range_low_eur,
                    range_high_eur,
                    sample_count,
                    updated_at,
                    recent_sales::text AS recent_sales,
                    price_window_days,
                    price_window_label,
                    low_sample
                FROM ebay_price_cache
                WHERE card_id = ?
                  AND language_code = ?
                  AND variant_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, cardId)
                statement.setString(2, languageCode)
                statement.setString(3, variantId)

                statement.executeQuery().use { result ->
                    if (!result.next()) return null

                    val recentSales = runCatching {
                        json.decodeFromString<List<EbayRecentSaleResponse>>(
                            result.getString("recent_sales") ?: "[]"
                        )
                    }.getOrDefault(emptyList())

                    CachedEbayPrice(
                        cardId = result.getString("card_id"),
                        languageCode = result.getString("language_code"),
                        variantId = result.getString("variant_id"),
                        source = result.getString("source"),
                        baseEur = result.getDouble("base_eur"),
                        rangeLowEur = result.getDouble("range_low_eur"),
                        rangeHighEur = result.getDouble("range_high_eur"),
                        sampleCount = result.getInt("sample_count"),
                        updatedAtMs = result
                            .getObject("updated_at", OffsetDateTime::class.java)
                            .toInstant()
                            .toEpochMilli(),
                        recentSales = recentSales.take(10),
                        priceWindowDays = result.getInt("price_window_days"),
                        priceWindowLabel = result.getString("price_window_label") ?: "30 Tage",
                        lowSample = result.getBoolean("low_sample")
                    )
                }
            }
        }

    fun write(price: CachedEbayPrice) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                INSERT INTO ebay_price_cache (
                    card_id,
                    language_code,
                    variant_id,
                    source,
                    base_eur,
                    range_low_eur,
                    range_high_eur,
                    sample_count,
                    updated_at,
                    recent_sales
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?::jsonb)
                ON CONFLICT (card_id, language_code, variant_id)
                DO UPDATE SET
                    source = EXCLUDED.source,
                    base_eur = EXCLUDED.base_eur,
                    range_low_eur = EXCLUDED.range_low_eur,
                    range_high_eur = EXCLUDED.range_high_eur,
                    sample_count = EXCLUDED.sample_count,
                    recent_sales = EXCLUDED.recent_sales,
                    updated_at = NOW()
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, price.cardId)
                statement.setString(2, price.languageCode)
                statement.setString(3, price.variantId)
                statement.setString(4, price.source)
                statement.setDouble(5, price.baseEur)
                statement.setDouble(6, price.rangeLowEur)
                statement.setDouble(7, price.rangeHighEur)
                statement.setInt(8, price.sampleCount)
                statement.setString(9, json.encodeToString(price.recentSales.take(10)))
                statement.executeUpdate()
            }
        }
    }

    fun canRefresh(
        cardId: String,
        languageCode: String,
        variantId: String
    ): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT next_attempt_at <= NOW() AS allowed
                FROM ebay_price_refresh_state
                WHERE card_id = ?
                  AND language_code = ?
                  AND variant_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, cardId)
                statement.setString(2, languageCode)
                statement.setString(3, variantId)

                statement.executeQuery().use { result ->
                    if (result.next()) {
                        result.getBoolean("allowed")
                    } else {
                        true
                    }
                }
            }
        }

    fun recordRefreshSuccess(
        cardId: String,
        languageCode: String,
        variantId: String
    ) {
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                DELETE FROM ebay_price_refresh_state
                WHERE card_id = ?
                  AND language_code = ?
                  AND variant_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, cardId)
                statement.setString(2, languageCode)
                statement.setString(3, variantId)
                statement.executeUpdate()
            }
        }
    }

    fun recordRefreshFailure(
        cardId: String,
        languageCode: String,
        variantId: String
    ) {
        dataSource.connection.use { connection ->
            val currentFailures = connection.prepareStatement(
                """
                SELECT failure_count
                FROM ebay_price_refresh_state
                WHERE card_id = ?
                  AND language_code = ?
                  AND variant_id = ?
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, cardId)
                statement.setString(2, languageCode)
                statement.setString(3, variantId)
                statement.executeQuery().use { result ->
                    if (result.next()) result.getInt("failure_count") else 0
                }
            }

            val failureCount = currentFailures + 1
            val backoffMinutes = when (failureCount) {
                1 -> 1L
                2 -> 5L
                3 -> 15L
                else -> 60L
            }
            val nextAttemptAt = OffsetDateTime
                .now(ZoneOffset.UTC)
                .plusMinutes(backoffMinutes)

            connection.prepareStatement(
                """
                INSERT INTO ebay_price_refresh_state (
                    card_id,
                    language_code,
                    variant_id,
                    failure_count,
                    next_attempt_at,
                    last_failure_at
                )
                VALUES (?, ?, ?, ?, ?, NOW())
                ON CONFLICT (card_id, language_code, variant_id)
                DO UPDATE SET
                    failure_count = EXCLUDED.failure_count,
                    next_attempt_at = EXCLUDED.next_attempt_at,
                    last_failure_at = NOW()
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, cardId)
                statement.setString(2, languageCode)
                statement.setString(3, variantId)
                statement.setInt(4, failureCount)
                statement.setObject(5, nextAttemptAt)
                statement.executeUpdate()
            }
        }
    }
}

interface EbayQuoteProvider {
    suspend fun quote(
        cardId: String,
        language: String,
        variantId: String?,
        legacyVariant: String?,
        condition: PricingCondition
    ): CardPriceQuoteResponse?
}

class SoldCompsEbayQuoteProvider(
    private val delegate: EbaySoldPricingService
) : EbayQuoteProvider {
    override suspend fun quote(
        cardId: String,
        language: String,
        variantId: String?,
        legacyVariant: String?,
        condition: PricingCondition
    ): CardPriceQuoteResponse? =
        delegate.quote(
            cardId = cardId,
            language = language,
            variantId = variantId,
            legacyVariant = legacyVariant,
            condition = condition
        )
}

class CachedEbayPricingService(
    private val catalog: CardCatalogService,
    private val cache: EbayPriceCacheRepository,
    private val providers: List<EbayQuoteProvider>,
    private val cacheTtlMs: Long
) {
    private val refreshLocks =
        ConcurrentHashMap<String, Mutex>()

    suspend fun quote(
        cardId: String,
        language: String,
        variantId: String?,
        legacyVariant: String?,
        condition: PricingCondition
    ): CardPriceQuoteResponse? {
        val details = catalog.details(cardId, language) ?: return null
        val exactLanguageMatch = details.languageCode == language
        val selected = selectVariant(details, variantId, legacyVariant)

        if (!exactLanguageMatch || selected == null) {
            return providers.firstNotNullOfOrNull { provider ->
                runCatching {
                    provider.quote(
                        cardId = cardId,
                        language = language,
                        variantId = variantId,
                        legacyVariant = legacyVariant,
                        condition = condition
                    )
                }.getOrNull()
            } ?: emptyQuote(details, selected, exactLanguageMatch, condition)
        }

        val key = "${details.id}|${details.languageCode}|${selected.id}"
        val cached = cache.read(details.id, details.languageCode, selected.id)

        if (
            cached != null &&
            cached.hasSalesEvidence() &&
            isFresh(cached)
        ) {
            println("eBay pricing cache hit: $key ageMs=${System.currentTimeMillis() - cached.updatedAtMs}")
            return cached.toResponse(details, selected, condition)
        }

        val mutex = refreshLocks.computeIfAbsent(key) { Mutex() }

        return mutex.withLock {
            try {
                val latestCached = cache.read(details.id, details.languageCode, selected.id)
                if (
                    latestCached != null &&
                    latestCached.hasSalesEvidence() &&
                    isFresh(latestCached)
                ) {
                    return@withLock latestCached.toResponse(details, selected, condition)
                }

                if (!cache.canRefresh(details.id, details.languageCode, selected.id)) {
                    println("eBay pricing refresh backoff active: $key")
                    return@withLock latestCached
                        ?.takeIf {
                            it.hasSalesEvidence()
                        }
                        ?.toResponse(
                            details,
                            selected,
                            condition
                        )
                        ?: emptyQuote(
                            details,
                            selected,
                            true,
                            condition
                        )
                }

                val live = providers.firstNotNullOfOrNull { provider ->
                    runCatching {
                        provider.quote(
                            cardId = cardId,
                            language = language,
                            variantId = selected.id,
                            legacyVariant = null,
                            condition = condition
                        )
                    }.getOrNull()?.takeIf {
                        it.hasSalesEvidence()
                    }
                }

                if (live != null) {
                    live.toCacheRecord(condition)?.let(cache::write)
                    cache.recordRefreshSuccess(details.id, details.languageCode, selected.id)
                    return@withLock live
                }

                cache.recordRefreshFailure(details.id, details.languageCode, selected.id)

                if (
                    latestCached != null &&
                    latestCached.hasSalesEvidence()
                ) {
                    println(
                        "eBay pricing cache stale fallback: $key ageMs=" +
                            (System.currentTimeMillis() - latestCached.updatedAtMs)
                    )
                    return@withLock latestCached.toResponse(details, selected, condition)
                }

                emptyQuote(details, selected, true, condition)
            } finally {
                refreshLocks.remove(key, mutex)
            }
        }
    }

    private fun isFresh(price: CachedEbayPrice): Boolean =
        System.currentTimeMillis() - price.updatedAtMs <= cacheTtlMs

    private fun CardPriceQuoteResponse.hasSalesEvidence(): Boolean =
        baseEur?.let {
            it.isFinite() && it > 0.0
        } == true &&
            sampleCount?.let { it > 0 } == true &&
            recentSales.any {
                it.soldPriceEur.isFinite() &&
                    it.soldPriceEur > 0.0
            }

    private fun CardPriceQuoteResponse.toCacheRecord(
        condition: PricingCondition
    ): CachedEbayPrice? {
        val base = baseEur ?: return null
        val sourceName = source?.takeIf(String::isNotBlank) ?: return null
        val variant = variantId?.takeIf(String::isNotBlank) ?: return null
        val samples = sampleCount?.takeIf { it > 0 } ?: return null
        val sales =
            recentSales
                .filter {
                    it.soldPriceEur.isFinite() &&
                        it.soldPriceEur > 0.0
                }
                .take(10)

        if (sales.isEmpty()) {
            return null
        }

        val factor = condition.factor.takeIf { it > 0.0 } ?: return null
        val low = rangeLowEur?.div(factor) ?: return null
        val high = rangeHighEur?.div(factor) ?: return null

        if (
            !base.isFinite() || base <= 0.0 ||
            !low.isFinite() || low <= 0.0 ||
            !high.isFinite() || high <= 0.0 ||
            low > high
        ) {
            return null
        }

        return CachedEbayPrice(
            cardId = cardId,
            languageCode = languageCode,
            variantId = variant,
            source = sourceName,
            baseEur = base,
            rangeLowEur = low,
            rangeHighEur = high,
            sampleCount = samples,
            updatedAtMs = updatedAtMs ?: System.currentTimeMillis(),
            recentSales = sales
        )
    }

    private fun CachedEbayPrice.hasSalesEvidence(): Boolean =
        source == "CARDYSSEY_EBAY" &&
            sampleCount > 0 &&
            recentSales.any {
                it.soldPriceEur.isFinite() &&
                    it.soldPriceEur > 0.0
            }

    private fun CachedEbayPrice.toResponse(
        details: CatalogCardDetails,
        selected: CatalogVariant,
        condition: PricingCondition
    ): CardPriceQuoteResponse =
        CardPriceQuoteResponse(
            cardId = details.id,
            languageCode = details.languageCode,
            variantId = selected.id,
            variantType = selected.type,
            condition = condition.name,
            market = "EBAY",
            source = source,
            baseEur = baseEur,
            conditionFactor = condition.factor,
            eur = baseEur * condition.factor,
            exactLanguageMatch = true,
            exactVariantMatch = true,
            sampleCount = sampleCount,
            rangeLowEur = rangeLowEur * condition.factor,
            rangeHighEur = rangeHighEur * condition.factor,
            updatedAtMs = updatedAtMs,
            recentSales = recentSales.take(10),
            priceWindowDays = priceWindowDays,
            priceWindowLabel = priceWindowLabel,
            lowSample = lowSample
        )

    private fun emptyQuote(
        details: CatalogCardDetails,
        selected: CatalogVariant?,
        exactLanguageMatch: Boolean,
        condition: PricingCondition
    ): CardPriceQuoteResponse =
        CardPriceQuoteResponse(
            cardId = details.id,
            languageCode = details.languageCode,
            variantId = selected?.id,
            variantType = selected?.type,
            condition = condition.name,
            market = "EBAY",
            source = null,
            baseEur = null,
            conditionFactor = condition.factor,
            eur = null,
            exactLanguageMatch = exactLanguageMatch,
            exactVariantMatch = selected != null
        )

    private fun selectVariant(
        details: CatalogCardDetails,
        variantId: String?,
        legacyVariant: String?
    ): CatalogVariant? {
        if (!variantId.isNullOrBlank()) {
            return details.variants.firstOrNull { it.id == variantId.trim() }
        }

        val legacy = legacyVariant
            ?.trim()
            ?.uppercase(Locale.ROOT)
            ?.takeIf(String::isNotBlank)

        if (legacy != null) {
            return details.variants
                .filter { it.legacyVariant == legacy }
                .singleOrNull()
        }

        return details.variants.singleOrNull()
    }
}
