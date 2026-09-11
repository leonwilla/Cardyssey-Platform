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
        val typeKey: String,
        val subtypeKey: String?,
        val foilKey: String?,
        val sizeKey: String?,
        val firstEdition: Boolean,
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
         * Name + exakte Nummer + Sprache bleiben die stabile Basis.
         * Nur eindeutige physische Merkmale werden zusätzlich in die Provider-
         * Suche aufgenommen. Die vollständige Validierung passiert trotzdem
         * lokal, weil eBay-Verkäufer dieselbe Eigenschaft unterschiedlich
         * benennen können.
         */
        val query = (
            listOf(
                card.name,
                printedNumber,
                searchLanguageToken(card.languageCode)
            ) +
                variantSearchTokens(card, variant)
            )
            .filter(String::isNotBlank)
            .distinct()
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
                "variant=${variant.id} type=${variant.type} subtype=${variant.subtype} " +
                "foil=${variant.foil} size=${variant.size} stamps=${variant.stamps.joinToString("+")} " +
                "providerItems=${items.size} matched=${unique.size} " +
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
     * Exakter physischer Fingerprint aus TCGdex:
     * type + subtype + foil + stamps + size.
     *
     * Der alte Legacy-Basistyp reicht dafür nicht. Metal, Lenticular,
     * Master-Ball/Poké-Ball-Foils, Jumbo und Promo-/Turnier-Stamps werden hier
     * genauso berücksichtigt wie 1st Edition/Shadowless/Unlimited.
     *
     * Regel: Fehlt bei einer unterscheidbaren Sondervariante die nötige
     * Titel-Evidenz, wird der Verkauf verworfen. Ein fehlender Preis ist besser
     * als ein Preis einer anderen physischen Karte.
     */
    private fun variantMatches(
        title: String,
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): Boolean {
        val target = variantTraits(variant)

        if (!typeMatches(title, card, target)) return false
        if (!sizeMatches(title, target)) return false

        val firstEditionInTitle =
            containsAnyPhrase(title, FIRST_EDITION_MARKERS)

        if (target.firstEdition) {
            if (!firstEditionInTitle) return false
        } else if (firstEditionInTitle) {
            return false
        }

        if (!subtypeMatches(title, card, variant, target)) return false
        if (!foilMatches(title, card, variant, target)) return false
        if (!stampMatches(title, card, variant, target)) return false

        return true
    }

    private fun typeMatches(
        title: String,
        card: CatalogCardDetails,
        target: VariantTraits
    ): Boolean {
        val allTypes = card.variants
            .map { variantTraits(it).typeKey }
            .filter(String::isNotBlank)
            .toSet()
        val hasCompetingType =
            allTypes.any { it != target.typeKey }

        val reverse = containsAnyPhrase(
            title,
            aliasesForType("reverse")
        )
        val nonHolo = containsAnyPhrase(
            title,
            NON_HOLO_MARKERS
        )
        val holo = !nonHolo && containsAnyPhrase(
            title,
            aliasesForType("holo")
        )
        val metal = containsAnyPhrase(
            title,
            aliasesForType("metal")
        )
        val lenticular = containsAnyPhrase(
            title,
            aliasesForType("lenticular")
        )

        return when (target.typeKey) {
            "normal" ->
                !reverse && !holo && !metal && !lenticular

            "holo" ->
                !reverse && !nonHolo && !metal && !lenticular &&
                    (!hasCompetingType || holo)

            "reverse" ->
                !nonHolo && !metal && !lenticular &&
                    (!hasCompetingType || reverse)

            "metal" ->
                metal && !lenticular

            "lenticular" ->
                lenticular && !metal

            else -> {
                val ownAliases = aliasesForType(target.typeKey)
                val competingMentioned = allTypes
                    .filter { it != target.typeKey }
                    .any { type ->
                        containsAnyPhrase(
                            title,
                            aliasesForType(type)
                        )
                    }

                !competingMentioned &&
                    (!hasCompetingType || containsAnyPhrase(title, ownAliases))
            }
        }
    }

    private fun sizeMatches(
        title: String,
        target: VariantTraits
    ): Boolean {
        val jumboInTitle =
            containsAnyPhrase(title, JUMBO_MARKERS)

        return if (target.sizeKey == "jumbo") {
            jumboInTitle
        } else {
            !jumboInTitle
        }
    }

    private fun subtypeMatches(
        title: String,
        card: CatalogCardDetails,
        variant: CatalogVariant,
        target: VariantTraits
    ): Boolean {
        val subtype = target.subtypeKey
        val shadowlessInTitle =
            containsAnyPhrase(title, aliasesForSubtype("shadowless"))
        val unlimitedInTitle =
            containsAnyPhrase(title, aliasesForSubtype("unlimited"))
        val targetShadowlessFamily =
            subtype == "shadowless" ||
                subtype == "shadowless red cheek"

        if (targetShadowlessFamily) {
            val firstEditionImpliesPlainShadowless =
                subtype == "shadowless" &&
                    target.firstEdition &&
                    card.variants
                        .filter {
                            it.id != variant.id &&
                                variantTraits(it).typeKey == target.typeKey &&
                                variantTraits(it).firstEdition
                        }
                        .let { siblings ->
                            siblings.isEmpty() ||
                                siblings.all {
                                    variantTraits(it).subtypeKey == "shadowless"
                                }
                        }

            if (
                !shadowlessInTitle &&
                !firstEditionImpliesPlainShadowless
            ) {
                return false
            }
        } else if (shadowlessInTitle) {
            return false
        }

        if (subtype == "unlimited") {
            if (shadowlessInTitle) return false
            /* "Unlimited" wird von Verkäufern oft weggelassen. */
        } else if (unlimitedInTitle) {
            return false
        }

        val related = card.variants
            .filter { other ->
                if (other.id == variant.id) return@filter false
                val traits = variantTraits(other)
                traits.typeKey == target.typeKey &&
                    traits.sizeKey == target.sizeKey &&
                    traits.foilKey == target.foilKey &&
                    traits.specialStamps == target.specialStamps
            }

        val competingSubtypes = related
            .mapNotNull { variantTraits(it).subtypeKey }
            .filter { it != subtype }
            .toSet()

        if (
            subtype != null &&
            subtype !in setOf("shadowless", "unlimited")
        ) {
            val needsExplicitMarker =
                subtype in ALWAYS_EXPLICIT_SUBTYPES ||
                    related.any {
                        variantTraits(it).subtypeKey != subtype
                    }

            if (
                needsExplicitMarker &&
                !containsAnyPhrase(
                    title,
                    aliasesForSubtype(subtype)
                )
            ) {
                return false
            }
        }

        for (competitor in competingSubtypes) {
            if (
                containsAnyPhrase(
                    title,
                    aliasesForSubtype(competitor)
                )
            ) {
                return false
            }
        }

        return true
    }

    private fun foilMatches(
        title: String,
        card: CatalogCardDetails,
        variant: CatalogVariant,
        target: VariantTraits
    ): Boolean {
        val related = card.variants
            .filter { other ->
                if (other.id == variant.id) return@filter false
                val traits = variantTraits(other)
                traits.typeKey == target.typeKey &&
                    traits.subtypeKey == target.subtypeKey &&
                    traits.sizeKey == target.sizeKey &&
                    traits.specialStamps == target.specialStamps
            }

        val competingFoils = related
            .map { variantTraits(it).foilKey }
            .filter { it != target.foilKey }
            .toSet()

        if (
            target.foilKey != null &&
            competingFoils.isNotEmpty() &&
            !containsAnyPhrase(
                title,
                aliasesForFoil(target.foilKey)
            )
        ) {
            return false
        }

        for (competitor in competingFoils.filterNotNull()) {
            if (
                containsAnyPhrase(
                    title,
                    aliasesForFoil(competitor)
                )
            ) {
                return false
            }
        }

        return true
    }

    private fun stampMatches(
        title: String,
        card: CatalogCardDetails,
        variant: CatalogVariant,
        target: VariantTraits
    ): Boolean {
        /*
         * Ein Stamp ist Teil der physischen Karte, nicht nur Dekoration im
         * UI. Für eine gestempelte Zielvariante verlangen wir deshalb explizite
         * Titel-Evidenz. First Edition wurde oben separat behandelt.
         */
        for (stamp in target.specialStamps) {
            if (
                !containsAnyPhrase(
                    title,
                    aliasesForStamp(stamp)
                )
            ) {
                return false
            }
        }

        val competingStamps = card.variants
            .asSequence()
            .filter { it.id != variant.id }
            .flatMap { variantTraits(it).specialStamps.asSequence() }
            .filter { it !in target.specialStamps }
            .toSet()

        for (competitor in competingStamps) {
            if (
                containsAnyPhrase(
                    title,
                    aliasesForStamp(competitor)
                )
            ) {
                return false
            }
        }

        return true
    }

    private fun variantTraits(
        variant: CatalogVariant
    ): VariantTraits {
        val typeKey =
            normalizeCompSniperText(variant.type)
                .ifBlank { "normal" }
        val subtypeKey = variant.subtype
            ?.let(::normalizeCompSniperText)
            ?.takeIf(String::isNotBlank)
        val foilKey = variant.foil
            ?.let(::normalizeCompSniperText)
            ?.takeIf(String::isNotBlank)
        val sizeKey = variant.size
            ?.let(::normalizeCompSniperText)
            ?.takeIf(String::isNotBlank)
        val normalizedStamps = variant.stamps
            .map(::normalizeCompSniperText)
            .filter(String::isNotBlank)
            .toSet()

        val firstEdition =
            variant.legacyVariant.equals("FIRST_EDITION", ignoreCase = true) ||
                normalizedStamps.any(::isFirstEditionMarker)

        return VariantTraits(
            typeKey = typeKey,
            subtypeKey = subtypeKey,
            foilKey = foilKey,
            sizeKey = sizeKey,
            firstEdition = firstEdition,
            specialStamps = normalizedStamps
                .filterNot(::isFirstEditionMarker)
                .toSet()
        )
    }

    private fun variantSearchTokens(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): List<String> {
        val target = variantTraits(variant)
        val result = mutableListOf<String>()

        if (target.firstEdition) {
            result += "1st Edition"
        }

        when (target.subtypeKey) {
            "shadowless" -> result += "Shadowless"
            "shadowless red cheek" -> result += "Shadowless Red Cheek"
        }

        if (target.sizeKey == "jumbo") {
            result += "Jumbo"
        }

        when (target.typeKey) {
            "metal" -> result += "Metal"
            "lenticular" -> result += "Lenticular"
        }

        val targetFoil = target.foilKey
        if (targetFoil != null) {
            val differsByFoil = card.variants.any { other ->
                if (other.id == variant.id) return@any false
                val traits = variantTraits(other)
                traits.typeKey == target.typeKey &&
                    traits.subtypeKey == target.subtypeKey &&
                    traits.sizeKey == target.sizeKey &&
                    traits.specialStamps == target.specialStamps &&
                    traits.foilKey != targetFoil
            }

            if (differsByFoil) {
                result += searchTokenForFoil(targetFoil)
            }
        }

        target.specialStamps
            .sorted()
            .take(1)
            .forEach {
                result += searchTokenForStamp(it)
            }

        return result
            .filter(String::isNotBlank)
            .distinct()
            .take(MAX_PROVIDER_VARIANT_TOKENS)
    }

    private fun aliasesForType(
        key: String
    ): Set<String> =
        TYPE_ALIASES[key]
            ?: genericAliases(key)

    private fun aliasesForSubtype(
        key: String
    ): Set<String> =
        SUBTYPE_ALIASES[key]
            ?: genericAliases(key)

    private fun aliasesForFoil(
        key: String
    ): Set<String> =
        FOIL_ALIASES[key]
            ?: genericAliases(key)

    private fun aliasesForStamp(
        key: String
    ): Set<String> =
        STAMP_ALIASES[key]
            ?: genericAliases(key)

    private fun genericAliases(
        key: String
    ): Set<String> =
        setOf(
            key,
            key.replace(" ", "")
        ).filter(String::isNotBlank).toSet()

    private fun searchTokenForFoil(
        key: String
    ): String =
        when (key) {
            "pokeball" -> "Pokeball"
            "greatball" -> "Great Ball"
            "ultraball" -> "Ultra Ball"
            "masterball" -> "Master Ball"
            "cracked ice" -> "Cracked Ice"
            "team rocket" -> "Team Rocket"
            else -> titleCaseVariantToken(key)
        }

    private fun searchTokenForStamp(
        key: String
    ): String =
        when (key) {
            "pre release" -> "Prerelease"
            "pokemon center" -> "Pokemon Center"
            "set logo" -> "Set Logo"
            "w promo" -> "W Promo"
            else -> titleCaseVariantToken(key)
        }

    private fun titleCaseVariantToken(
        key: String
    ): String =
        key.split(' ')
            .filter(String::isNotBlank)
            .joinToString(" ") { token ->
                token.replaceFirstChar {
                    if (it.isLowerCase()) it.titlecase(Locale.ROOT) else it.toString()
                }
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
        private const val MAX_PROVIDER_VARIANT_TOKENS = 3

        private val FIRST_EDITION_MARKERS = setOf(
            "1st edition",
            "first edition",
            "1st ed",
            "first ed",
            "1 edition",
            "1 auflage",
            "erste auflage"
        )

        private val NON_HOLO_MARKERS = setOf(
            "non holo",
            "nonholo",
            "non foil",
            "nonfoil",
            "nicht holo"
        )

        private val JUMBO_MARKERS = setOf(
            "jumbo",
            "oversized",
            "oversize",
            "oversize card",
            "giant card",
            "xxl card"
        )

        private val TYPE_ALIASES = mapOf(
            "normal" to setOf(
                "normal",
                "non holo",
                "nonholo",
                "non foil"
            ),
            "holo" to setOf(
                "holo",
                "holofoil",
                "foil",
                "holographic"
            ),
            "reverse" to setOf(
                "reverse",
                "reverse holo",
                "reverse holofoil",
                "reverse foil"
            ),
            "metal" to setOf(
                "metal",
                "metal card",
                "metallic",
                "metallkarte",
                "metall karte"
            ),
            "lenticular" to setOf(
                "lenticular",
                "lentikular",
                "wackelbild",
                "3d card",
                "3d karte"
            )
        )

        private val SUBTYPE_ALIASES = mapOf(
            "shadowless" to setOf("shadowless", "schattenlos"),
            "unlimited" to setOf("unlimited", "unbegrenzt"),
            "1999 2000 copyright" to setOf(
                "1999 2000",
                "copyright 1999 2000"
            ),
            "missing expansion symbol" to setOf(
                "missing expansion symbol",
                "no expansion symbol",
                "missing set symbol",
                "no set symbol",
                "ohne set symbol"
            ),
            "gold border" to setOf("gold border", "goldrand"),
            "missing hp" to setOf("missing hp", "no hp", "fehlende kp", "ohne kp"),
            "aoki error" to setOf("aoki error"),
            "1999 copyright" to setOf("1999 copyright", "copyright 1999"),
            "evolution box error" to setOf("evolution box error", "evolution box misprint"),
            "no holo error" to setOf("no holo error", "no holo misprint", "non holo error"),
            "d ink dot error" to setOf("d ink dot error", "ink dot error", "d ink dot"),
            "energy symbol error" to setOf("energy symbol error", "energy symbol misprint"),
            "text error" to setOf("text error", "text misprint"),
            "shifted energy cost" to setOf("shifted energy cost", "shifted energy"),
            "japanese back" to setOf("japanese back", "japanische ruckseite"),
            "no e reader" to setOf("no e reader", "without e reader", "no ereader"),
            "rarity error" to setOf("rarity error", "rarity misprint"),
            "cosmos" to setOf("cosmos"),
            "blue border" to setOf("blue border", "blauer rand"),
            "glossy" to setOf("glossy", "glanzend"),
            "shadowless red cheek" to setOf(
                "shadowless red cheek",
                "shadowless red cheeks",
                "red cheek",
                "red cheeks"
            ),
            "2019 copyright" to setOf("2019 copyright", "copyright 2019"),
            "2020 copyright" to setOf("2020 copyright", "copyright 2020"),
            "nintedo error" to setOf("nintedo error", "nintedo misprint"),
            "1995 1998 copyright" to setOf(
                "1995 1998 copyright",
                "copyright 1995 1998"
            ),
            "no rarity" to setOf(
                "no rarity",
                "no rarity symbol",
                "missing rarity symbol",
                "ohne seltenheitssymbol"
            ),
            "missing retreat cost" to setOf(
                "missing retreat cost",
                "no retreat cost"
            ),
            "phanphy error" to setOf("phanphy error", "phanpy error"),
            "peelable ditto" to setOf("peelable ditto", "peelable")
        )

        private val ALWAYS_EXPLICIT_SUBTYPES =
            SUBTYPE_ALIASES.keys - setOf(
                "unlimited"
            )

        private val FOIL_ALIASES = mapOf(
            "pokeball" to setOf("pokeball", "poke ball"),
            "greatball" to setOf("greatball", "great ball"),
            "ultraball" to setOf("ultraball", "ultra ball"),
            "masterball" to setOf("masterball", "master ball"),
            "gold" to setOf("gold foil", "gold holo", "gold"),
            "cosmos" to setOf("cosmos", "cosmos holo"),
            "galaxy" to setOf("galaxy", "galaxy holo"),
            "starlight" to setOf("starlight", "starlight holo"),
            "energy" to setOf("energy holo", "energy foil"),
            "cracked ice" to setOf("cracked ice", "cracked ice holo"),
            "mirror" to setOf("mirror", "mirror holo"),
            "league" to setOf("league", "league holo"),
            "player reward" to setOf("player reward", "player rewards"),
            "professor program" to setOf("professor program"),
            "tinsel" to setOf("tinsel", "tinsel holo"),
            "loveball" to setOf("loveball", "love ball"),
            "friendball" to setOf("friendball", "friend ball"),
            "quickball" to setOf("quickball", "quick ball"),
            "team rocket" to setOf("team rocket", "rocket foil"),
            "duskball" to setOf("duskball", "dusk ball"),
            "rainbow" to setOf("rainbow foil", "rainbow holo", "rainbow"),
            "glitter" to setOf("glitter", "glitter holo")
        )

        private val STAMP_ALIASES = mapOf(
            "w promo" to setOf("w promo", "w stamp", "wizards promo"),
            "pre release" to setOf("pre release", "prerelease"),
            "pokemon center" to setOf("pokemon center", "pokecenter"),
            "set logo" to setOf("set logo", "set stamp", "set stamped"),
            "staff" to setOf("staff", "staff stamp"),
            "winner" to setOf("winner", "winner stamp"),
            "snowflake" to setOf("snowflake", "snowflake stamp"),
            "trick or trade" to setOf("trick or trade", "halloween stamp"),
            "gamestop" to setOf("gamestop", "game stop"),
            "eb games" to setOf("eb games", "ebgames"),
            "professor program" to setOf("professor program"),
            "player rewards program" to setOf("player rewards", "player reward"),
            "pokemon day" to setOf("pokemon day", "pokeday"),
            "pokemon together" to setOf("pokemon together", "together stamp"),
            "illustration contest 2022" to setOf("illustration contest 2022"),
            "illustration contest 2024" to setOf("illustration contest 2024"),
            "25th celebration" to setOf("25th celebration", "25th anniversary"),
            "30th pokeday" to setOf("30th pokeday", "30th pokemon day")
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
