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

    @Volatile
    private var requestLimitRetryAtMs = 0L

    override suspend fun quote(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): CentralProviderQuote? {
        if (apiKey.isBlank()) return null
        if (System.currentTimeMillis() < requestLimitRetryAtMs) return null

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

        val market = marketForLanguage(card.languageCode) ?: return null
        val query = card.name.trim().takeIf(String::isNotBlank) ?: return null
        val url = "https://api.justtcg.com/v1/cards" +
            "?game=${encode(market.first)}" +
            "&q=${encode(query)}" +
            "&language=${encode(market.second)}" +
            "&limit=20"

        val root = getJson(url, "X-API-Key", apiKey) ?: return null
        val cards = root["data"] as? JsonArray ?: return null

        val expectedNumber = normalizeNumber(card.localId)
        val expectedName = normalizeText(card.name)
        val expectedSet = normalizeText(card.setName)

        val numberedCards =
            cards.mapNotNull { it as? JsonObject }
                .filter { raw ->
                    val number = raw.string("number")
                        ?: return@filter false
                    normalizeNumber(number) == expectedNumber
                }

        val strictCandidates =
            numberedCards.filter { raw ->
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
                nameMatches && setMatches
            }

        val candidate =
            strictCandidates.singleOrNull()
                ?: numberedCards
                    .filter { raw ->
                        normalizeText(raw.string("name").orEmpty()) ==
                            expectedName
                    }
                    /*
                     * Localized German set names can differ from JustTCG's set
                     * title. Exact card name + exact card number is still safe
                     * when it resolves to one unique candidate in the provider
                     * response. Ambiguous results remain intentionally rejected.
                     */
                    .singleOrNull()
                ?: return null

        val variants = candidate["variants"] as? JsonArray ?: return null
        val expectedLanguage =
            normalizeText(
                market.second
            )

        val usdValues = variants.mapNotNull { it as? JsonObject }
            .filter {
                val rawLanguage =
                    it.string(
                        "language"
                    )
                        ?.trim()
                        .orEmpty()

                /*
                 * JustTCG v1 documents an omitted language as English.
                 * Treating blank as "" used to discard valid English prices.
                 */
                val actualLanguage =
                    normalizeText(
                        if (
                            rawLanguage.isBlank()
                        ) {
                            "English"
                        } else {
                            rawLanguage
                        }
                    )

                actualLanguage ==
                    expectedLanguage
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
        when (
            language.lowercase(
                Locale.ROOT
            )
        ) {
            "de" ->
                "pokemon" to "German"

            "en" ->
                "pokemon" to "English"

            "ko" ->
                "pokemon" to "Korean"

            "zh-cn" ->
                "pokemon" to "Chinese (S)"

            "zh-tw" ->
                "pokemon" to "Chinese (T)"

            "ja" ->
                "pokemon-japan" to "Japanese"

            "fr" ->
                "pokemon" to "French"

            "it" ->
                "pokemon" to "Italian"

            "es" ->
                "pokemon" to "Spanish"

            "pt" ->
                "pokemon" to "Portuguese"

            else ->
                null
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
            val body = response.body()
            val providerCode =
                runCatching {
                    json.parseToJsonElement(body)
                        .jsonObject
                        .string("code")
                }.getOrNull()

            when {
                providerCode == "REQUEST_LIMIT_EXCEEDED" -> {
                    requestLimitRetryAtMs =
                        System.currentTimeMillis() +
                            24L * 60L * 60L * 1000L
                    println("JustTCG paused for 24h: request limit exceeded")
                    null
                }

                response.statusCode() in 200..299 ->
                    json.parseToJsonElement(body).jsonObject

                response.statusCode() == 429 -> {
                    // Back off globally instead of repeating a known rate-limited
                    // request for every card in the worker's large batch.
                    requestLimitRetryAtMs = System.currentTimeMillis() + 60L * 60L * 1000L
                    println("JustTCG paused for 1h: HTTP 429 rate limit")
                    null
                }

                response.statusCode() >= 500 ->
                    throw IllegalStateException(
                        "JustTCG provider unavailable: HTTP ${response.statusCode()}"
                    )

                else ->
                    null
            }
        }.getOrElse { error ->
            if (
                error is IllegalStateException &&
                error.message?.startsWith("JustTCG ") == true
            ) {
                throw error
            }
            null
        }
    }
}

