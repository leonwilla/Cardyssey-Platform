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
import kotlin.math.abs

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
                val nameMatches =
                    name == expectedName ||
                        name.contains(expectedName) ||
                        expectedName.contains(name)
                val setMatches =
                    expectedSet.isBlank() ||
                        setName == expectedSet ||
                        setName.contains(expectedSet) ||
                        expectedSet.contains(setName)
                if (!nameMatches || !setMatches) return@mapNotNull null
                raw
            }
            .firstOrNull() ?: return null

        val variants = candidate["variants"] as? JsonArray ?: return null
        val usdValues = variants.mapNotNull { it as? JsonObject }
            .filter {
                normalizeText(it.string("language").orEmpty()) ==
                    normalizeText(market.second)
            }
            .filter { printingMatches(it.string("printing"), variant.legacyVariant) }
            .filter {
                normalizeText(it.string("condition").orEmpty())
                    .contains("near mint")
            }
            .mapNotNull { it.double("price") }
            .filter { it.isFinite() && it > 0.0 }

        if (usdValues.isEmpty()) return null
        val usd = median(usdValues)
        val eur = usdToEur(usd) ?: return null
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
    private val apiKey: String,
    private val ebayCookies: String = ""
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

        val sold = if (apiKey.isNotBlank() && exactLanguageMatch && selected != null) {
            soldSummary(details, selected)
        } else {
            if (apiKey.isBlank()) {
                println("eBay pricing unavailable: SOLDCOMPS_API_KEY is not configured")
            }
            null
        }

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

    private suspend fun soldSummary(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): SoldSummary? {
        val printedNumber = if (card.officialCount > 0 && card.localId.isNotBlank()) {
            "${card.localId}/${card.officialCount}"
        } else {
            card.localId
        }

        val query = listOf(card.name, printedNumber)
            .filter(String::isNotBlank)
            .joinToString(" ")

        val url = "https://api.sold-comps.com/v1/scrape" +
            "?keyword=${encode(query)}" +
            "&ebaySite=ebay.de&page=1&count=200" +
            "&sortOrder=endedRecently&sold=true" +
            "&includeCompleteListing=true&exactMatch=false"

        val root = getSoldCompsJson(url) ?: return null
        val items = root["items"] as? JsonArray ?: return null

        val unique = linkedMapOf<String, Double>()

        items.mapNotNull { it as? JsonObject }.forEach { item ->
            if (!listingMatches(item, card, variant, printedNumber)) return@forEach

            if (
                item.bool("bestOfferAccepted") == true ||
                item.bool("invalid") == true ||
                item.bool("isInvalid") == true
            ) {
                return@forEach
            }

            val currency = item.string("soldCurrency")
                ?.uppercase(Locale.ROOT)
            if (currency != "EUR") return@forEach

            val rawPrice = item.double("soldPrice")
                ?: item.double("totalPrice")
                ?: return@forEach

            if (!rawPrice.isFinite() || rawPrice <= 0.0) return@forEach

            val basePrice = normalizeSoldCondition(item, rawPrice)
                ?: return@forEach

            if (!basePrice.isFinite() || basePrice <= 0.0) return@forEach

            val stableId = item.string("itemId")
                ?: item.string("listingId")
                ?: item.string("id")
                ?: item.string("url")
                ?: listOf(
                    normalizeText(item.string("title").orEmpty()),
                    rawPrice.toString(),
                    item.string("endedAt").orEmpty(),
                    item.string("soldDate").orEmpty()
                ).joinToString("|")

            unique.putIfAbsent(stableId, basePrice)
        }

        println(
            "eBay pricing: card=${card.id} language=${card.languageCode} " +
                "variant=${variant.id} providerItems=${items.size} matched=${unique.size} " +
                "ebaySession=${if (ebayCookies.isBlank()) "none" else "configured"}"
        )

        if (unique.isEmpty()) return null

        val filtered = rejectOutliers(unique.values.toList())
        if (filtered.isEmpty()) return null

        val baseEur = median(filtered)
            .takeIf { it.isFinite() && it > 0.0 }
            ?: return null

        return SoldSummary(
            baseEur = baseEur,
            sampleCount = filtered.size,
            updatedAtMs = System.currentTimeMillis()
        )
    }

    private fun normalizeSoldCondition(
        item: JsonObject,
        rawPrice: Double
    ): Double? {
        val conditionText = normalizeText(
            listOf(
                item.string("condition").orEmpty(),
                item.string("itemCondition").orEmpty(),
                item.string("conditionName").orEmpty(),
                item.string("title").orEmpty()
            ).joinToString(" ")
        )

        val condition = when {
            "near mint" in conditionText ||
                "boosterfrisch" in conditionText ||
                "pack fresh" in conditionText ||
                Regex("""\bnm\b""").containsMatchIn(conditionText) ->
                PricingCondition.NEAR_MINT

            "mint" in conditionText ->
                PricingCondition.MINT

            "excellent" in conditionText ||
                "sehr gut" in conditionText ||
                Regex("""\bex\b""").containsMatchIn(conditionText) ->
                PricingCondition.EXCELLENT

            "played" in conditionText ||
                "gespielt" in conditionText ->
                PricingCondition.PLAYED

            "good" in conditionText ||
                Regex("""\bgut\b""").containsMatchIn(conditionText) ->
                PricingCondition.GOOD

            else -> null
        } ?: return null

        return rawPrice / condition.factor
    }

    private fun rejectOutliers(values: List<Double>): List<Double> {
        if (values.size < 5) return values

        val center = median(values)
        val deviations = values.map { abs(it - center) }
        val mad = median(deviations)

        if (!mad.isFinite() || mad <= 0.0) return values

        val filtered = values.filter {
            abs(it - center) / mad <= 3.5
        }

        return if (filtered.isNotEmpty()) filtered else values
    }

    private fun listingMatches(
        item: JsonObject,
        card: CatalogCardDetails,
        variant: CatalogVariant,
        printedNumber: String
    ): Boolean {
        val title = normalizeText(item.string("title").orEmpty())
        if (title.isBlank()) return false

        if (looksLikeBundleOrGraded(title)) return false

        val cardName = normalizeText(card.name)
        if (cardName.isNotBlank() && cardName !in title) return false

        val numberTokens = listOf(
            normalizeText(printedNumber),
            normalizeText(card.localId)
        ).filter(String::isNotBlank)

        if (numberTokens.none { it in title }) return false
        if (!languageMatches(title, card.languageCode)) return false

        return variantMatches(title, card, variant)
    }

    private fun looksLikeBundleOrGraded(title: String): Boolean {
        val padded = " $title "
        val blocked = listOf(
            " psa ",
            " bgs ",
            " cgc ",
            " graded ",
            " gegradet ",
            " konvolut ",
            " sammlung ",
            " komplettes set ",
            " complete set ",
            " lot "
        )
        return blocked.any { it in padded }
    }

    private fun variantMatches(
        title: String,
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): Boolean {
        val padded = " $title "
        val reverse = " reverse " in padded || " reverse holo " in padded
        val nonHolo = " non holo " in padded || " nonholo " in padded
        val holo =
            " holo " in padded ||
                " foil " in padded ||
                " holographic " in padded

        val legacy = variant.legacyVariant.uppercase(Locale.ROOT)

        if (card.variants.size == 1) {
            return when (legacy) {
                "REVERSE" ->
                    reverse || normalizeText(variant.type).contains("reverse")

                "HOLO" ->
                    !reverse && !nonHolo

                "NORMAL" ->
                    !reverse && !holo

                else ->
                    true
            }
        }

        return when (legacy) {
            "REVERSE" -> reverse
            "HOLO" -> holo && !reverse && !nonHolo
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

        val foreignMarkers = explicit
            .filterKeys { it != language }
            .values
            .flatten()

        return foreignMarkers.none { it in title }
    }

    private suspend fun getSoldCompsJson(url: String): JsonObject? =
        withContext(Dispatchers.IO) {
            runCatching {
                val builder = HttpRequest.newBuilder(URI.create(url))
                    .timeout(Duration.ofSeconds(25))
                    .header("Accept", "application/json")
                    .header("Authorization", "Bearer $apiKey")

                if (ebayCookies.isNotBlank()) {
                    builder.header("X-eBay-Cookies", ebayCookies)
                }

                val response = http.send(
                    builder.GET().build(),
                    HttpResponse.BodyHandlers.ofString()
                )

                if (response.statusCode() !in 200..299) {
                    println(
                        "SoldComps request failed: HTTP ${response.statusCode()} " +
                            response.body().take(300)
                    )
                    return@runCatching null
                }

                json.parseToJsonElement(response.body()).jsonObject
            }.onFailure {
                println("SoldComps request failed: ${it.message}")
            }.getOrNull()
        }
}

private fun JsonObject.string(key: String): String? =
    (this[key] as? JsonPrimitive)
        ?.content
        ?.trim()
        ?.takeIf(String::isNotBlank)

private fun JsonObject.bool(key: String): Boolean? =
    (this[key] as? JsonPrimitive)
        ?.content
        ?.trim()
        ?.lowercase(Locale.ROOT)
        ?.let {
            when (it) {
                "true" -> true
                "false" -> false
                else -> null
            }
        }

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
    raw.trim()
        .lowercase(Locale.ROOT)
        .replace("^0+(?=\\d)".toRegex(), "")

private fun encode(raw: String): String =
    URLEncoder.encode(raw, StandardCharsets.UTF_8)

private fun median(values: List<Double>): Double {
    val sorted = values.sorted()
    val middle = sorted.size / 2
    return if (sorted.size % 2 == 0) {
        (sorted[middle - 1] + sorted[middle]) / 2.0
    } else {
        sorted[middle]
    }
}
