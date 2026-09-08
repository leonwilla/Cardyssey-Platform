package de.cardyssey.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonObject
import java.net.URI
import java.net.URLEncoder
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.charset.StandardCharsets
import java.time.Duration
import java.util.Locale
import kotlin.math.roundToLong

internal class JustTcgCentralPricingProvider(
    private val apiKey: String
) : CentralPricingProvider {

    private val json = Json { ignoreUnknownKeys = true }
    private val http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(10))
        .followRedirects(HttpClient.Redirect.NORMAL)
        .build()

    override suspend fun quote(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): CentralProviderQuote? {
        if (apiKey.isBlank()) return null

        val market = marketForLanguage(card.languageCode) ?: return null
        val query = card.name.trim().takeIf(String::isNotBlank) ?: return null
        val url = "https://api.justtcg.com/v1/cards" +
            "?game=${encode(market.first)}" +
            "&q=${encode(query)}&limit=20"

        val root = getJson(url, "X-API-Key", apiKey) ?: return null
        val cards = root["data"] as? JsonArray ?: return null

        val expectedNumber = normalizeNumber(card.localId)
        val expectedName = normalizeText(card.name)
        val expectedSet = normalizeText(card.setName)

        val candidate = cards.mapNotNull { it as? JsonObject }
            .mapNotNull { raw ->
                val number = raw.string("number") ?: return@mapNotNull null
                if (normalizeNumber(number) != expectedNumber) return@mapNotNull null

                val name = normalizeText(raw.string("name").orEmpty())
                val setName = normalizeText(raw.string("set_name").orEmpty())
                val nameMatches = name == expectedName || name.contains(expectedName) || expectedName.contains(name)
                val setMatches = expectedSet.isBlank() || setName == expectedSet || setName.contains(expectedSet) || expectedSet.contains(setName)
                if (!nameMatches || !setMatches) return@mapNotNull null
                raw
            }
            .firstOrNull() ?: return null

        val variants = candidate["variants"] as? JsonArray ?: return null
        val usdValues = variants.mapNotNull { it as? JsonObject }
            .filter {
                normalizeText(it.string("language").orEmpty()) == normalizeText(market.second)
            }
            .filter { printingMatches(it.string("printing"), variant.legacyVariant) }
            .filter { normalizeText(it.string("condition").orEmpty()).contains("near mint") }
            .mapNotNull { it.double("price") }
            .filter { it.isFinite() && it > 0.0 }

        if (usdValues.isEmpty()) return null
        val usd = median(usdValues)
        val eur = usdToEur(usd) ?: return null

        // JustTCG liefert condition-spezifische Werte. Für den zentralen Basiswert
        // normalisieren wir Near Mint zurück auf 100 %, weil Cardyssey den
        // Zustandsfaktor erst danach einheitlich anwendet.
        val baseEur = eur / PricingCondition.NEAR_MINT.factor

        return baseEur.takeIf { it.isFinite() && it > 0.0 }?.let {
            CentralProviderQuote(source = "JUSTTCG", baseEur = it)
        }
    }

    private suspend fun usdToEur(usd: Double): Double? {
        val root = getJson("https://api.frankfurter.dev/v2/rate/USD/EUR") ?: return null
        val rate = root.double("rate") ?: return null
        return (usd * rate).takeIf { it.isFinite() && it > 0.0 }
    }

    private fun marketForLanguage(language: String): Pair<String, String>? =
        when (language.lowercase(Locale.ROOT)) {
            "de" -> "pokemon" to "German"
            "en" -> "pokemon" to "English"
            "fr" -> "pokemon" to "French"
            "it" -> "pokemon" to "Italian"
            "es" -> "pokemon" to "Spanish"
            "pt" -> "pokemon" to "Portuguese"
            "ja" -> "pokemon-japan" to "Japanese"
            else -> null
        }

    private fun printingMatches(raw: String?, legacyVariant: String): Boolean {
        val printing = normalizeText(raw.orEmpty())
        return when (legacyVariant.uppercase(Locale.ROOT)) {
            "REVERSE" -> "reverse" in printing
            "HOLO" -> "holo" in printing && "reverse" !in printing
            "NORMAL" -> "reverse" !in printing && "holo" !in printing
            else -> false
        }
    }

    private suspend fun getJson(
        url: String,
        headerName: String? = null,
        headerValue: String? = null
    ): JsonObject? = withContext(Dispatchers.IO) {
        runCatching {
            val builder = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(15))
                .header("Accept", "application/json")
                .GET()
            if (!headerName.isNullOrBlank() && !headerValue.isNullOrBlank()) {
                builder.header(headerName, headerValue)
            }
            val response = http.send(builder.build(), HttpResponse.BodyHandlers.ofString())
            if (response.statusCode() !in 200..299) return@runCatching null
            json.parseToJsonElement(response.body()).jsonObject
        }.getOrNull()
    }
}

