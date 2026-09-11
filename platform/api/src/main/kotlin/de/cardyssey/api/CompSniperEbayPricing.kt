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

class CompSniperEbayQuoteProvider(
    private val catalog: CardCatalogService,
    private val apiKey: String
) : EbayQuoteProvider {
    private data class SoldSummary(
        val baseEur: Double,
        val rangeLowEur: Double,
        val rangeHighEur: Double,
        val sampleCount: Int,
        val updatedAtMs: Long
    )

    private val json = Json { ignoreUnknownKeys = true }
    private val http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(10))
        .followRedirects(HttpClient.Redirect.NORMAL)
        .build()

    override suspend fun quote(
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
            source = if (baseEur != null) "COMPSNIPER" else null,
            baseEur = baseEur,
            conditionFactor = condition.factor,
            eur = baseEur?.times(condition.factor),
            exactLanguageMatch = exactLanguageMatch,
            exactVariantMatch = exactVariantMatch,
            sampleCount = sold?.sampleCount,
            rangeLowEur = sold?.rangeLowEur?.times(condition.factor),
            rangeHighEur = sold?.rangeHighEur?.times(condition.factor),
            updatedAtMs = sold?.updatedAtMs
        )
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

        val url = "https://api.compsniper.com/v1/scrape" +
            "?keyword=${encodeCompSniper(query)}" +
            "&ebaySite=ebay.de&page=1&count=240" +
            "&sortOrder=endedRecently&sold=true" +
            "&exactMatch=false&relevance=false"

        val root = getJson(url) ?: return null
        val items = root["items"] as? JsonArray ?: return null
        val unique = linkedMapOf<String, Double>()

        items.mapNotNull { it as? JsonObject }.forEach { item ->
            if (!listingMatches(item, card, variant, printedNumber)) return@forEach
            if (item.boolValue("bestOfferAccepted") == true) return@forEach

            val currency = item.stringValue("soldCurrency")
                ?.uppercase(Locale.ROOT)
            if (currency != "EUR") return@forEach

            val rawPrice = item.doubleValue("soldPrice")
                ?: item.doubleValue("totalPrice")
                ?: return@forEach

            if (!rawPrice.isFinite() || rawPrice <= 0.0) return@forEach

            val basePrice = normalizeSoldCondition(item, rawPrice)
                ?: return@forEach

            if (!basePrice.isFinite() || basePrice <= 0.0) return@forEach

            val stableId = item.stringValue("itemId")
                ?: item.stringValue("listingId")
                ?: item.stringValue("id")
                ?: item.stringValue("url")
                ?: listOf(
                    normalizeCompSniperText(item.stringValue("title").orEmpty()),
                    rawPrice.toString(),
                    item.stringValue("endedAt").orEmpty(),
                    item.stringValue("soldDate").orEmpty()
                ).joinToString("|")

            unique.putIfAbsent(stableId, basePrice)
        }

        if (unique.isEmpty()) return null

        val filtered = rejectOutliers(unique.values.toList())
        if (filtered.isEmpty()) return null

        val mean = filtered.average()
            .takeIf { it.isFinite() && it > 0.0 }
            ?: return null
        val low = filtered.minOrNull()
            ?.takeIf { it.isFinite() && it > 0.0 }
            ?: return null
        val high = filtered.maxOrNull()
            ?.takeIf { it.isFinite() && it > 0.0 }
            ?: return null

        println(
            "eBay pricing: provider=COMPSNIPER card=${card.id} language=${card.languageCode} " +
                "variant=${variant.id} providerItems=${items.size} matched=${unique.size} " +
                "kept=${filtered.size} mean=$mean range=$low..$high"
        )

        return SoldSummary(
            baseEur = mean,
            rangeLowEur = low,
            rangeHighEur = high,
            sampleCount = filtered.size,
            updatedAtMs = System.currentTimeMillis()
        )
    }

    private suspend fun getJson(url: String): JsonObject? =
        withContext(Dispatchers.IO) {
            runCatching {
                val request = HttpRequest.newBuilder(URI.create(url))
                    .timeout(Duration.ofSeconds(70))
                    .header("Accept", "application/json")
                    .header("Authorization", "Bearer $apiKey")
                    .GET()
                    .build()

                val response = http.send(
                    request,
                    HttpResponse.BodyHandlers.ofString()
                )

                if (response.statusCode() !in 200..299) {
                    println(
                        "CompSniper request failed: HTTP ${response.statusCode()} " +
                            response.body().take(300)
                    )
                    return@runCatching null
                }

                json.parseToJsonElement(response.body()).jsonObject
            }.onFailure {
                println("CompSniper request failed: ${it.message}")
            }.getOrNull()
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

    private fun listingMatches(
        item: JsonObject,
        card: CatalogCardDetails,
        variant: CatalogVariant,
        printedNumber: String
    ): Boolean {
        val title = normalizeCompSniperText(item.stringValue("title").orEmpty())
        if (title.isBlank()) return false
        if (looksLikeBundleOrGraded(title)) return false

        val cardName = normalizeCompSniperText(card.name)
        if (cardName.isNotBlank() && cardName !in title) return false

        val numberTokens = listOf(
            normalizeCompSniperText(printedNumber),
            normalizeCompSniperText(card.localId)
        ).filter(String::isNotBlank)

        if (numberTokens.none { it in title }) return false
        if (!languageMatches(title, card.languageCode)) return false

        return variantMatches(title, card, variant)
    }

    private fun looksLikeBundleOrGraded(title: String): Boolean {
        val padded = " $title "
        return listOf(
            " psa ", " bgs ", " cgc ", " graded ", " gegradet ",
            " konvolut ", " sammlung ", " komplettes set ",
            " complete set ", " lot "
        ).any { it in padded }
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
                    reverse || normalizeCompSniperText(variant.type).contains("reverse")
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

        return explicit
            .filterKeys { it != language }
            .values
            .flatten()
            .none { it in title }
    }

    private fun normalizeSoldCondition(
        item: JsonObject,
        rawPrice: Double
    ): Double? {
        val conditionText = normalizeCompSniperText(
            listOf(
                item.stringValue("condition").orEmpty(),
                item.stringValue("itemCondition").orEmpty(),
                item.stringValue("conditionName").orEmpty(),
                item.stringValue("title").orEmpty()
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
        val clean = values.filter { it.isFinite() && it > 0.0 }
        if (clean.size <= 2) return clean

        val center = medianCompSniper(clean)
        if (!center.isFinite() || center <= 0.0) return clean

        val deviations = clean.map { abs(it - center) }
        val mad = medianCompSniper(deviations)

        val filtered = if (mad.isFinite() && mad > 0.0) {
            clean.filter { abs(it - center) / mad <= 3.5 }
        } else {
            clean.filter {
                it >= center * 0.35 &&
                    it <= center * 2.85
            }
        }

        val minimumKept = if (clean.size >= 5) 3 else 2
        return if (filtered.size >= minimumKept) filtered else clean
    }
}

private fun JsonObject.stringValue(key: String): String? =
    (this[key] as? JsonPrimitive)
        ?.content
        ?.trim()
        ?.takeIf(String::isNotBlank)

private fun JsonObject.boolValue(key: String): Boolean? =
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

private fun JsonObject.doubleValue(key: String): Double? =
    (this[key] as? JsonPrimitive)?.doubleOrNull

private fun normalizeCompSniperText(raw: String): String =
    java.text.Normalizer.normalize(raw, java.text.Normalizer.Form.NFD)
        .replace("\\p{M}+".toRegex(), "")
        .lowercase(Locale.ROOT)
        .replace("[^a-z0-9/]+".toRegex(), " ")
        .trim()
        .replace("\\s+".toRegex(), " ")

private fun encodeCompSniper(raw: String): String =
    URLEncoder.encode(raw, StandardCharsets.UTF_8)

private fun medianCompSniper(values: List<Double>): Double {
    val sorted = values.sorted()
    val middle = sorted.size / 2
    return if (sorted.size % 2 == 0) {
        (sorted[middle - 1] + sorted[middle]) / 2.0
    } else {
        sorted[middle]
    }
}
