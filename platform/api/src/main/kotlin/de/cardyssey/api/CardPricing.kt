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
    val updatedAtMs: Long? = null
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
                ?: return null

        val identityCount =
            variants.count {
                it.priceIdentity == identity
            }

        if (identityCount != 1) {
            return null
        }

        val eur =
            selected.eur
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }
                ?: return null

        return CentralProviderQuote(
            source = "TCGDEX",
            baseEur = eur
        )
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
        condition: PricingCondition
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
                providers.firstNotNullOfOrNull {
                    provider ->

                    provider.quote(
                        card = details,
                        variant = selected
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
                baseEur?.times(
                    condition.factor
                ),
            exactLanguageMatch =
                exactLanguageMatch,
            exactVariantMatch =
                selected != null
        )
    }
}
