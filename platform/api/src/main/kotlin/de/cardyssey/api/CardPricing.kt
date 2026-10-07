package de.cardyssey.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonObject
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration

@Serializable
data class EbayRecentSaleResponse(
    val itemId: String? = null,
    val title: String,
    val soldPriceEur: Double,
    val rawCondition: String? = null,
    val endedAt: String? = null,
    val url: String? = null
)

@Serializable
data class CardPriceQuoteResponse(
    val cardId: String,
    val languageCode: String,
    val variantId: String?,
    val variantType: String?,
    val condition: String,
    val market: String,
    val source: String?,
    val baseEur: Double?,
    val conditionFactor: Double,
    val eur: Double?,
    val exactLanguageMatch: Boolean,
    val exactVariantMatch: Boolean,
    val sampleCount: Int? = null,
    val rangeLowEur: Double? = null,
    val rangeHighEur: Double? = null,
    val trend30dPercent: Double? = null,
    val updatedAtMs: Long? = null,
    val recentSales: List<EbayRecentSaleResponse> = emptyList()
)

enum class PricingCondition(
    val factor: Double
) {
    MINT(1.00),
    NEAR_MINT(0.92),
    EXCELLENT(0.80),
    GOOD(0.65),
    PLAYED(0.45);

    companion object {
        fun parse(
            raw: String?
        ): PricingCondition? {
            if (raw.isNullOrBlank()) {
                return NEAR_MINT
            }

            return entries.firstOrNull {
                it.name.equals(
                    raw.trim(),
                    ignoreCase = true
                )
            }
        }
    }
}

internal data class CentralProviderQuote(
    val source: String,
    val baseEur: Double
)

internal interface CentralPricingProvider {
    suspend fun quote(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): CentralProviderQuote?
}

private data class ExactTcgDexPrice(
    val variantId: String,
    val priceIdentity: String?,
    val eur: Double?
)

/**
 * TCGdex-Provider für den zentralen Server.
 *
 * Für Preise wird bewusst die konkret angefragte Sprachkarte geladen.
 * Es gibt hier keinen Sprach-Fallback. Außerdem wird die technische
 * Cardmarket-Preisidentität aller physischen Varianten verglichen.
 * Teilen mehrere Varianten denselben Preissatz, gilt er nicht als
 * variantspezifisch und wird nicht zurückgegeben.
 */