class EbaySoldPricingService(
    private val catalog: CardCatalogService,
    private val apiKey: String
) {
    private data class SoldSummary(
        val baseEur: Double,
        val sampleCount: Int,
        val updatedAtMs: Long
    )
    private val json = Json { ignoreUnknownKeys = true }
    private val http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(10))
        .followRedirects(HttpClient.Redirect.NORMAL)
        .build()

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
        val exactVariantMatch = selected != null

        val sold = if (
        apiKey.isNotBlank() && exactLanguageMatch && selected != null
    ) {
        soldSummary(details, selected)
    } else null

    val baseEur = sold?.baseEur

        return CardPriceQuoteResponse(
            cardId = details.id,
            languageCode = details.languageCode,
            variantId = selected?.id,
            variantType = selected?.type,
            condition = condition.name,
            market = "EBAY",
            source = if (baseEur != null) "SOLDCOMPS" else null,
            baseEur = baseEur,
            conditionFactor = condition.factor,
            eur = baseEur?.times(condition.factor),
            exactLanguageMatch = exactLanguageMatch,
            exactVariantMatch = exactVariantMatch,
            sampleCount = sold?.sampleCount,
            updatedAtMs = sold?.updatedAtMs
        )
    }

    private fun selectVariant(
        details: CatalogCardDetails,
        variantId: String?,
        legacyVariant: String?
    ): CatalogVariant? {
        if (!variantId.isNullOrBlank()) {
            return details.variants.firstOrNull { it.id == variantId.trim() }
        }
        val legacy = legacyVariant?.trim()?.uppercase(Locale.ROOT)?.takeIf(String::isNotBlank)
        if (legacy != null) {
            return details.variants.filter { it.legacyVariant == legacy }.singleOrNull()
        }
        return details.variants.singleOrNull()
    }

    private suspend fun soldSummary(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): SoldSummary? {
        val printedNumber = if (card.officialCount > 0 && card.localId.isNotBlank()) {
            "${card.localId}/${card.officialCount}"
        } else card.localId

        val query = listOf(card.name, printedNumber)
            .filter(String::isNotBlank)
            .joinToString(" ")

        val url = "https://api.sold-comps.com/v1/scrape" +
            "?keyword=${encode(query)}" +
            "&ebaySite=ebay.de&page=1&count=200" +
            "&sortOrder=endedRecently&sold=true" +
            "&includeCompleteListing=true&exactMatch=true"

        val root = getJson(url) ?: return null
        val items = root["items"] as? JsonArray ?: return null

        val prices = items.mapNotNull { it as? JsonObject }
            .filter { listingMatches(it, card, variant, printedNumber) }
            .mapNotNull { item ->
                val currency = item.string("soldCurrency")?.uppercase(Locale.ROOT)
                if (currency != "EUR") return@mapNotNull null
                item.double("totalPrice") ?: item.double("soldPrice")
            }
            .filter { it.isFinite() && it > 0.0 }
            .sorted()

        if (prices.size < 3) return null

        // Robuste Mitte: bei genügend Samples die äußeren 10 % abschneiden.
        val trimmed = if (prices.size >= 10) {
            val trim = (prices.size * 0.10).roundToLong().toInt().coerceAtLeast(1)
            prices.drop(trim).dropLast(trim)
        } else prices

        val baseEur = median(trimmed)
        .takeIf { it.isFinite() && it > 0.0 }
        ?: return null

    return SoldSummary(
        baseEur = baseEur,
        sampleCount = trimmed.size,
        updatedAtMs = System.currentTimeMillis()
    )
    }

    private fun listingMatches(
        item: JsonObject,
        card: CatalogCardDetails,
        variant: CatalogVariant,
        printedNumber: String
    ): Boolean {
        val title = normalizeText(item.string("title").orEmpty())
        if (title.isBlank()) return false

        val cardName = normalizeText(card.name)
        if (cardName.isNotBlank() && cardName !in title) return false

        val numberTokens = listOf(
            normalizeText(printedNumber),
            normalizeText(card.localId)
        ).filter(String::isNotBlank)
        if (numberTokens.none { it in title }) return false

        if (!languageMatches(title, card.languageCode)) return false

        val reverse = "reverse" in title
        val holo = "holo" in title || "foil" in title
        return when (variant.legacyVariant.uppercase(Locale.ROOT)) {
            "REVERSE" -> reverse
            "HOLO" -> holo && !reverse
            "NORMAL" -> !reverse && !holo
            else -> false
        }
    }

    private fun languageMatches(title: String, language: String): Boolean {
        val explicit = mapOf(
            "de" to listOf("deutsch", "german"),
            "en" to listOf("englisch", "english"),
            "fr" to listOf("franzosisch", "french"),
            "it" to listOf("italienisch", "italian"),
            "es" to listOf("spanisch", "spanish"),
            "pt" to listOf("portugiesisch", "portuguese"),
            "ja" to listOf("japanisch", "japanese")
        )
        val wanted = explicit[language] ?: return true
        val foreignMarkers = explicit.filterKeys { it != language }.values.flatten()
        if (foreignMarkers.any { it in title }) return false
        // Deutsch/Japanisch und andere lokalisierte Karten brauchen eine explizite
        // Sprachangabe. Englisch darf ohne Sprachmarker vorkommen.
        return language == "en" || wanted.any { it in title }
    }

    private suspend fun getJson(url: String): JsonObject? = withContext(Dispatchers.IO) {
        runCatching {
            val request = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(20))
                .header("Accept", "application/json")
                .header("X-API-Key", apiKey)
                .GET()
                .build()
            val response = http.send(request, HttpResponse.BodyHandlers.ofString())
            if (response.statusCode() !in 200..299) return@runCatching null
            json.parseToJsonElement(response.body()).jsonObject
        }.getOrNull()
    }
}

private fun JsonObject.string(key: String): String? =
    (this[key] as? JsonPrimitive)?.content?.trim()?.takeIf(String::isNotBlank)

private fun JsonObject.double(key: String): Double? =
    (this[key] as? JsonPrimitive)?.doubleOrNull

private fun normalizeText(raw: String): String =
    java.text.Normalizer.normalize(raw, java.text.Normalizer.Form.NFD)
        .replace("\\p{M}+".toRegex(), "")
        .lowercase(Locale.ROOT)
        .replace("[^a-z0-9/]+".toRegex(), " ")
        .trim()
        .replace("\\s+".toRegex(), " ")

private fun normalizeNumber(raw: String): String =
    raw.trim().lowercase(Locale.ROOT).replace("^0+(?=\\d)".toRegex(), "")

private fun encode(raw: String): String =
    URLEncoder.encode(raw, StandardCharsets.UTF_8)

private fun median(values: List<Double>): Double {
    val sorted = values.sorted()
    val middle = sorted.size / 2
    return if (sorted.size % 2 == 0) {
        (sorted[middle - 1] + sorted[middle]) / 2.0
    } else sorted[middle]
}
