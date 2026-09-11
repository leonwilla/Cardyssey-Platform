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
import java.time.LocalDate
import java.time.ZoneOffset
import java.time.temporal.ChronoUnit
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
        val updatedAtMs: Long,
        val recentSales: List<EbayRecentSaleResponse>
    )

    private data class MatchedSale(
        val stableId: String,
        val basePrice: Double,
        val soldDate: LocalDate,
        val sale: EbayRecentSaleResponse
    )

    private data class ListingMatchContext(
        val expectedSetName: String,
        val foreignExpectedSetName: String?,
        val conflictingSetNames: Set<String>
    )

    private data class VariantTraits(
        val firstEdition: Boolean,
        val shadowless: Boolean,
        val unlimited: Boolean,
        val copyright19992000: Boolean,
        val specialStamps: Set<String>
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
            updatedAtMs = sold?.updatedAtMs,
            recentSales = sold?.recentSales.orEmpty()
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

        val localSets = runCatching {
            catalog.sets(card.languageCode)
        }.getOrDefault(emptyList())

        val englishSets = if (card.languageCode != "en") {
            runCatching { catalog.sets("en") }.getOrDefault(emptyList())
        } else {
            localSets
        }

        val expectedSetName = normalizeCompSniperText(card.setName)
        val englishExpectedSetName = englishSets
            .firstOrNull { it.id == card.setId }
            ?.name
            ?.let(::normalizeCompSniperText)
            ?.takeIf { it.isNotBlank() && it != expectedSetName }

        val conflictingSetNames = (localSets + englishSets)
            .asSequence()
            .filter { it.id != card.setId }
            .map { normalizeCompSniperText(it.name) }
            .filter(::isUsefulSetPhrase)
            .toSet()

        val matchContext = ListingMatchContext(
            expectedSetName = expectedSetName,
            foreignExpectedSetName = englishExpectedSetName,
            conflictingSetNames = conflictingSetNames
        )

        /*
         * Provider-Suche bewusst breit halten. Die exakte physische Variante
         * wird lokal anhand der TCGdex-Variantenmerkmale validiert. So verlieren
         * wir seltene Listings nicht nur deshalb, weil ein Verkäufer z. B.
         * "1. Auflage" statt "1st Edition" schreibt.
         */
        val query = listOf(
            card.name,
            printedNumber,
            searchLanguageToken(card.languageCode)
        )
            .filter(String::isNotBlank)
            .joinToString(" ")

        val url = "https://api.compsniper.com/v1/scrape" +
            "?keyword=${encodeCompSniper(query)}" +
            "&ebaySite=ebay.de&page=1&count=240" +
            "&sortOrder=endedRecently&sold=true" +
            "&exactMatch=false&relevance=false"

        val root = getJson(url) ?: return null
        val items = root["items"] as? JsonArray ?: return null
        val unique = linkedMapOf<String, MatchedSale>()

        items.mapNotNull { it as? JsonObject }.forEach { item ->
            if (!listingMatches(item, card, variant, matchContext)) return@forEach

            if (
                item.boolValue("bestOfferAccepted") == true ||
                item.boolValue("acceptedBestOffer") == true ||
                item.boolValue("isBestOffer") == true ||
                item.boolValue("invalid") == true ||
                item.boolValue("isInvalid") == true
            ) {
                return@forEach
            }

            val currency = item.stringValue("soldCurrency")
                ?.uppercase(Locale.ROOT)
            if (currency != "EUR") return@forEach

            val rawPrice = item.doubleValue("soldPrice") ?: return@forEach
            if (!rawPrice.isFinite() || rawPrice <= 0.0) return@forEach

            val basePrice = normalizeSoldCondition(item, rawPrice)
                ?: return@forEach
            if (!basePrice.isFinite() || basePrice <= 0.0) return@forEach

            val endedAt = item.stringValue("endedAt")
                ?: item.stringValue("soldDate")
            val soldDate = parseCompSniperSoldDate(endedAt)
                ?: return@forEach

            val stableId = item.stringValue("itemId")
                ?: item.stringValue("listingId")
                ?: item.stringValue("id")
                ?: item.stringValue("url")
                ?: listOf(
                    normalizeCompSniperText(item.stringValue("title").orEmpty()),
                    rawPrice.toString(),
                    endedAt.orEmpty()
                ).joinToString("|")

            val itemId = item.stringValue("itemId")
            val directUrl = item.stringValue("url")
                ?.takeIf { it.startsWith("https://", ignoreCase = true) }
                ?: itemId?.let { "https://www.ebay.de/itm/$it" }

            unique.putIfAbsent(
                stableId,
                MatchedSale(
                    stableId = stableId,
                    basePrice = basePrice,
                    soldDate = soldDate,
                    sale = EbayRecentSaleResponse(
                        itemId = itemId,
                        title = item.stringValue("title").orEmpty(),
                        soldPriceEur = rawPrice,
                        rawCondition = item.stringValue("condition"),
                        endedAt = endedAt,
                        url = directUrl
                    )
                )
            )
        }

        if (unique.isEmpty()) return null

        val today = LocalDate.now(ZoneOffset.UTC)
        val windowSelections = listOf(30, 60, 90).map { days ->
            val candidates = unique.values
                .asSequence()
                .filter { matched ->
                    val ageDays = ChronoUnit.DAYS.between(matched.soldDate, today)
                    ageDays in 0L..days.toLong()
                }
                .sortedWith(
                    compareByDescending<MatchedSale> { it.soldDate }
                        .thenByDescending { it.sale.itemId.orEmpty() }
                )
                .take(MAX_MARKET_SALES)
                .toList()

            days to rejectOutliers(candidates)
        }

        val selectedWindow = windowSelections
            .firstOrNull { (_, sales) -> sales.size >= MIN_MARKET_SALES }
            ?: windowSelections.last()
        val selectedWindowDays = selectedWindow.first
        val filtered = selectedWindow.second

        if (filtered.isEmpty()) return null

        val prices = filtered.map { it.basePrice }
        val mean = prices.average()
            .takeIf { it.isFinite() && it > 0.0 }
            ?: return null
        val low = prices.minOrNull()
            ?.takeIf { it.isFinite() && it > 0.0 }
            ?: return null
        val high = prices.maxOrNull()
            ?.takeIf { it.isFinite() && it > 0.0 }
            ?: return null

        val recentSales = filtered
            .sortedWith(
                compareByDescending<MatchedSale> { it.soldDate }
                    .thenByDescending { it.sale.itemId.orEmpty() }
            )
            .take(10)
            .map { it.sale }

        println(
            "eBay pricing: provider=COMPSNIPER card=${card.id} language=${card.languageCode} " +
                "variant=${variant.id} providerItems=${items.size} matched=${unique.size} " +
                "windowDays=$selectedWindowDays kept=${filtered.size} mean=$mean " +
                "range=$low..$high recent=${recentSales.size}"
        )

        return SoldSummary(
            baseEur = mean,
            rangeLowEur = low,
            rangeHighEur = high,
            sampleCount = filtered.size,
            updatedAtMs = System.currentTimeMillis(),
            recentSales = recentSales
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
        context: ListingMatchContext
    ): Boolean {
        val title = normalizeCompSniperText(item.stringValue("title").orEmpty())
        if (title.isBlank()) return false
        if (looksLikeBundleOrGraded(title)) return false

        val cardName = normalizeCompSniperText(card.name)
        if (cardName.isNotBlank() && !containsPhrase(title, cardName)) return false

        if (!cardNumberMatches(title, card.localId, card.officialCount)) return false
        if (
            !languageMatches(
                title = title,
                language = card.languageCode,
                expectedSetName = context.expectedSetName,
                foreignExpectedSetName = context.foreignExpectedSetName
            )
        ) {
            return false
        }
        if (context.conflictingSetNames.any { containsPhrase(title, it) }) return false

        return variantMatches(title, card, variant)
    }

    private fun cardNumberMatches(
        title: String,
        localId: String,
        officialCount: Int
    ): Boolean {
        val localNumeric = localId.trim().toIntOrNull()
        if (localNumeric != null && officialCount > 0) {
            val pattern = Regex(
                "(?<![0-9])0*${Regex.escape(localNumeric.toString())}\\s*/\\s*0*${officialCount}(?![0-9])"
            )
            return pattern.containsMatchIn(title)
        }

        val normalized = normalizeCompSniperText(localId)
        return normalized.isNotBlank() && containsPhrase(title, normalized)
    }

    private fun looksLikeBundleOrGraded(title: String): Boolean {
        val padded = " $title "
        val blocked = listOf(
            " psa ",
            " bgs ",
            " cgc ",
            " sgc ",
            " beckett ",
            " graded ",
            " grading ",
            " gegradet ",
            " ace grading ",
            " gem mint 10 ",
            " grade 10 ",
            " konvolut ",
            " sammlung ",
            " komplettes set ",
            " complete set ",
            " bundle ",
            " lot ",
            " auswahl ",
            " choose ",
            " choice ",
            " playset "
        )

        if (blocked.any { it in padded }) return true
        if (Regex("""\bace\s*(?:grade\s*)?\d{1,2}\b""").containsMatchIn(title)) return true
        if (Regex("""\b(?:psa|bgs|cgc|sgc)\s*\d{1,2}\b""").containsMatchIn(title)) return true

        /* Mehrfach-Angebote dürfen nie als Einzelkarten-Verkauf in den Mittelwert. */
        if (Regex("""\b(?:[2-9]|[1-9][0-9]+)\s*x\b""").containsMatchIn(title)) return true
        if (Regex("""\bx\s*(?:[2-9]|[1-9][0-9]+)\b""").containsMatchIn(title)) return true
        if (
            Regex(
                """\b(?:[2-9]|[1-9][0-9]+)\s*(?:karten|cards|stuck|stueck|stk|copies|exemplare)\b"""
            ).containsMatchIn(title)
        ) {
            return true
        }
        if (Regex("""\b[2-9]er\s*(?:set|pack|lot)\b""").containsMatchIn(title)) return true

        return false
    }

    /*
     * Physische Varianten werden als Fingerprint geprüft, nicht nur als
     * "Holo/Reverse/Normal". Das ist besonders bei Vintage entscheidend:
     * Shadowless, Unlimited und 1st Edition können bei derselben Kartennummer
     * preislich um ein Vielfaches auseinanderliegen.
     *
     * Regel: lieber keinen eBay-Wert als Verkäufe einer anderen physischen
     * Variante in den Mittelwert zu mischen.
     */
    private fun variantMatches(
        title: String,
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): Boolean {
        val padded = " $title "
        val reverse =
            " reverse " in padded ||
                " reverse holo " in padded ||
                " reverse foil " in padded
        val nonHolo =
            " non holo " in padded ||
                " nonholo " in padded ||
                " non foil " in padded
        val holo =
            " holo " in padded ||
                " holofoil " in padded ||
                " foil " in padded ||
                " holographic " in padded

        val legacy = variant.legacyVariant.uppercase(Locale.ROOT)
        val legacyFamilies = card.variants
            .map { it.legacyVariant.uppercase(Locale.ROOT) }
            .toSet()
        val hasCompetingFoilFamily = legacyFamilies.size > 1

        val baseMatches = when (legacy) {
            "REVERSE" ->
                if (hasCompetingFoilFamily) reverse else !nonHolo

            "HOLO" ->
                !reverse && !nonHolo && (!hasCompetingFoilFamily || holo)

            "NORMAL" ->
                !reverse && !holo

            /* Legacy-1st-Edition hat keinen eigenen Foil-Marker. */
            "FIRST_EDITION" ->
                !reverse && !nonHolo

            else ->
                false
        }

        if (!baseMatches) return false

        val target = variantTraits(variant)
        val firstEditionInTitle = containsAnyPhrase(title, FIRST_EDITION_MARKERS)
        val shadowlessInTitle = containsAnyPhrase(title, SHADOWLESS_MARKERS)
        val unlimitedInTitle = containsAnyPhrase(title, UNLIMITED_MARKERS)
        val copyrightInTitle = containsAnyPhrase(title, COPYRIGHT_1999_2000_MARKERS)

        /* 1st Edition ist niemals mit Unlimited austauschbar. */
        if (target.firstEdition) {
            if (!firstEditionInTitle) return false
        } else if (firstEditionInTitle) {
            return false
        }

        /*
         * Bei Base-Set-artigen Varianten kann "1st Edition" Shadowless bereits
         * eindeutig implizieren. Das wird aus den vorhandenen Varianten
         * abgeleitet statt hart auf ein bestimmtes Set zu codieren.
         */
        if (target.shadowless) {
            val sameLegacyFirstEditions = card.variants
                .filter {
                    it.legacyVariant.equals(
                        variant.legacyVariant,
                        ignoreCase = true
                    ) && variantTraits(it).firstEdition
                }
            val firstEditionImpliesShadowless =
                target.firstEdition &&
                    sameLegacyFirstEditions.isNotEmpty() &&
                    sameLegacyFirstEditions.all { variantTraits(it).shadowless }

            if (!shadowlessInTitle && !firstEditionImpliesShadowless) return false
        } else if (shadowlessInTitle) {
            return false
        }

        if (!target.unlimited && unlimitedInTitle) return false

        if (target.copyright19992000) {
            if (!copyrightInTitle) return false
        } else if (copyrightInTitle) {
            return false
        }

        /*
         * Weitere TCGdex-Stamps werden generisch gegeneinander abgegrenzt.
         * Nur wenn innerhalb derselben Grundvariante tatsächlich konkurrierende
         * Stamps existieren, verlangen wir den Marker im Listing-Titel.
         */
        val related = card.variants.filter {
            it.legacyVariant.equals(
                variant.legacyVariant,
                ignoreCase = true
            )
        }
        val targetStamps = target.specialStamps
        val competingStamps = related
            .flatMap { variantTraits(it).specialStamps }
            .toSet()

        for (stamp in targetStamps) {
            val needsExplicitMarker = related.any {
                stamp !in variantTraits(it).specialStamps
            }
            if (needsExplicitMarker && !containsPhrase(title, stamp)) return false
        }

        for (stamp in competingStamps - targetStamps) {
            if (containsPhrase(title, stamp)) return false
        }

        return true
    }

    private fun variantTraits(variant: CatalogVariant): VariantTraits {
        val subtype = normalizeCompSniperText(variant.subtype.orEmpty())
        val compactSubtype = subtype.replace(" ", "")
        val normalizedStamps = variant.stamps
            .map(::normalizeCompSniperText)
            .filter(String::isNotBlank)
            .toSet()

        val firstEdition =
            variant.legacyVariant.equals("FIRST_EDITION", ignoreCase = true) ||
                normalizedStamps.any(::isFirstEditionMarker)

        return VariantTraits(
            firstEdition = firstEdition,
            shadowless =
                subtype == "shadowless" ||
                    subtype == "schattenlos",
            unlimited =
                subtype == "unlimited" ||
                    subtype == "unbegrenzt",
            copyright19992000 =
                compactSubtype in setOf(
                    "copyright19992000",
                    "19992000"
                ),
            specialStamps = normalizedStamps
                .filterNot(::isFirstEditionMarker)
                .toSet()
        )
    }

    private fun isFirstEditionMarker(value: String): Boolean =
        normalizeCompSniperText(value) in FIRST_EDITION_MARKERS

    private fun containsAnyPhrase(
        title: String,
        phrases: Set<String>
    ): Boolean =
        phrases.any { containsPhrase(title, it) }

    private fun languageMatches(
        title: String,
        language: String,
        expectedSetName: String,
        foreignExpectedSetName: String?
    ): Boolean {
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

        if (foreignMarkers.any { containsPhrase(title, it) }) return false

        if (language == "de") {
            val explicitGerman = explicit["de"].orEmpty().any {
                containsPhrase(title, it)
            } || containsPhrase(title, "de")

            val localizedSetEvidence =
                expectedSetName.isNotBlank() &&
                    expectedSetName != foreignExpectedSetName &&
                    containsPhrase(title, expectedSetName)

            if (!explicitGerman && !localizedSetEvidence) {
                return false
            }
        }

        if (
            foreignExpectedSetName != null &&
            containsPhrase(title, foreignExpectedSetName)
        ) {
            val positiveMarkers = explicit[language].orEmpty()
            if (positiveMarkers.none { containsPhrase(title, it) }) {
                return false
            }
        }

        return true
    }

    private fun normalizeSoldCondition(
        item: JsonObject,
        rawPrice: Double
    ): Double? {
        val title = normalizeCompSniperText(item.stringValue("title").orEmpty())
        val conditionText = normalizeCompSniperText(
            listOf(
                title,
                item.stringValue("condition").orEmpty(),
                item.stringValue("itemCondition").orEmpty(),
                item.stringValue("conditionName").orEmpty()
            ).joinToString(" ")
        )

        if (
            listOf(
                "damaged",
                "beschadigt",
                "poor condition",
                "knick",
                "crease"
            ).any { normalizeCompSniperText(it) in conditionText }
        ) {
            return null
        }

        val soldCondition = when {
            "near mint" in conditionText ||
                "boosterfrisch" in conditionText ||
                "pack fresh" in conditionText ||
                Regex("""\bnm\b""").containsMatchIn(conditionText) ->
                PricingCondition.NEAR_MINT

            Regex("""\bmint\b""").containsMatchIn(conditionText) ->
                PricingCondition.MINT

            "excellent" in conditionText ||
                "sehr gut" in conditionText ||
                "light played" in conditionText ||
                "lightly played" in conditionText ||
                Regex("""\bex\b""").containsMatchIn(conditionText) ->
                PricingCondition.EXCELLENT

            "heavily played" in conditionText ||
                "heavy played" in conditionText ||
                "played" in conditionText ||
                "gespielt" in conditionText ||
                Regex("""\bhp\b""").containsMatchIn(conditionText) ->
                PricingCondition.PLAYED

            "good" in conditionText ||
                Regex("""\bgut\b""").containsMatchIn(conditionText) ->
                PricingCondition.GOOD

            else -> PricingCondition.NEAR_MINT
        }

        return rawPrice / soldCondition.factor
    }

    private fun rejectOutliers(values: List<MatchedSale>): List<MatchedSale> {
        val clean = values.filter { it.basePrice.isFinite() && it.basePrice > 0.0 }
        if (clean.size <= 2) return clean

        val center = medianCompSniper(clean.map { it.basePrice })
        if (!center.isFinite() || center <= 0.0) return clean

        if (clean.size <= 4) {
            val conservative = clean.filter {
                it.basePrice >= center * 0.20 && it.basePrice <= center * 5.0
            }
            return if (conservative.size >= 2) conservative else clean
        }

        val deviations = clean.map { abs(it.basePrice - center) }
        val mad = medianCompSniper(deviations)

        val filtered = if (mad.isFinite() && mad > 0.0) {
            clean.filter {
                0.6745 * abs(it.basePrice - center) / mad <= 3.5
            }
        } else {
            clean.filter {
                it.basePrice >= center * 0.35 && it.basePrice <= center * 2.85
            }
        }

        return if (filtered.size >= 3) filtered else clean
    }

    companion object {
        private const val MIN_MARKET_SALES = 10
        private const val MAX_MARKET_SALES = 30

        private val FIRST_EDITION_MARKERS = setOf(
            "1st edition",
            "first edition",
            "1st ed",
            "first ed",
            "1 edition",
            "1 auflage",
            "erste auflage"
        )

        private val SHADOWLESS_MARKERS = setOf(
            "shadowless",
            "schattenlos"
        )

        private val UNLIMITED_MARKERS = setOf(
            "unlimited",
            "unbegrenzt"
        )

        private val COPYRIGHT_1999_2000_MARKERS = setOf(
            "1999 2000",
            "copyright 1999 2000"
        )
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

private fun parseCompSniperSoldDate(raw: String?): LocalDate? {
    val normalized = raw
        ?.trim()
        ?.takeIf(String::isNotBlank)
        ?: return null

    return runCatching {
        LocalDate.parse(normalized.take(10))
    }.getOrNull()
}

private fun normalizeCompSniperText(raw: String): String =
    java.text.Normalizer.normalize(raw, java.text.Normalizer.Form.NFD)
        .replace("\\p{M}+".toRegex(), "")
        .lowercase(Locale.ROOT)
        .replace("[^a-z0-9/]+".toRegex(), " ")
        .trim()
        .replace("\\s+".toRegex(), " ")

private fun containsPhrase(text: String, phrase: String): Boolean {
    if (phrase.isBlank()) return false
    return Regex("(?:^| )${Regex.escape(phrase)}(?: |$)").containsMatchIn(text)
}

private fun isUsefulSetPhrase(raw: String): Boolean {
    val normalized = normalizeCompSniperText(raw)
    if (normalized.length < 7) return false
    val words = normalized.split(' ').filter(String::isNotBlank)
    return words.size >= 2 || normalized.length >= 12
}

private fun searchLanguageToken(language: String): String =
    when (language.lowercase(Locale.ROOT)) {
        "de" -> "Deutsch"
        "en" -> "English"
        "fr" -> "French"
        "it" -> "Italian"
        "es" -> "Spanish"
        "pt" -> "Portuguese"
        "ja" -> "Japanese"
        else -> ""
    }

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