class EbaySoldPricingService(
    private val catalog: CardCatalogService,
    private val apiKey: String,
    private val ebayCookies: String = ""
) {
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
            rangeLowEur = sold?.rangeLowEur?.times(condition.factor),
            rangeHighEur = sold?.rangeHighEur?.times(condition.factor),
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

        if (unique.isEmpty()) return null

        val filtered = rejectOutliers(unique.values.toList())
        if (filtered.isEmpty()) return null

        val baseEur = filtered.average()
            .takeIf { it.isFinite() && it > 0.0 }
            ?: return null

        val rangeLowEur = filtered.minOrNull()
            ?.takeIf { it.isFinite() && it > 0.0 }
            ?: return null

        val rangeHighEur = filtered.maxOrNull()
            ?.takeIf { it.isFinite() && it > 0.0 }
            ?: return null

        println(
            "eBay pricing: card=${card.id} language=${card.languageCode} " +
                "variant=${variant.id} providerItems=${items.size} matched=${unique.size} " +
                "kept=${filtered.size} mean=$baseEur range=$rangeLowEur..$rangeHighEur " +
                "ebaySession=${if (ebayCookies.isBlank()) "none" else "configured"}"
        )

        return SoldSummary(
            baseEur = baseEur,
            rangeLowEur = rangeLowEur,
            rangeHighEur = rangeHighEur,
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
        val clean = values.filter { it.isFinite() && it > 0.0 }
        if (clean.size <= 2) return clean

        val center = median(clean)
        if (!center.isFinite() || center <= 0.0) return clean

        val deviations = clean.map { abs(it - center) }
        val mad = median(deviations)

        val filtered = if (mad.isFinite() && mad > 0.0) {
            clean.filter {
                abs(it - center) / mad <= 3.5
            }
        } else {
            /*
             * Wenn mehrere Verkäufe exakt am Median liegen, ist MAD = 0.
             * Dann fangen wir nur wirklich extreme Einzelpreise ab und
             * lassen einen breiten normalen Marktbereich unangetastet.
             */
            clean.filter {
                it >= center * 0.35 &&
                    it <= center * 2.85
            }
        }

        val minimumKept = if (clean.size >= 5) 3 else 2
        return if (filtered.size >= minimumKept) filtered else clean
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

internal class PkmnPricesCentralPricingProvider(
    private val apiKey: String
) : CentralPricingProvider {

    private val json = Json { ignoreUnknownKeys = true }
    private val http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(10))
        .followRedirects(HttpClient.Redirect.NORMAL)
        .build()

    @Volatile
    private var retryAtMs = 0L

    override suspend fun quote(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): CentralProviderQuote? {
        if (apiKey.isBlank()) return null
        if (System.currentTimeMillis() < retryAtMs) return null

        val providerLanguage =
            when (card.languageCode.lowercase(Locale.ROOT)) {
                "de" -> "German"
                "en" -> "English"
                "ja" -> "Japanese"
                else -> return null
            }

        val searchUrl =
            "https://api.pkmnprices.com/v1/cards" +
                "?name=" + encode(card.name) +
                "&number=" + encode(card.localId) +
                "&language=" + encode(providerLanguage) +
                "&per_page=100"

        val search = getJson(searchUrl) ?: return null
        val cards = search["data"] as? JsonArray ?: return null
        val expectedName = normalizeText(card.name)
        val expectedSet = normalizeText(card.setName)
        val expectedNumber = normalizeNumber(card.localId)

        val numbered =
            cards.mapNotNull { it as? JsonObject }
                .filter {
                    normalizeNumber(it.string("number").orEmpty()) ==
                        expectedNumber
                }

        val strict =
            numbered.filter { raw ->
                val name = normalizeText(raw.string("name").orEmpty())
                val setName =
                    (raw["set"] as? JsonObject)
                        ?.string("name")
                        ?.let(::normalizeText)
                        .orEmpty()

                val nameMatches =
                    name == expectedName ||
                        name.contains(expectedName) ||
                        expectedName.contains(name)

                val setMatches =
                    expectedSet.isBlank() ||
                        setName == expectedSet ||
                        setName.contains(expectedSet) ||
                        expectedSet.contains(setName)

                nameMatches && setMatches
            }

        val candidate =
            strict.singleOrNull()
                ?: numbered
                    .filter {
                        normalizeText(it.string("name").orEmpty()) ==
                            expectedName
                    }
                    .singleOrNull()
                ?: return null

        val providerId = candidate.string("id") ?: return null
        val details =
            getJson(
                "https://api.pkmnprices.com/v1/cards/" +
                    encode(providerId) +
                    "?currency=eur"
            ) ?: return null

        val prices = details["prices"] as? JsonArray ?: return null
        val eurValues =
            prices.mapNotNull { it as? JsonObject }
                .filter {
                    normalizeText(it.string("source").orEmpty()) ==
                        "cardmarket"
                }
                .filter {
                    normalizeText(it.string("currency").orEmpty()) ==
                        "eur"
                }
                .filter {
                    val condition =
                        normalizeText(it.string("condition").orEmpty())
                    condition == "near mint" || condition == "mint"
                }
                .filter {
                    printingMatches(
                        providerPrinting = it.string("variant"),
                        variant = variant
                    )
                }
                .mapNotNull { it.double("market_price") }
                .filter { it.isFinite() && it > 0.0 }

        if (eurValues.isEmpty()) return null

        val eur = median(eurValues)
        val baseEur = eur / PricingCondition.NEAR_MINT.factor

        return baseEur
            .takeIf { it.isFinite() && it > 0.0 }
            ?.let {
                CentralProviderQuote(
                    source = "PKMNPRICES_CARDMARKET",
                    baseEur = it
                )
            }
    }

    private fun printingMatches(
        providerPrinting: String?,
        variant: CatalogVariant
    ): Boolean {
        val printing = normalizeText(providerPrinting.orEmpty())
        if (printing.isBlank()) return false

        val foil = normalizeText(variant.foil.orEmpty())
        if (foil.isNotBlank()) {
            val foilMatches =
                when {
                    "cosmos" in foil ->
                        "cosmos" in printing
                    "cracked" in foil && "ice" in foil ->
                        "cracked" in printing && "ice" in printing
                    "master" in foil ->
                        "master" in printing && "ball" in printing
                    "poke" in foil || "poki" in foil ->
                        ("poke" in printing || "poki" in printing) &&
                            "ball" in printing
                    else ->
                        printing.contains(foil)
                }
            if (!foilMatches) return false
        }

        if (!variant.subtype.isNullOrBlank()) {
            val subtype = normalizeText(variant.subtype)
            if (!printing.contains(subtype)) return false
        }

        if (variant.stamps.isNotEmpty()) {
            val allStampsMatch =
                variant.stamps.all { stamp ->
                    val normalized = normalizeText(stamp)
                    when {
                        "1st edition" in normalized ||
                            "first edition" in normalized ->
                            "1st edition" in printing ||
                                "first edition" in printing
                        "pre release" in normalized ||
                            "prerelease" in normalized ->
                            "pre release" in printing ||
                                "prerelease" in printing
                        else ->
                            printing.contains(normalized)
                    }
                }
            if (!allStampsMatch) return false
        }

        if (
            !variant.foil.isNullOrBlank() ||
            !variant.subtype.isNullOrBlank() ||
            variant.stamps.isNotEmpty()
        ) {
            return true
        }

        return when (variant.legacyVariant.uppercase(Locale.ROOT)) {
            "REVERSE" ->
                "reverse" in printing
            "HOLO" ->
                "holo" in printing && "reverse" !in printing
            "NORMAL" ->
                ("normal" in printing || "non holo" in printing) &&
                    "reverse" !in printing
            else ->
                false
        }
    }

    private suspend fun getJson(url: String): JsonObject? =
        withContext(Dispatchers.IO) {
            runCatching {
                val request =
                    HttpRequest.newBuilder(URI.create(url))
                        .timeout(Duration.ofSeconds(20))
                        .header("Accept", "application/json")
                        .header("X-API-Key", apiKey)
                        .GET()
                        .build()

                val response =
                    http.send(
                        request,
                        HttpResponse.BodyHandlers.ofString()
                    )

                when {
                    response.statusCode() in 200..299 ->
                        json.parseToJsonElement(response.body()).jsonObject

                    response.statusCode() == 429 -> {
                        retryAtMs =
                            System.currentTimeMillis() +
                                60L * 60L * 1000L
                        println(
                            "PkmnPrices paused for 1h: rate limit reached"
                        )
                        null
                    }

                    response.statusCode() == 401 ||
                        response.statusCode() == 403 -> {
                        retryAtMs =
                            System.currentTimeMillis() +
                                24L * 60L * 60L * 1000L
                        println(
                            "PkmnPrices paused for 24h: HTTP " +
                                response.statusCode()
                        )
                        null
                    }

                    response.statusCode() >= 500 ->
                        throw IllegalStateException(
                            "PkmnPrices unavailable: HTTP " +
                                response.statusCode()
                        )

                    else ->
                        null
                }
            }.getOrElse { error ->
                if (
                    error is IllegalStateException &&
                    error.message?.startsWith("PkmnPrices ") == true
                ) {
                    throw error
                }
                null
            }
        }
}

internal class PokemonTcgIoCentralPricingProvider :
    CentralPricingProvider {

    private val json = Json { ignoreUnknownKeys = true }
    private val http =
        HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build()

    private val paceLock = Any()

    @Volatile
    private var nextRequestAtMs = 0L

    @Volatile
    private var fxCachedAtMs = 0L

    @Volatile
    private var usdEurRate: Double? = null

    override suspend fun quote(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): CentralProviderQuote? {
        if (!card.languageCode.equals("en", ignoreCase = true)) return null

        if (
            variant.stamps.isNotEmpty() ||
            !variant.subtype.isNullOrBlank() ||
            !variant.foil.isNullOrBlank() ||
            (!variant.size.isNullOrBlank() &&
                !variant.size.equals("standard", ignoreCase = true))
        ) {
            return null
        }

        val direct =
            getJson(
                "https://api.pokemontcg.io/v2/cards/" +
                    encode(card.id)
            )
                ?.get("data") as? JsonObject

        val raw =
            direct
                ?.takeIf {
                    exactMatches(
                        raw = it,
                        card = card
                    )
                }
                ?: searchExact(card)
                ?: return null

        val cardmarket =
            (raw["cardmarket"] as? JsonObject)
                ?.get("prices") as? JsonObject

        val cardmarketEur =
            when (variant.legacyVariant.uppercase(Locale.ROOT)) {
                "NORMAL" ->
                    firstPositive(
                        cardmarket,
                        "trendPrice",
                        "avg7",
                        "avg30",
                        "averageSellPrice",
                        "avg1"
                    )
                "REVERSE" ->
                    firstPositive(
                        cardmarket,
                        "reverseHoloTrend",
                        "reverseHoloAvg7",
                        "reverseHoloAvg30",
                        "reverseHoloSell",
                        "reverseHoloAvg1"
                    )
                else -> null
            }

        if (cardmarketEur != null) {
            return CentralProviderQuote(
                source = "POKEMONTCGIO_CARDMARKET",
                baseEur =
                    cardmarketEur /
                        PricingCondition.NEAR_MINT.factor
            )
        }

        val tcgplayerPrices =
            (raw["tcgplayer"] as? JsonObject)
                ?.get("prices") as? JsonObject
                ?: return null

        val priceKey =
            when (variant.legacyVariant.uppercase(Locale.ROOT)) {
                "NORMAL" -> "normal"
                "HOLO" -> "holofoil"
                "REVERSE" -> "reverseHolofoil"
                else -> return null
            }

        val priceObject =
            tcgplayerPrices[priceKey] as? JsonObject
                ?: return null

        val usd =
            firstPositive(
                priceObject,
                "market",
                "mid",
                "low"
            ) ?: return null

        val rate = usdToEurRate() ?: return null
        val eur = usd * rate

        return CentralProviderQuote(
            source = "POKEMONTCGIO_TCGPLAYER",
            baseEur =
                eur /
                    PricingCondition.NEAR_MINT.factor
        )
    }

    private suspend fun searchExact(
        card: CatalogCardDetails
    ): JsonObject? {
        val query =
            "number:" + card.localId +
                " name:" + card.name

        val root =
            getJson(
                "https://api.pokemontcg.io/v2/cards" +
                    "?q=" + encode(query) +
                    "&pageSize=50"
            ) ?: return null

        val rows =
            root["data"] as? JsonArray
                ?: return null

        return rows
            .mapNotNull { it as? JsonObject }
            .filter {
                exactMatches(
                    raw = it,
                    card = card
                )
            }
            .singleOrNull()
    }

    private fun exactMatches(
        raw: JsonObject,
        card: CatalogCardDetails
    ): Boolean =
        normalizeNumber(raw.string("number").orEmpty()) ==
            normalizeNumber(card.localId) &&
            normalizeText(raw.string("name").orEmpty()) ==
                normalizeText(card.name)

    private suspend fun usdToEurRate(): Double? {
        val now = System.currentTimeMillis()
        val cached = usdEurRate

        if (
            cached != null &&
            now - fxCachedAtMs <
                6L * 60L * 60L * 1000L
        ) {
            return cached
        }

        val root =
            getJsonUnpaced(
                "https://api.frankfurter.dev/v2/rate/USD/EUR"
            ) ?: return cached

        val rate =
            root.double("rate")
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }
                ?: return cached

        usdEurRate = rate
        fxCachedAtMs = now
        return rate
    }

    private suspend fun getJson(
        url: String
    ): JsonObject? =
        withContext(Dispatchers.IO) {
            pace()

            runCatching {
                val request =
                    HttpRequest.newBuilder(URI.create(url))
                        .timeout(Duration.ofSeconds(20))
                        .header("Accept", "application/json")
                        .GET()
                        .build()

                val response =
                    http.send(
                        request,
                        HttpResponse.BodyHandlers.ofString()
                    )

                when {
                    response.statusCode() in 200..299 ->
                        json.parseToJsonElement(
                            response.body()
                        ).jsonObject
                    response.statusCode() == 404 ->
                        null
                    response.statusCode() == 429 ->
                        null
                    response.statusCode() >= 500 ->
                        null
                    else ->
                        null
                }
            }.getOrNull()
        }

    private suspend fun getJsonUnpaced(
        url: String
    ): JsonObject? =
        withContext(Dispatchers.IO) {
            runCatching {
                val request =
                    HttpRequest.newBuilder(URI.create(url))
                        .timeout(Duration.ofSeconds(15))
                        .header("Accept", "application/json")
                        .GET()
                        .build()

                val response =
                    http.send(
                        request,
                        HttpResponse.BodyHandlers.ofString()
                    )

                if (response.statusCode() !in 200..299) {
                    return@runCatching null
                }

                json.parseToJsonElement(
                    response.body()
                ).jsonObject
            }.getOrNull()
        }

    private fun pace() {
        synchronized(paceLock) {
            val now = System.currentTimeMillis()
            val waitMs =
                (nextRequestAtMs - now)
                    .coerceAtLeast(0L)

            if (waitMs > 0L) {
                Thread.sleep(waitMs)
            }

            nextRequestAtMs =
                System.currentTimeMillis() +
                    2100L
        }
    }

    private fun firstPositive(
        raw: JsonObject?,
        vararg keys: String
    ): Double? =
        keys.firstNotNullOfOrNull { key ->
            raw
                ?.double(key)
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }
        }
}