private class TcgDexCentralPricingProvider :
    CentralPricingProvider {

    companion object {
        private const val BASE =
            "https://api.tcgdex.net/v2"
    }

    private val json =
        Json {
            ignoreUnknownKeys = true
        }

    private val http =
        HttpClient
            .newBuilder()
            .connectTimeout(
                Duration.ofSeconds(10)
            )
            .followRedirects(
                HttpClient.Redirect.NORMAL
            )
            .build()

    override suspend fun quote(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): CentralProviderQuote? {
        val raw =
            fetchCard(
                language = card.languageCode,
                cardId = card.id
            ) ?: return null

        val variants =
            raw["variants_detailed"]
                ?.asArray()
                .orEmpty()
                .mapNotNull(
                    ::parseExactPrice
                )

        if (variants.isEmpty()) {
            /*
             * Legacy-Karten ohne variants_detailed dürfen den bereits
             * eindeutig zugeordneten Cardmarket-Wert aus dem zentralen
             * Katalog verwenden.
             */
            return variant.tcgDexEur
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }
                ?.let {
                    CentralProviderQuote(
                        source = "TCGDEX",
                        baseEur = it
                    )
                }
        }

        val selected =
            variants.firstOrNull {
                it.variantId == variant.id
            } ?: return null

        val identity =
            selected.priceIdentity

        val cardLevelEur =
            when {
                variants.size == 1 ->
                    cardLevelCardmarketEur(
                        raw = raw,
                        variant = variant
                    )

                isUniquePlainStandardNormal(
                    raw = raw,
                    variant = variant
                ) ->
                    cardLevelCardmarketEur(
                        raw = raw,
                        variant = variant
                    )

                isUniquePlainStandardHoloLike(
                    raw = raw,
                    variant = variant
                ) ->
                    cardLevelHoloCardmarketEur(
                        raw = raw
                    )

                else -> null
            }

        val sharedUniqueHoloEur =
            if (selected.eur == null) {
                uniqueSharedHoloFamilyEur(
                    raw = raw,
                    variant = variant
                )
            } else {
                null
            }

        val cardmarketEur =
            selected.eur
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }
                ?: variant.tcgDexEur
                    ?.takeIf {
                        it.isFinite() &&
                            it > 0.0
                    }
                ?: sharedUniqueHoloEur
                ?: cardLevelEur

        val tcgPlayerEur =
            if (cardmarketEur == null) {
                tcgPlayerEur(
                    raw = raw,
                    variant = variant
                )
            } else {
                null
            }

        val eur =
            cardmarketEur
                ?: tcgPlayerEur
                ?: return null

        val identityCount =
            identity
                ?.let {
                    priceIdentity ->
                    variants.count {
                        it.priceIdentity ==
                            priceIdentity
                    }
                }
                ?: 0

        /*
         * Cardmarket sometimes exposes one market price for multiple
         * physical variants of the same price family. The old code rejected
         * those quotes completely and the app showed "–" although a valid
         * TCG market value existed. The price identity already separates
         * base vs holo families, so a shared family value is preferable to
         * no value. The source label keeps that distinction observable.
         */
        return CentralProviderQuote(
            source =
                if (tcgPlayerEur != null) {
                    "TCGDEX_TCGPLAYER"
                } else if (sharedUniqueHoloEur != null) {
                    "TCGDEX_SHARED_HOLO"
                } else {
                    when {
                        identity == null ->
                            "TCGDEX_CATALOG"

                        identityCount <= 1 ->
                            "TCGDEX"

                        else ->
                            "TCGDEX_SHARED"
                    }
                },
            baseEur =
                eur
        )
    }

    private fun isUniquePlainStandardNormal(
        raw: JsonObject,
        variant: CatalogVariant
    ): Boolean {
        if (
            !variant.legacyVariant.equals("NORMAL", ignoreCase = true) ||
            variant.stamps.isNotEmpty() ||
            !variant.subtype.isNullOrBlank() ||
            !variant.foil.isNullOrBlank() ||
            (
                !variant.size.isNullOrBlank() &&
                    !variant.size.equals("standard", ignoreCase = true)
            )
        ) {
            return false
        }

        val detailed =
            raw["variants_detailed"]
                ?.asArray()
                .orEmpty()
                .mapNotNull {
                    it as? JsonObject
                }

        val plainNormal =
            detailed.filter { candidate ->
                candidate.string("type")
                    .equals("normal", ignoreCase = true) &&
                    candidate.string("subtype").isNullOrBlank() &&
                    candidate.string("foil").isNullOrBlank() &&
                    candidate["stamp"]
                        ?.asArray()
                        .orEmpty()
                        .isEmpty() &&
                    (
                        candidate.string("size").isNullOrBlank() ||
                            candidate.string("size")
                                .equals("standard", ignoreCase = true)
                    )
            }

        return plainNormal.size == 1 &&
            plainNormal.single().string("variantId") == variant.id
    }

    private fun isUniquePlainStandardHoloLike(
        raw: JsonObject,
        variant: CatalogVariant
    ): Boolean {
        if (
            !(
                variant.legacyVariant.equals("HOLO", ignoreCase = true) ||
                    variant.legacyVariant.equals("REVERSE", ignoreCase = true)
            ) ||
            variant.stamps.isNotEmpty() ||
            !variant.subtype.isNullOrBlank() ||
            !variant.foil.isNullOrBlank() ||
            (
                !variant.size.isNullOrBlank() &&
                    !variant.size.equals("standard", ignoreCase = true)
            )
        ) {
            return false
        }

        val detailed =
            raw["variants_detailed"]
                ?.asArray()
                .orEmpty()
                .mapNotNull {
                    it as? JsonObject
                }

        val plainHoloLike =
            detailed.filter { candidate ->
                val type =
                    candidate.string("type")
                        ?.trim()
                        ?.lowercase()
                        .orEmpty()

                (type == "holo" || type == "reverse") &&
                    candidate.string("subtype").isNullOrBlank() &&
                    candidate.string("foil").isNullOrBlank() &&
                    candidate["stamp"]
                        ?.asArray()
                        .orEmpty()
                        .isEmpty() &&
                    (
                        candidate.string("size").isNullOrBlank() ||
                            candidate.string("size")
                                .equals("standard", ignoreCase = true)
                    )
            }

        return plainHoloLike.size == 1 &&
            plainHoloLike.single().string("variantId") == variant.id
    }

    private fun cardLevelHoloCardmarketEur(
        raw: JsonObject
    ): Double? {
        val cardmarket =
            raw["pricing"]
                ?.asObject()
                ?.get("cardmarket")
                ?.asObject()
                ?: return null

        return listOf(
            "trend-holo",
            "avg1-holo",
            "avg7-holo",
            "avg30-holo",
            "avg-holo",
            "low-holo"
        ).firstNotNullOfOrNull { key ->
            cardmarket.double(key)
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }
        }
    }

    private fun uniqueSharedHoloFamilyEur(
        raw: JsonObject,
        variant: CatalogVariant
    ): Double? {
        if (
            !variant.legacyVariant.equals("HOLO", ignoreCase = true) &&
            !variant.legacyVariant.equals("REVERSE", ignoreCase = true)
        ) {
            return null
        }

        if (
            variant.stamps.isNotEmpty() ||
            !variant.subtype.isNullOrBlank() ||
            !variant.foil.isNullOrBlank() ||
            (
                !variant.size.isNullOrBlank() &&
                    !variant.size.equals("standard", ignoreCase = true)
            )
        ) {
            return null
        }

        val detailed =
            raw["variants_detailed"]
                ?.asArray()
                .orEmpty()
                .mapNotNull {
                    it as? JsonObject
                }

        val holoLike =
            detailed.filter { candidate ->
                val type =
                    candidate.string("type")
                        ?.trim()
                        ?.lowercase()
                        .orEmpty()

                type == "reverse" ||
                    type == "holo" ||
                    !candidate.string("foil").isNullOrBlank()
            }

        if (holoLike.size != 1) {
            return null
        }

        val only =
            holoLike.single()

        if (
            only.string("variantId") != variant.id ||
            !only.string("subtype").isNullOrBlank() ||
            !only.string("foil").isNullOrBlank() ||
            only["stamp"]
                ?.asArray()
                .orEmpty()
                .isNotEmpty() ||
            (
                !only.string("size").isNullOrBlank() &&
                    !only.string("size")
                        .equals("standard", ignoreCase = true)
            )
        ) {
            return null
        }

        val candidates =
            detailed.mapNotNull { candidate ->
                val cardmarket =
                    candidate["pricing"]
                        ?.asObject()
                        ?.get("cardmarket")
                        ?.asObject()
                        ?: return@mapNotNull null

                val price =
                    listOf(
                        "trend-holo",
                        "avg1-holo",
                        "avg7-holo",
                        "avg30-holo",
                        "avg-holo",
                        "low-holo"
                    ).firstNotNullOfOrNull { key ->
                        cardmarket.double(key)
                            ?.takeIf {
                                it.isFinite() &&
                                    it > 0.0
                            }
                    } ?: return@mapNotNull null

                val productId =
                    cardmarket.string("idProduct")
                        ?.trim()
                        ?.takeIf(String::isNotBlank)
                        ?: return@mapNotNull null

                productId to price
            }
                .distinctBy {
                    it.first
                }

        return candidates
            .singleOrNull()
            ?.second
    }

    private fun cardLevelCardmarketEur(
        raw: JsonObject,
        variant: CatalogVariant
    ): Double? {
        val cardmarket =
            raw["pricing"]
                ?.asObject()
                ?.get("cardmarket")
                ?.asObject()
                ?: return null

        val holoLike =
            variant.legacyVariant.equals("HOLO", ignoreCase = true) ||
                variant.legacyVariant.equals("REVERSE", ignoreCase = true) ||
                !variant.foil.isNullOrBlank()

        val keys =
            if (holoLike) {
                listOf(
                    "trend-holo",
                    "avg1-holo",
                    "avg7-holo",
                    "avg30-holo",
                    "avg-holo",
                    "low-holo",
                    "trend",
                    "avg1",
                    "avg7",
                    "avg30",
                    "avg",
                    "low"
                )
            } else {
                listOf(
                    "trend",
                    "avg1",
                    "avg7",
                    "avg30",
                    "avg",
                    "low"
                )
            }

        return keys.firstNotNullOfOrNull { key ->
            cardmarket.double(key)
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }
        }
    }

    private var cachedUsdToEur: Double? = null
    private var cachedUsdToEurAtMs: Long = 0L

    private suspend fun tcgPlayerEur(
        raw: JsonObject,
        variant: CatalogVariant
    ): Double? {
        // TCGPlayer's card-level feed can distinguish the legacy market
        // families, but not arbitrary stamped/jumbo/special printings.
        if (
            variant.stamps.isNotEmpty() ||
            !variant.size.isNullOrBlank() &&
                !variant.size.equals("standard", ignoreCase = true)
        ) {
            return null
        }

        val tcgPlayer =
            raw["pricing"]
                ?.asObject()
                ?.get("tcgplayer")
                ?.asObject()
                ?: return null

        val familyKeys =
            when (variant.legacyVariant.uppercase()) {
                "NORMAL" ->
                    listOf(
                        "normal",
                        "unlimited"
                    )

                "REVERSE" ->
                    listOf(
                        "reverse-holofoil",
                        "reverse"
                    )

                "HOLO" ->
                    listOf(
                        "holofoil",
                        "holo",
                        "unlimited-holofoil"
                    )

                else ->
                    emptyList()
            }

        val price =
            familyKeys
                .asSequence()
                .mapNotNull {
                    tcgPlayer[it]
                        ?.asObject()
                }
                .mapNotNull { family ->
                    listOf(
                        "marketPrice",
                        "midPrice",
                        "lowPrice"
                    )
                        .asSequence()
                        .mapNotNull {
                            family.double(it)
                        }
                        .firstOrNull {
                            it.isFinite() &&
                                it > 0.0
                        }
                }
                .firstOrNull()
                ?: return null

        val unit =
            tcgPlayer.string("unit")
                ?.uppercase()
                ?: "USD"

        return when (unit) {
            "EUR" ->
                price

            "USD" ->
                usdToEurRate()
                    ?.let {
                        price * it
                    }

            else ->
                null
        }
    }

    private suspend fun usdToEurRate(): Double? {
        val now =
            System.currentTimeMillis()

        cachedUsdToEur
            ?.takeIf {
                now - cachedUsdToEurAtMs <
                    24L * 60L * 60L * 1000L
            }
            ?.let {
                return it
            }

        val rate =
            withContext(Dispatchers.IO) {
                runCatching {
                    val request =
                        HttpRequest
                            .newBuilder(
                                URI.create(
                                    "https://api.frankfurter.dev/v2/providers/ecb/rate/usd/eur"
                                )
                            )
                            .timeout(
                                Duration.ofSeconds(10)
                            )
                            .header(
                                "Accept",
                                "application/json"
                            )
                            .GET()
                            .build()

                    val response =
                        http.send(
                            request,
                            HttpResponse.BodyHandlers.ofString()
                        )

                    if (
                        response.statusCode() !in 200..299
                    ) {
                        return@runCatching null
                    }

                    json.parseToJsonElement(
                        response.body()
                    )
                        .jsonObject
                        .double("rate")
                        ?.takeIf {
                            it.isFinite() &&
                                it > 0.0
                        }
                }.getOrNull()
            }

        if (rate != null) {
            cachedUsdToEur =
                rate
            cachedUsdToEurAtMs =
                now
        }

        return rate
    }

    private suspend fun fetchCard(
        language: String,
        cardId: String
    ): JsonObject? =
        withContext(Dispatchers.IO) {
            runCatching {
                val request =
                    HttpRequest
                        .newBuilder(
                            URI.create(
                                "$BASE/$language/cards/$cardId"
                            )
                        )
                        .timeout(
                            Duration.ofSeconds(15)
                        )
                        .header(
                            "Accept",
                            "application/json"
                        )
                        .GET()
                        .build()

                val response =
                    http.send(
                        request,
                        HttpResponse.BodyHandlers.ofString()
                    )

                if (
                    response.statusCode() !in 200..299
                ) {
                    return@runCatching null
                }

                json.parseToJsonElement(
                    response.body()
                ).jsonObject
            }.getOrNull()
        }

    private fun parseExactPrice(
        element: kotlinx.serialization.json.JsonElement
    ): ExactTcgDexPrice? {
        val raw =
            element as? JsonObject
                ?: return null

        val type =
            raw.string("type")
                ?.trim()
                ?.takeIf(String::isNotBlank)
                ?: return null

        val subtype =
            raw.string("subtype")

        val foil =
            raw.string("foil")

        val size =
            raw.string("size")

        val stamps =
            raw["stamp"]
                ?.asArray()
                .orEmpty()
                .mapNotNull {
                    (it as? JsonPrimitive)
                        ?.content
                        ?.trim()
                        ?.takeIf(String::isNotBlank)
                }

        val variantId =
            raw.string("variantId")
                ?: listOf(
                    type,
                    subtype.orEmpty(),
                    foil.orEmpty(),
                    stamps.joinToString("+"),
                    size.orEmpty()
                ).joinToString(":")

        val cardmarket =
            raw["pricing"]
                ?.asObject()
                ?.get("cardmarket")
                ?.asObject()

        if (cardmarket == null) {
            return ExactTcgDexPrice(
                variantId = variantId,
                priceIdentity = null,
                eur = null
            )
        }

        val normalizedType =
            type.trim().lowercase()

        val holoLike =
            normalizedType == "reverse" ||
                !foil.isNullOrBlank()

        val keys =
            when {
                holoLike ->
                    listOf(
                        "trend-holo",
                        "avg1-holo",
                        "avg7-holo",
                        "avg30-holo",
                        "avg-holo",
                        "low-holo",
                        "trend",
                        "avg1",
                        "avg7",
                        "avg30",
                        "avg",
                        "low"
                    )

                normalizedType == "holo" ->
                    listOf(
                        "trend",
                        "avg1",
                        "avg7",
                        "avg30",
                        "avg",
                        "low",
                        "trend-holo",
                        "avg1-holo",
                        "avg7-holo",
                        "avg30-holo",
                        "avg-holo",
                        "low-holo"
                    )

                else ->
                    listOf(
                        "trend",
                        "avg1",
                        "avg7",
                        "avg30",
                        "avg",
                        "low"
                    )
            }

        val productId =
            cardmarket.string(
                "idProduct"
            )
                ?.trim()
                ?.takeIf(String::isNotBlank)
                ?: "card"

        for (key in keys) {
            val value =
                cardmarket.double(key)
                    ?.takeIf {
                        it.isFinite() &&
                            it > 0.0
                    }
                    ?: continue

            val family =
                if (key.contains("-holo")) {
                    "holo"
                } else {
                    "base"
                }

            return ExactTcgDexPrice(
                variantId = variantId,
                priceIdentity =
                    "cardmarket:$productId:$family",
                eur = value
            )
        }

        return ExactTcgDexPrice(
            variantId = variantId,
            priceIdentity = null,
            eur = null
        )
    }

    private fun JsonObject.string(
        key: String
    ): String? =
        (this[key] as? JsonPrimitive)
            ?.content
            ?.takeIf(String::isNotBlank)

    private fun JsonObject.double(
        key: String
    ): Double? =
        (this[key] as? JsonPrimitive)
            ?.doubleOrNull

    private fun kotlinx.serialization.json.JsonElement.asObject():
        JsonObject? =
        this as? JsonObject

    private fun kotlinx.serialization.json.JsonElement.asArray():
        JsonArray? =
        this as? JsonArray
}

