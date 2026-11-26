package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.coroutines.delay
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.DayOfWeek
import java.time.LocalTime

/** Missing prices fill continuously; existing prices refresh in the Sunday UTC lane. */
/** DE/EN prices come only from the Cardmarket pipeline, never from this worker. */
internal val CARDMARKET_ONLY_LANGUAGES = setOf("de", "en")

/** TCGdex is no price source any more (owner decision 24.11.2026). */
internal fun isRetiredPriceSource(source: String?): Boolean =
    source?.uppercase()?.startsWith("TCGDEX") == true

internal fun workerPriceLanguages(languages: List<String>): List<String> =
    languages.filterNot { it.lowercase() in CARDMARKET_ONLY_LANGUAGES }

internal fun weeklyPriceRefreshAllowed(
    now: OffsetDateTime = OffsetDateTime.now(ZoneOffset.UTC)
): Boolean {
    val utc = now.withOffsetSameInstant(ZoneOffset.UTC)
    return utc.dayOfWeek == DayOfWeek.SUNDAY &&
        !utc.toLocalTime().isBefore(LocalTime.of(4, 17))
}

data class CachedTcgPrice(
    val cardId: String,
    val languageCode: String,
    val variantId: String,
    val legacyVariant: String,
    val source: String?,
    val baseEur: Double?,
    val resolutionStatus: String,
    val failureDetail: String?,
    val updatedAtMs: Long,
    val providerUrl: String? = null
)

data class TcgPriceRefreshTarget(
    val cardId: String,
    val languageCode: String,
    val variantId: String,
    val legacyVariant: String
)

data class TcgPriceStatistics(
    val lowEur: Double?,
    val highEur: Double?,
    val trend30dPercent: Double?
)

internal fun TcgPriceStatistics.forCondition(condition: PricingCondition): TcgPriceStatistics =
    copy(
        lowEur = lowEur?.let { roundedUnitEur(it, condition.factor) },
        highEur = highEur?.let { roundedUnitEur(it, condition.factor) }
    )