class CardPricingService(
    private val catalog: CardCatalogService,
    justTcgApiKey: String? = null
) {
    private val providers:
        List<CentralPricingProvider> =
        buildList {
            add(TcgDexCentralPricingProvider())
            justTcgApiKey
                ?.trim()
                ?.takeIf(String::isNotBlank)
                ?.let {
                    add(JustTcgCentralPricingProvider(it))
                }
        }

    suspend fun quote(
        cardId: String,
        language: String,
        variantId: String?,
        legacyVariant: String?,
        condition: PricingCondition,
        includeFallbackProviders: Boolean = true
    ): CardPriceQuoteResponse? {
        val details =
            catalog.details(
                cardId = cardId,
                language = language
            ) ?: return null

        val exactLanguageMatch =
            details.languageCode == language

        val normalizedLegacyVariant =
            legacyVariant
                ?.trim()
                ?.uppercase()
                ?.takeIf(String::isNotBlank)

        val selected =
            when {
                !variantId.isNullOrBlank() ->
                    details.variants
                        .firstOrNull {
                            it.id == variantId.trim()
                        }

                normalizedLegacyVariant != null -> {
                    val candidates =
                        details.variants.filter {
                            it.legacyVariant ==
                                normalizedLegacyVariant
                        }

                    /*
                     * Eine Legacy-Variante darf nur dann
                     * bepreist werden, wenn genau eine
                     * physische Detailvariante dazu passt.
                     * Besser kein Preis als ein falscher.
                     */
                    candidates.singleOrNull()
                }

                details.variants.size == 1 ->
                    details.variants.first()

                else ->
                    null
            }

        val providerQuote =
            if (
                exactLanguageMatch &&
                selected != null
            ) {
                providers
                    .let {
                        if (
                            includeFallbackProviders
                        ) {
                            it
                        } else {
                            it.take(
                                1
                            )
                        }
                    }
                    .firstNotNullOfOrNull {
                        provider ->

                        provider.quote(
                            card = details,
                            variant = selected
                        )
                    }
                    ?: selected.tcgDexEur
                        ?.takeIf {
                            it.isFinite() &&
                                it > 0.0
                        }
                        ?.let {
                            CentralProviderQuote(
                                source =
                                    "TCGDEX_CATALOG_CACHE",
                                baseEur =
                                    it
                            )
                        }
            } else {
                null
            }

        val baseEur =
            providerQuote?.baseEur

        return CardPriceQuoteResponse(
            cardId = details.id,
            languageCode = details.languageCode,
            variantId = selected?.id,
            variantType = selected?.type,
            condition = condition.name,
            market = "TCG",
            source = providerQuote?.source,
            baseEur = baseEur,
            conditionFactor = condition.factor,
            eur =
                baseEur?.let { roundedUnitEur(it, condition.factor) },
            exactLanguageMatch =
                exactLanguageMatch,
            exactVariantMatch =
                selected != null
        )
    }
}