class TcgPriceCacheRepository(
    private val dataSource: HikariDataSource
) {
    /** Card-level reference quote, explicitly NOT a verified printing/condition price. */
    fun reference(cardId: String, languageCode: String, variantId: String): Triple<Double, Long, String>? =
        dataSource.connection.use { connection ->
            connection.prepareStatement("""
                SELECT r.price_eur,r.observed_at,r.provider,r.evidence->>'basis' AS basis,r.evidence->>'n' AS n
                FROM price_reference_candidates r
                LEFT JOIN tcg_price_cache c
                  ON c.card_id=r.card_id AND c.language_code=r.language_code AND c.variant_id=r.variant_id
                WHERE r.card_id=? AND r.language_code=? AND r.variant_id=?
                  AND r.provider IN ('POKEMONTCGAPI_REFERENCE','CARDYSSEY_REFERENCE')
                  AND r.price_eur>0
                  AND (c.resolution_status IS NULL OR c.resolution_status<>'PRICE_FOUND')
                ORDER BY (r.provider='CARDYSSEY_REFERENCE') DESC, r.observed_at DESC LIMIT 1
            """.trimIndent()).use { statement ->
                statement.setString(1,cardId)
                statement.setString(2,languageCode)
                statement.setString(3,variantId)
                statement.executeQuery().use { rs ->
                    if (!rs.next()) null else Triple(
                        rs.getBigDecimal("price_eur").toDouble(),
                        rs.getObject("observed_at", OffsetDateTime::class.java).toInstant().toEpochMilli(),
                        referenceNote(rs.getString("provider"), rs.getString("basis"), rs.getString("n"))
                    )
                }
            }
        }

    private fun referenceNote(provider: String, basis: String?, n: String?): String = when {
        provider != "CARDYSSEY_REFERENCE" ->
            "Englischer Karten-Richtwert; Druckvariante und Zustand ungeprüft. Kein bestätigter Marktpreis."
        basis == "ja_same_card" ->
            "Richtwert aus der japanischen Ausgabe derselben Karte (CardTrader). Für diese Sprache gibt es keinen Marktpreis."
        else ->
            "Richtwert: üblicher Preis dieser Seltenheit" + (if (basis == "set_rarity") " im Set" else "") +
                (n?.let { " ($it Karten)" } ?: "") + ". Für diese Karte gibt es keinen eigenen Marktpreis."
    }

    fun read(
        cardId: String,
        languageCode: String,
        variantId: String
    ): CachedTcgPrice? =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    card_id,
                    language_code,
                    variant_id,
                    legacy_variant,
                    source,
                    base_eur,
                    resolution_status,
                    failure_detail,
                    updated_at,
                    provider_url
                FROM tcg_price_cache
                WHERE card_id = ?
                  AND language_code = ?
                  AND variant_id = ?
                  AND (source IS NULL OR source NOT LIKE 'TCGDEX%')
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, cardId)
                statement.setString(2, languageCode)
                statement.setString(3, variantId)

                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        return null
                    }

                    CachedTcgPrice(
                        cardId =
                            result.getString("card_id"),
                        languageCode =
                            result.getString("language_code"),
                        variantId =
                            result.getString("variant_id"),
                        legacyVariant =
                            result.getString("legacy_variant"),
                        source =
                            result.getString("source"),
                        baseEur =
                            result.getBigDecimal("base_eur")
                                ?.toDouble(),
                        resolutionStatus =
                            result.getString("resolution_status")
                                ?: "NO_PRICE",
                        failureDetail =
                            result.getString("failure_detail"),
                        providerUrl =
                            result.getString("provider_url"),
                        updatedAtMs =
                            result
                                .getObject(
                                    "updated_at",
                                    OffsetDateTime::class.java
                                )
                                .toInstant()
                                .toEpochMilli()
                    )
                }
            }
        }

    fun readByLegacyVariant(
        cardId: String,
        languageCode: String,
        legacyVariant: String
    ): CachedTcgPrice? =
        dataSource.connection.use {
            connection ->
            connection.prepareStatement(
                """
                SELECT
                    card_id,
                    language_code,
                    variant_id,
                    legacy_variant,
                    source,
                    base_eur,
                    resolution_status,
                    failure_detail,
                    updated_at,
                    provider_url
                FROM tcg_price_cache
                WHERE card_id = ?
                  AND language_code = ?
                  AND legacy_variant = ?
                  AND (source IS NULL OR source NOT LIKE 'TCGDEX%')
                ORDER BY updated_at DESC
                """.trimIndent()
            ).use {
                statement ->
                statement.setString(
                    1,
                    cardId
                )
                statement.setString(
                    2,
                    languageCode
                )
                statement.setString(
                    3,
                    legacyVariant.uppercase()
                )

                statement.executeQuery().use {
                    result ->
                    if (!result.next()) {
                        return null
                    }

                    val first =
                        CachedTcgPrice(
                            cardId =
                                result.getString(
                                    "card_id"
                                ),
                            languageCode =
                                result.getString(
                                    "language_code"
                                ),
                            variantId =
                                result.getString(
                                    "variant_id"
                                ),
                            legacyVariant =
                                result.getString(
                                    "legacy_variant"
                                ),
                            source =
                                result.getString(
                                    "source"
                                ),
                            baseEur =
                                result.getBigDecimal(
                                    "base_eur"
                                )?.toDouble(),
                            resolutionStatus =
                                result.getString(
                                    "resolution_status"
                                ) ?: "NO_PRICE",
                            failureDetail =
                                result.getString(
                                    "failure_detail"
                                ),
                            providerUrl =
                                result.getString("provider_url"),
                            updatedAtMs =
                                result.getObject(
                                    "updated_at",
                                    OffsetDateTime::class.java
                                )
                                    .toInstant()
                                    .toEpochMilli()
                        )

                    /*
                     * Legacy identities are safe only if exactly one physical
                     * variant maps to them. Otherwise we intentionally return
                     * no price instead of silently valuing the wrong print.
                     */
                    if (result.next()) {
                        null
                    } else {
                        first
                    }
                }
            }
        }

    fun statistics(
        cardId: String,
        languageCode: String,
        variantId: String
    ): TcgPriceStatistics =
        dataSource.connection.use {
            connection ->
            val current =
                read(
                    cardId =
                        cardId,
                    languageCode =
                        languageCode,
                    variantId =
                        variantId
                )?.baseEur

            val values =
                connection.prepareStatement(
                    """
                    SELECT
                        MIN(base_eur) AS low_eur,
                        MAX(base_eur) AS high_eur
                    FROM tcg_price_history
                    WHERE card_id = ?
                      AND language_code = ?
                      AND variant_id = ?
                      AND captured_at >= NOW() - INTERVAL '30 days'
                    """.trimIndent()
                ).use {
                    statement ->
                    statement.setString(
                        1,
                        cardId
                    )
                    statement.setString(
                        2,
                        languageCode
                    )
                    statement.setString(
                        3,
                        variantId
                    )

                    statement.executeQuery()
                        .use {
                            result ->
                            if (
                                result.next()
                            ) {
                                result.getBigDecimal(
                                    "low_eur"
                                )
                                    ?.toDouble() to
                                    result.getBigDecimal(
                                        "high_eur"
                                    )
                                        ?.toDouble()
                            } else {
                                null to null
                            }
                        }
                }

            val baseline =
                connection.prepareStatement(
                    """
                    SELECT base_eur
                    FROM tcg_price_history
                    WHERE card_id = ?
                      AND language_code = ?
                      AND variant_id = ?
                      AND captured_at <= NOW() - INTERVAL '30 days'
                    ORDER BY captured_at DESC
                    LIMIT 1
                    """.trimIndent()
                ).use {
                    statement ->
                    statement.setString(
                        1,
                        cardId
                    )
                    statement.setString(
                        2,
                        languageCode
                    )
                    statement.setString(
                        3,
                        variantId
                    )

                    statement.executeQuery()
                        .use {
                            result ->
                            if (
                                result.next()
                            ) {
                                result.getBigDecimal(
                                    "base_eur"
                                )
                                    ?.toDouble()
                            } else {
                                null
                            }
                        }
                }

            val trend =
                if (
                    current != null &&
                    baseline != null &&
                    baseline > 0.0
                ) {
                    (
                        (
                            current -
                                baseline
                            ) /
                            baseline *
                            100.0
                        )
                        .let {
                            kotlin.math.round(
                                it * 10.0
                            ) / 10.0
                        }
                } else {
                    null
                }

            TcgPriceStatistics(
                lowEur =
                    values.first
                        ?: current,
                highEur =
                    values.second
                        ?: current,
                trend30dPercent =
                    trend
            )
        }

    fun write(
        target: TcgPriceRefreshTarget,
        source: String?,
        baseEur: Double?,
        resolutionStatus: String,
        failureDetail: String?,
        retryAfterHours: Long,
        allowExistingPrices: Boolean = weeklyPriceRefreshAllowed()
    ) {
        val normalized =
            baseEur
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }

        dataSource.connection.use { connection ->
            val written = connection.prepareStatement(
                """
                INSERT INTO tcg_price_cache (
                    card_id,
                    language_code,
                    variant_id,
                    legacy_variant,
                    source,
                    base_eur,
                    resolution_status,
                    failure_detail,
                    updated_at,
                    next_attempt_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, NOW(),
                    NOW() + (? * INTERVAL '1 hour')
                )
                ON CONFLICT (card_id, language_code, variant_id)
                DO UPDATE SET
                    legacy_variant = EXCLUDED.legacy_variant,
                    source = EXCLUDED.source,
                    base_eur = EXCLUDED.base_eur,
                    resolution_status = EXCLUDED.resolution_status,
                    failure_detail = EXCLUDED.failure_detail,
                    updated_at = NOW(),
                    next_attempt_at = EXCLUDED.next_attempt_at
                WHERE ? OR COALESCE(tcg_price_cache.base_eur, 0) <= 0
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, target.cardId)
                statement.setString(2, target.languageCode)
                statement.setString(3, target.variantId)
                statement.setString(4, target.legacyVariant)
                statement.setString(5, source)

                if (normalized == null) {
                    statement.setNull(
                        6,
                        java.sql.Types.NUMERIC
                    )
                } else {
                    statement.setDouble(
                        6,
                        normalized
                    )
                }

                statement.setString(
                    7,
                    resolutionStatus
                )
                statement.setString(
                    8,
                    failureDetail
                )
                statement.setLong(
                    9,
                    retryAfterHours.coerceAtLeast(1L)
                )

                statement.setBoolean(10, allowExistingPrices)
                statement.executeUpdate()
            }

            if (
                normalized != null && written > 0
            ) {
                connection.prepareStatement(
                    """
                    INSERT INTO tcg_price_history (
                        card_id,
                        language_code,
                        variant_id,
                        source,
                        base_eur,
                        captured_at
                    )
                    VALUES (?, ?, ?, ?, ?, NOW())
                    """.trimIndent()
                ).use {
                    statement ->
                    statement.setString(
                        1,
                        target.cardId
                    )
                    statement.setString(
                        2,
                        target.languageCode
                    )
                    statement.setString(
                        3,
                        target.variantId
                    )
                    statement.setString(
                        4,
                        source
                    )
                    statement.setDouble(
                        5,
                        normalized
                    )
                    statement.executeUpdate()
                }
            }
        }
    }

    fun deferExistingPrice(
        target: TcgPriceRefreshTarget,
        failureDetail: String?,
        retryAfterHours: Long
    ): Boolean =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                UPDATE tcg_price_cache
                SET legacy_variant = ?,
                    failure_detail =
                        CASE
                            WHEN source = 'TCGCSV_TCGPLAYER'
                                THEN failure_detail
                            ELSE ?
                        END,
                    next_attempt_at =
                        NOW() + (? * INTERVAL '1 hour')
                WHERE card_id = ?
                  AND language_code = ?
                  AND variant_id = ?
                  AND resolution_status = 'PRICE_FOUND'
                  AND base_eur IS NOT NULL
                """.trimIndent()
            ).use { statement ->
                statement.setString(1, target.legacyVariant)
                statement.setString(2, failureDetail)
                statement.setLong(
                    3,
                    retryAfterHours.coerceAtLeast(1L)
                )
                statement.setString(4, target.cardId)
                statement.setString(5, target.languageCode)
                statement.setString(6, target.variantId)
                statement.executeUpdate() > 0
            }
        }

    fun dueTargets(
        languages: List<String>,
        ttlHours: Long,
        limit: Int,
        allowExistingPrices: Boolean = weeklyPriceRefreshAllowed()
    ): List<TcgPriceRefreshTarget> {
        if (languages.isEmpty()) {
            return emptyList()
        }

        val placeholders =
            languages.joinToString(",") {
                "?"
            }

        val missingOnlyClause =
            if (allowExistingPrices) "" else "AND COALESCE(p.base_eur, 0) <= 0"

        val sql =
            """
            SELECT
                c.card_id,
                c.language_code,
                v.value ->> 'id' AS variant_id,
                v.value ->> 'legacyVariant' AS legacy_variant
            FROM catalog_cards_mirror c
            CROSS JOIN LATERAL
                jsonb_array_elements(c.variants) AS v(value)
            LEFT JOIN tcg_price_cache p
              ON p.card_id = c.card_id
             AND p.language_code = c.language_code
             AND p.variant_id = v.value ->> 'id'
            WHERE c.details_complete = TRUE
              AND c.language_code IN ($placeholders)
              AND COALESCE(v.value ->> 'id', '') <> ''
              AND COALESCE(v.value ->> 'legacyVariant', '') <> ''
              /*
               * Pocket sets are digital and do not have a physical TCG market.
               * Skipping them keeps Cardmarket/TCGPlayer/JustTCG quota focused
               * on cards that can actually receive a physical market value.
               */
              AND c.set_id !~ '^(A[0-9]|B[0-9]|P-A)'
              $missingOnlyClause
              AND (
                    p.next_attempt_at IS NULL
                    OR p.next_attempt_at <= NOW()
                  )
            ORDER BY
                /*
                 * Fill cards that still have no usable value before refreshing
                 * already-priced variants. This is especially important for
                 * the limited JustTCG fallback budget.
                 */
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM tcg_price_cache priced
                        WHERE priced.card_id = c.card_id
                          AND priced.language_code = c.language_code
                          AND priced.resolution_status = 'PRICE_FOUND'
                    ) THEN 1
                    ELSE 0
                END,
                CASE p.resolution_status
                    WHEN 'NO_PRICE' THEN 0
                    WHEN 'PROVIDER_ERROR' THEN 1
                    WHEN 'NO_VARIANT_MATCH' THEN 2
                    WHEN 'PRICE_FOUND' THEN 3
                    ELSE 0
                END,
                /*
                 * Interleave languages inside the same priority bucket so the
                 * global JustTCG daily budget cannot be consumed by German or
                 * English leftovers before Japanese/Chinese cards are reached.
                 */
                ROW_NUMBER() OVER (
                    PARTITION BY c.language_code
                    ORDER BY
                        p.updated_at NULLS FIRST,
                        c.card_id,
                        v.value ->> 'id'
                ),
                CASE c.language_code
                    WHEN 'de' THEN 0
                    WHEN 'en' THEN 1
                    WHEN 'ja' THEN 2
                    WHEN 'ko' THEN 3
                    WHEN 'zh-tw' THEN 4
                    WHEN 'zh-cn' THEN 5
                    ELSE 9
                END,
                p.updated_at NULLS FIRST,
                c.language_code,
                c.card_id,
                v.value ->> 'id'
            LIMIT ?
            """.trimIndent()

        return dataSource.connection.use { connection ->
            connection.prepareStatement(
                sql
            ).use { statement ->
                var index = 1

                languages.forEach {
                    statement.setString(
                        index++,
                        it
                    )
                }

                statement.setInt(
                    index,
                    limit.coerceIn(
                        1,
                        2_000
                    )
                )

                statement.executeQuery().use { result ->
                    buildList {
                        while (result.next()) {
                            add(
                                TcgPriceRefreshTarget(
                                    cardId =
                                        result.getString(
                                            "card_id"
                                        ),
                                    languageCode =
                                        result.getString(
                                            "language_code"
                                        ),
                                    variantId =
                                        result.getString(
                                            "variant_id"
                                        ),
                                    legacyVariant =
                                        result.getString(
                                            "legacy_variant"
                                        )
                                )
                            )
                        }
                    }
                }
            }
        }
    }

    fun status(): Pair<Long, Long> =
        dataSource.connection.use { connection ->
            connection.prepareStatement(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (
                        WHERE p.resolution_status = 'PRICE_FOUND'
                          AND p.base_eur IS NOT NULL
                    ) AS priced
                FROM catalog_cards_mirror c
                CROSS JOIN LATERAL
                    jsonb_array_elements(c.variants) AS v(value)
                LEFT JOIN tcg_price_cache p
                  ON p.card_id = c.card_id
                 AND p.language_code = c.language_code
                 AND p.variant_id = v.value ->> 'id'
                WHERE c.details_complete = TRUE
                  AND COALESCE(v.value ->> 'id', '') <> ''
                  AND c.set_id !~ '^(A[0-9]|B[0-9]|P-A)'
                """.trimIndent()
            ).use { statement ->
                statement.executeQuery().use { result ->
                    if (!result.next()) {
                        0L to 0L
                    } else {
                        result.getLong("total") to
                            result.getLong("priced")
                    }
                }
            }
        }
}

/**
 * Public requests are cache-only. This guarantees that opening a collection,
 * scanner result or card detail can never consume TCGdex/JustTCG quota.
 *
 * The worker is the only caller allowed to use live providers.
 */
class CachedTcgPricingService(
    private val catalog: CardCatalogService,
    private val cache: TcgPriceCacheRepository,
    private val livePricing: CardPricingService,
    private val languages: List<String>,
    private val cacheTtlHours: Long,
    private val batchSize: Int,
    private val requestSpacingMs: Long,
    private val justTcgFallbacksPerDay: Int,
    private val missingRetryHours: Long,
    private val providerErrorRetryHours: Long
) {
    @Volatile
    private var fallbackDay: String =
        ""

    @Volatile
    private var fallbackCount: Int =
        0

    suspend fun quote(
        cardId: String,
        language: String,
        variantId: String?,
        legacyVariant: String?,
        condition: PricingCondition
    ): CardPriceQuoteResponse? {
        val details =
            catalog.details(
                cardId = cardId,
                language = language
            ) ?: return null

        val exactLanguageMatch =
            details.languageCode ==
                language

        val selected =
            selectVariant(
                details = details,
                variantId = variantId,
                legacyVariant =
                    legacyVariant
            )

        if (
            !exactLanguageMatch ||
            selected == null
        ) {
            return emptyQuote(
                details = details,
                selected = selected,
                condition = condition,
                exactLanguageMatch =
                    exactLanguageMatch
            )
        }

        val cached =
            cache.read(
                cardId = details.id,
                languageCode =
                    details.languageCode,
                variantId =
                    selected.id
            )

        return if (
            cached != null &&
            !isRetiredPriceSource(cached.source)
        ) {
            cached.toResponse(
                details = details,
                selected = selected,
                condition = condition
            )
        } else {
            emptyQuote(
                details = details,
                selected = selected,
                condition = condition,
                exactLanguageMatch = true
            )
        }
    }

    suspend fun runForever() {
        /*
         * Give Flyway/catalog startup a short head start. After that this loop
         * continuously fills missing rows. Existing positive prices are only
         * eligible in the Sunday 04:17–24:00 UTC weekly refresh lane.
         */
        delay(
            15_000L
        )

        while (true) {
            try {
                val targets =
                    cache.dueTargets(
                        languages =
                            workerPriceLanguages(languages),
                        ttlHours =
                            cacheTtlHours,
                        limit =
                            batchSize
                    )

                if (
                    targets.isEmpty()
                ) {
                    delay(
                        15L *
                            60L *
                            1000L
                    )
                    continue
                }

                for (target in targets) {
                    refreshTarget(
                        target
                    )

                    delay(
                        requestSpacingMs
                    )
                }
            } catch (error: Throwable) {
                println(
                    "TCG price worker error: " +
                        (
                            error.message
                                ?: error::class.java
                                    .simpleName
                            )
                )

                delay(
                    60_000L
                )
            }
        }
    }

    private suspend fun refreshTarget(
        target: TcgPriceRefreshTarget
    ) {
        // Recheck queued targets before any provider request; a recovery import
        // may have filled this price after the batch was selected.
        if (!weeklyPriceRefreshAllowed() &&
            (cache.read(target.cardId, target.languageCode, target.variantId)?.baseEur ?: 0.0) > 0.0
        ) return

        val details =
            runCatching {
                catalog.details(
                    cardId =
                        target.cardId,
                    language =
                        target.languageCode
                )
            }

        val detailsValue =
            details.getOrNull()

        if (detailsValue == null) {
            val status =
                if (details.isFailure) {
                    "PROVIDER_ERROR"
                } else {
                    "NO_VARIANT_MATCH"
                }
            val retryHours =
                if (details.isFailure) {
                    providerErrorRetryHours
                } else {
                    missingRetryHours
                }

            recordUnresolved(
                target = target,
                status = status,
                failureDetail =
                    details.exceptionOrNull()?.message
                        ?: "Card details unavailable during refresh",
                retryAfterHours = retryHours
            )
            return
        }

        val exactSelected =
            detailsValue.variants
                .firstOrNull {
                    it.id ==
                        target.variantId
                }

        val selected =
            exactSelected
                ?: detailsValue.variants
                    .filter {
                        it.legacyVariant ==
                            target.legacyVariant
                    }
                    .singleOrNull()

        if (selected == null) {
            recordUnresolved(
                target = target,
                status = "NO_VARIANT_MATCH",
                failureDetail =
                    "No exact or unique legacy-family variant in current catalog details",
                retryAfterHours = missingRetryHours
            )
            return
        }

        val primaryResult =
            runCatching {
                livePricing.quote(
                    cardId =
                        target.cardId,
                    language =
                        target.languageCode,
                    variantId =
                        selected.id,
                    legacyVariant =
                        null,
                    condition =
                        PricingCondition.MINT,
                    includeFallbackProviders =
                        false
                )
            }

        if (primaryResult.isFailure) {
            recordUnresolved(
                target = target,
                status = "PROVIDER_ERROR",
                failureDetail =
                    primaryResult.exceptionOrNull()?.message
                        ?: "Primary pricing provider failed",
                retryAfterHours = providerErrorRetryHours
            )
            return
        }

        var resolved =
            primaryResult.getOrNull()

        /*
         * If the exact physical variant has no own price, reuse a TCGdex
         * catalog value only inside the same legacy family. This never crosses
         * NORMAL / HOLO / REVERSE. We also require one unambiguous positive
         * value across that family; conflicting prices are intentionally not
         * guessed.
         */
        if (
            resolved?.baseEur == null
        ) {
            val familyValues =
                detailsValue.variants
                    .asSequence()
                    .filter {
                        it.legacyVariant ==
                            selected.legacyVariant
                    }
                    .mapNotNull {
                        it.tcgDexEur
                            ?.takeIf {
                                value ->
                                value.isFinite() &&
                                    value > 0.0
                            }
                    }
                    .map {
                        kotlin.math.round(
                            it * 10_000.0
                        ) / 10_000.0
                    }
                    .distinct()
                    .toList()

            if (
                familyValues.size ==
                    1
            ) {
                resolved =
                    CardPriceQuoteResponse(
                        cardId =
                            detailsValue.id,
                        languageCode =
                            detailsValue.languageCode,
                        variantId =
                            selected.id,
                        variantType =
                            selected.type,
                        condition =
                            PricingCondition.MINT.name,
                        market =
                            "TCG",
                        source =
                            "TCGDEX_FAMILY",
                        baseEur =
                            familyValues.single(),
                        conditionFactor =
                            PricingCondition.MINT.factor,
                        eur =
                            familyValues.single(),
                        exactLanguageMatch =
                            true,
                        exactVariantMatch =
                            true
                    )
            }
        }

        val fallbackEligible =
            selected.stamps.isEmpty() &&
                selected.subtype.isNullOrBlank() &&
                selected.foil.isNullOrBlank() &&
                (
                    selected.size.isNullOrBlank() ||
                        selected.size.equals("standard", ignoreCase = true)
                    )

        if (
            resolved?.baseEur == null &&
            fallbackEligible &&
            claimFallbackSlot()
        ) {
            val fallback =
                runCatching {
                    livePricing.quote(
                        cardId =
                            target.cardId,
                        language =
                            target.languageCode,
                        variantId =
                            selected.id,
                        legacyVariant =
                            null,
                        condition =
                            PricingCondition.MINT,
                        includeFallbackProviders =
                            true
                    )
                }

            if (fallback.isFailure) {
                recordUnresolved(
                    target = target,
                    status = "PROVIDER_ERROR",
                    failureDetail =
                        fallback.exceptionOrNull()?.message
                            ?: "Fallback pricing provider failed",
                    retryAfterHours = providerErrorRetryHours
                )
                return
            }

            resolved =
                fallback.getOrNull()
        }

        val price =
            resolved?.baseEur
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }

        if (price != null) {
            cache.write(
                target = target,
                source = resolved?.source,
                baseEur = price,
                resolutionStatus = "PRICE_FOUND",
                failureDetail = null,
                retryAfterHours = cacheTtlHours
            )

            logResolution(
                target = target,
                status = "PRICE_FOUND",
                source = resolved?.source,
                price = price
            )
        } else {
            recordUnresolved(
                target = target,
                status = "NO_PRICE",
                failureDetail =
                    "No current provider price during refresh",
                retryAfterHours = missingRetryHours
            )
        }
    }

    private fun recordUnresolved(
        target: TcgPriceRefreshTarget,
        status: String,
        failureDetail: String?,
        retryAfterHours: Long
    ) {
        if (!weeklyPriceRefreshAllowed() &&
            (cache.read(target.cardId, target.languageCode, target.variantId)?.baseEur ?: 0.0) > 0.0
        ) return

        val preserved =
            cache.deferExistingPrice(
                target = target,
                failureDetail = failureDetail,
                retryAfterHours = retryAfterHours
            )

        if (!preserved) {
            cache.write(
                target = target,
                source = null,
                baseEur = null,
                resolutionStatus = status,
                failureDetail = failureDetail,
                retryAfterHours = retryAfterHours
            )
        }

        logResolution(
            target = target,
            status =
                if (preserved) {
                    "PRICE_FOUND_STALE"
                } else {
                    status
                },
            source = null,
            price = null
        )
    }

    private fun logResolution(
        target: TcgPriceRefreshTarget,
        status: String,
        source: String?,
        price: Double?
    ) {
        println(
            "TCG price worker: " +
                "${target.languageCode} " +
                "${target.cardId} " +
                "${target.variantId} " +
                "status=$status " +
                "source=${source ?: "NONE"} " +
                "price=${price ?: "-"}"
        )
    }

    @Synchronized
    private fun claimFallbackSlot():
        Boolean {

        if (
            justTcgFallbacksPerDay <= 0
        ) {
            return false
        }

        val today =
            java.time.LocalDate
                .now(
                    ZoneOffset.UTC
                )
                .toString()

        if (
            fallbackDay !=
                today
        ) {
            fallbackDay =
                today
            fallbackCount =
                0
        }

        if (
            fallbackCount >=
                justTcgFallbacksPerDay
        ) {
            return false
        }

        fallbackCount += 1
        return true
    }

    private fun selectVariant(
        details: CatalogCardDetails,
        variantId: String?,
        legacyVariant: String?
    ): CatalogVariant? {
        if (
            !variantId.isNullOrBlank()
        ) {
            return details.variants
                .firstOrNull {
                    it.id ==
                        variantId.trim()
                }
        }

        val legacy =
            legacyVariant
                ?.trim()
                ?.uppercase()
                ?.takeIf(
                    String::isNotBlank
                )

        if (legacy != null) {
            return details.variants
                .filter {
                    it.legacyVariant ==
                        legacy
                }
                .singleOrNull()
        }

        return details.variants
            .singleOrNull()
    }

    private fun CachedTcgPrice.toResponse(
        details: CatalogCardDetails,
        selected: CatalogVariant,
        condition: PricingCondition
    ): CardPriceQuoteResponse {
        val statistics =
            cache.statistics(
                cardId =
                    details.id,
                languageCode =
                    details.languageCode,
                variantId =
                    selected.id
            ).forCondition(condition)

        return CardPriceQuoteResponse(
            cardId =
                details.id,
            languageCode =
                details.languageCode,
            variantId =
                selected.id,
            variantType =
                selected.type,
            condition =
                condition.name,
            market =
                "TCG",
            source =
                source,
            baseEur =
                baseEur,
            conditionFactor =
                condition.factor,
            eur =
                baseEur?.let {
                    roundedUnitEur(
                        it,
                        condition.factor
                    )
                },
            exactLanguageMatch =
                true,
            exactVariantMatch =
                true,
            rangeLowEur =
                statistics.lowEur,
            rangeHighEur =
                statistics.highEur,
            trend30dPercent =
                statistics.trend30dPercent,
            updatedAtMs =
                updatedAtMs,
            providerUrl =
                providerUrl
        )
    }

    private fun emptyQuote(
        details: CatalogCardDetails,
        selected: CatalogVariant?,
        condition: PricingCondition,
        exactLanguageMatch: Boolean
    ): CardPriceQuoteResponse =
        CardPriceQuoteResponse(
            cardId =
                details.id,
            languageCode =
                details.languageCode,
            variantId =
                selected?.id,
            variantType =
                selected?.type,
            condition =
                condition.name,
            market =
                "TCG",
            source =
                null,
            baseEur =
                null,
            conditionFactor =
                condition.factor,
            eur =
                null,
            exactLanguageMatch =
                exactLanguageMatch,
            exactVariantMatch =
                selected != null
        )
}
