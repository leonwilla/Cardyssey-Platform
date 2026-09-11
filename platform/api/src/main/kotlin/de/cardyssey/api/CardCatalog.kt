package de.cardyssey.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration
import java.util.concurrent.ConcurrentHashMap

@Serializable
data class CatalogCardSearchResult(
    val id: String,
    val localId: String,
    val name: String,
    val setId: String,
    val setName: String?,
    val imageBase: String?
)

@Serializable
data class CatalogVariant(
    val id: String,
    val type: String,
    val subtype: String? = null,
    val foil: String? = null,
    val size: String? = null,
    val stamps: List<String> = emptyList(),
    val legacyVariant: String,
    val tcgDexEur: Double? = null
)

@Serializable
data class CatalogCardDetails(
    val id: String,
    val localId: String,
    val name: String,

    val languageCode: String,

    val imageBase: String? = null,
    val imageLanguage: String? = null,

    val setId: String,
    val setName: String,
    val officialCount: Int = 0,

    val rarity: String? = null,

    val variants: List<CatalogVariant>
)


@Serializable
data class CatalogSetSummary(
    val id: String,
    val name: String,
    val logo: String? = null,
    val symbol: String? = null,
    val officialCount: Int = 0,
    val totalCount: Int = 0
)

@Serializable
data class CatalogSetCard(
    val id: String,
    val localId: String,
    val name: String,
    val imageBase: String? = null
)

@Serializable
data class CatalogSetDetails(
    val id: String,
    val name: String,
    val logo: String? = null,
    val symbol: String? = null,
    val officialCount: Int = 0,
    val totalCount: Int = 0,
    val cards: List<CatalogSetCard>
)

private data class BriefCard(
    val id: String,
    val localId: String,
    val name: String,
    val imageBase: String?
)

private data class CacheEntry<T>(
    val value: T,
    val expiresAtMs: Long
)

class CardCatalogService(
    private val persistentCache: CatalogCacheRepository
) {

    companion object {
        private const val BASE =
            "https://api.tcgdex.net/v2"

        private const val CACHE_MS =
            6L * 60L * 60L * 1000L

        private val ALLOWED_LANGUAGES =
            setOf(
                "de",
                "en",
                "fr",
                "it",
                "es",
                "pt",
                "ja",
                "ko",
                "zh-tw",
                "zh-cn"
            )
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

    private val cardsCache =
        ConcurrentHashMap<
            String,
            CacheEntry<List<BriefCard>>
        >()

    private val setsCache =
        ConcurrentHashMap<
            String,
            CacheEntry<Map<String, String>>
        >()

    /*
     * Set-Katalog und Setdetails werden zentral auf dem
     * Cardyssey-Server gecacht.
     *
     * Web und Android müssen dadurch nicht bei jedem Öffnen
     * erneut auf TCGdex warten.
     */
    private val setSummaryCache =
        ConcurrentHashMap<
            String,
            CacheEntry<List<CatalogSetSummary>>
        >()

    private val setDetailsCache =
        ConcurrentHashMap<
            String,
            CacheEntry<CatalogSetDetails>
        >()

    fun validLanguage(
        language: String
    ): Boolean =
        language in ALLOWED_LANGUAGES

    suspend fun search(
        query: String,
        number: String?,
        language: String,
        limit: Int
    ): List<CatalogCardSearchResult> {

        val safeLimit =
            limit.coerceIn(1, 50)

        val normalizedQuery =
            query
                .trim()
                .lowercase()

        val normalizedNumber =
            number
                ?.let(::normalizeNumber)
                ?.takeIf {
                    it.isNotBlank()
                }

        if (
            normalizedQuery.isBlank() &&
            normalizedNumber == null
        ) {
            return emptyList()
        }

        var cards =
            loadCards(language)

        /*
         * Wichtig für Suchen wie 025/165:
         *
         * Wenn eine Kartennummer angegeben wurde,
         * nehmen wir nur Karten mit exakt derselben
         * normalisierten localId.
         */
        if (normalizedNumber != null) {

            val exactNumber =
                cards.filter {
                    normalizeNumber(
                        it.localId
                    ) ==
                        normalizedNumber
                }

            cards =
                exactNumber
        }

        if (cards.isEmpty()) {
            return emptyList()
        }

        val setNames =
            loadSets(language)

        return cards
            .asSequence()
            .mapNotNull { card ->

                val nameScore =
                    scoreName(
                        card.name,
                        normalizedQuery
                    )

                if (
                    normalizedQuery.isNotBlank() &&
                    nameScore >= 100
                ) {
                    return@mapNotNull null
                }

                val setId =
                    card.id
                        .substringBeforeLast(
                            "-",
                            ""
                        )

                card to Pair(
                    nameScore,
                    setId
                )
            }
            .sortedWith(
                compareBy<
                    Pair<
                        BriefCard,
                        Pair<Int, String>
                    >
                > {
                    it.second.first
                }.thenBy {
                    it.first.name.length
                }
            )
            .take(safeLimit)
            .map {
                (card, scored) ->

                val setId =
                    scored.second

                CatalogCardSearchResult(
                    id =
                        card.id,

                    localId =
                        card.localId,

                    name =
                        card.name,

                    setId =
                        setId,

                    setName =
                        setNames[setId],

                    imageBase =
                        card.imageBase
                )
            }
            .toList()
    }

    suspend fun details(
        cardId: String,
        language: String
    ): CatalogCardDetails? {

        val requested =
            loadCardObject(
                language,
                cardId
            )

        val english =
            if (
                language != "en" &&
                (
                    requested == null ||
                    requested.string(
                        "image"
                    ) == null
                )
            ) {
                loadCardObject(
                    "en",
                    cardId
                )
            } else {
                null
            }

        val source =
            requested
                ?: english
                ?: return null

        val sourceLanguage =
            if (requested != null) {
                language
            } else {
                "en"
            }

        val imageBase =
            source.string(
                "image"
            )
                ?: english?.string(
                    "image"
                )

        val imageLanguage =
            when {
                source.string(
                    "image"
                ) != null ->
                    sourceLanguage

                english?.string(
                    "image"
                ) != null ->
                    "en"

                else ->
                    null
            }

        val set =
            source["set"]
                ?.asObject()

        val setId =
            set?.string(
                "id"
            )
                ?: cardId
                    .substringBeforeLast(
                        "-",
                        "unknown"
                    )

        val setName =
            set?.string(
                "name"
            )
                ?: "Unbekannt"

        val officialCount =
            set
                ?.get("cardCount")
                ?.asObject()
                ?.int("official")
                ?: 0

        return CatalogCardDetails(
            id =
                source.string("id")
                    ?: cardId,

            localId =
                source.string(
                    "localId"
                )
                    ?: "",

            name =
                source.string(
                    "name"
                )
                    ?: cardId,

            languageCode =
                sourceLanguage,

            imageBase =
                imageBase,

            imageLanguage =
                imageLanguage,

            setId =
                setId,

            setName =
                setName,

            officialCount =
                officialCount,

            rarity =
                source.string(
                    "rarity"
                ),

            variants =
                parseVariants(
                    card = source,
                    language = sourceLanguage
                )
        )
    }


    suspend fun sets(
        language: String
    ): List<CatalogSetSummary> {

        val now =
            System.currentTimeMillis()

        setSummaryCache[
            language
        ]
            ?.takeIf {
                it.expiresAtMs > now
            }
            ?.let {
                return it.value
            }

        fun parse(
            rawSets: JsonArray
        ): List<CatalogSetSummary> =
            rawSets.mapNotNull { element ->

                val raw =
                    element.asObject()
                        ?: return@mapNotNull null

                val id =
                    raw.string("id")
                        ?: return@mapNotNull null

                val name =
                    raw.string("name")
                        ?: return@mapNotNull null

                val count =
                    raw["cardCount"]
                        ?.asObject()

                CatalogSetSummary(
                    id = id,
                    name = name,
                    logo =
                        raw.string("logo"),
                    symbol =
                        raw.string("symbol"),
                    officialCount =
                        count?.int(
                            "official"
                        ) ?: 0,
                    totalCount =
                        count?.int(
                            "total"
                        ) ?: 0
                )
            }

        val local =
            runCatching {
                parse(
                    fetchArray(
                        "$BASE/$language/sets"
                    )
                )
            }
                .getOrDefault(
                    emptyList()
                )

        /*
         * Bei nicht-englischen Katalogen liefert
         * TCGdex teilweise Name/Kartenanzahl, aber
         * kein Logo oder Symbol.
         *
         * Englisch dient nur als Asset-/Count-Fallback.
         * Der lokale Name bleibt bevorzugt.
         */
        val english =
            if (
                language != "en" &&
                (
                    local.isEmpty() ||
                    local.any {
                        it.logo.isNullOrBlank() ||
                            it.symbol.isNullOrBlank() ||
                            it.officialCount <= 0
                    }
                )
            ) {
                runCatching {
                    parse(
                        fetchArray(
                            "$BASE/en/sets"
                        )
                    )
                }
                    .getOrDefault(
                        emptyList()
                    )
            } else {
                emptyList()
            }

        val englishById =
            english.associateBy {
                it.id
            }

        val base =
            if (
                local.isEmpty() &&
                language != "en"
            ) {
                english
            } else {
                local
            }

        val result =
            base.map { set ->

                val fallback =
                    englishById[
                        set.id
                    ]

                set.copy(
                    logo =
                        set.logo
                            ?.takeIf(
                                String::isNotBlank
                            )
                            ?: fallback
                                ?.logo,
                    symbol =
                        set.symbol
                            ?.takeIf(
                                String::isNotBlank
                            )
                            ?: fallback
                                ?.symbol,
                    officialCount =
                        set.officialCount
                            .takeIf {
                                it > 0
                            }
                            ?: fallback
                                ?.officialCount
                            ?: 0,
                    totalCount =
                        set.totalCount
                            .takeIf {
                                it > 0
                            }
                            ?: fallback
                                ?.totalCount
                            ?: 0
                )
            }

        if (result.isNotEmpty()) {
            setSummaryCache[
                language
            ] =
                CacheEntry(
                    result,
                    now + CACHE_MS
                )
        }

        return result
    }


    suspend fun setDetails(
        setId: String,
        language: String
    ): CatalogSetDetails? {

        val now =
            System.currentTimeMillis()

        val cacheKey =
            "$language:$setId"

        setDetailsCache[
            cacheKey
        ]
            ?.takeIf {
                it.expiresAtMs > now
            }
            ?.let {
                return it.value
            }

        val requested =
            runCatching {
                fetchObject(
                    "$BASE/$language/sets/$setId"
                )
            }
                .onFailure {
                    println(
                        "TCGdex set fetch failed: set=$setId language=$language error=${it.message}"
                    )
                }
                .getOrNull()

        /*
         * Englische Setdetails liefern bei vielen
         * lokalisierten Sets vollständigeres Artwork.
         *
         * Nur Bilder/fehlende Metadaten werden davon
         * übernommen. Lokalisierter Name/Text bleibt.
         */
        val english =
            if (
                language != "en"
            ) {
                runCatching {
                    fetchObject(
                        "$BASE/en/sets/$setId"
                    )
                }
                    .getOrNull()
            } else {
                null
            }

        val source =
            requested
                ?: english
                ?: return null

        fun cardsFrom(
            raw: JsonObject?
        ): List<CatalogSetCard> =
            raw
                ?.get("cards")
                ?.asArray()
                .orEmpty()
                .mapNotNull { element ->

                    val card =
                        element.asObject()
                            ?: return@mapNotNull null

                    CatalogSetCard(
                        id =
                            card.string("id")
                                ?: return@mapNotNull null,
                        localId =
                            card.string(
                                "localId"
                            )
                                ?: "",
                        name =
                            card.string("name")
                                ?: return@mapNotNull null,
                        imageBase =
                            card.string(
                                "image"
                            )
                    )
                }

        val sourceCards =
            cardsFrom(
                source
            )

        val englishCards =
            cardsFrom(
                english
            )

        val englishById =
            englishCards.associateBy {
                it.id
            }

        val englishByNumber =
            englishCards
                .filter {
                    it.localId.isNotBlank()
                }
                .associateBy {
                    it.localId
                }

        val cards =
            sourceCards.map { card ->

                if (
                    !card.imageBase
                        .isNullOrBlank()
                ) {
                    card
                } else {

                    val fallback =
                        englishById[
                            card.id
                        ]
                            ?: englishByNumber[
                                card.localId
                            ]

                    card.copy(
                        imageBase =
                            fallback
                                ?.imageBase
                    )
                }
            }

        val sourceCount =
            source["cardCount"]
                ?.asObject()

        val englishCount =
            english
                ?.get("cardCount")
                ?.asObject()

        val result =
            CatalogSetDetails(
                id =
                    source.string("id")
                        ?: setId,
                name =
                    source.string("name")
                        ?: english
                            ?.string("name")
                        ?: setId,
                logo =
                    source.string("logo")
                        ?.takeIf(
                            String::isNotBlank
                        )
                        ?: english
                            ?.string("logo"),
                symbol =
                    source.string("symbol")
                        ?.takeIf(
                            String::isNotBlank
                        )
                        ?: english
                            ?.string("symbol"),
                officialCount =
                    sourceCount
                        ?.int("official")
                        ?.takeIf {
                            it > 0
                        }
                        ?: englishCount
                            ?.int("official")
                        ?: 0,
                totalCount =
                    sourceCount
                        ?.int("total")
                        ?.takeIf {
                            it > 0
                        }
                        ?: englishCount
                            ?.int("total")
                        ?: cards.size,
                cards =
                    cards
            )

        setDetailsCache[
            cacheKey
        ] =
            CacheEntry(
                result,
                now + CACHE_MS
            )

        return result
    }


    private suspend fun loadCards(
        language: String
    ): List<BriefCard> {

        val now =
            System.currentTimeMillis()

        cardsCache[
            language
        ]
            ?.takeIf {
                it.expiresAtMs > now
            }
            ?.let {
                return it.value
            }

        val loaded =
            runCatching {
                fetchArray(
                    "$BASE/$language/cards"
                )
            }
                .getOrNull()
                ?.mapNotNull {
                    element ->

                    val raw =
                        element.asObject()
                            ?: return@mapNotNull null

                    val id =
                        raw.string("id")
                            ?: return@mapNotNull null

                    val name =
                        raw.string("name")
                            ?: return@mapNotNull null

                    BriefCard(
                        id =
                            id,

                        localId =
                            raw.string(
                                "localId"
                            )
                                ?: "",

                        name =
                            name,

                        imageBase =
                            raw.string(
                                "image"
                            )
                    )
                }
                .orEmpty()

        val result =
            if (
                loaded.isEmpty() &&
                language != "en"
            ) {
                loadCards("en")
            } else {
                loaded
            }

        cardsCache[
            language
        ] =
            CacheEntry(
                result,
                now + CACHE_MS
            )

        return result
    }

    private suspend fun loadSets(
        language: String
    ): Map<String, String> {

        val now =
            System.currentTimeMillis()

        setsCache[
            language
        ]
            ?.takeIf {
                it.expiresAtMs > now
            }
            ?.let {
                return it.value
            }

        val loaded =
            runCatching {
                fetchArray(
                    "$BASE/$language/sets"
                )
            }
                .getOrNull()
                ?.mapNotNull {
                    element ->

                    val raw =
                        element.asObject()
                            ?: return@mapNotNull null

                    val id =
                        raw.string("id")
                            ?: return@mapNotNull null

                    val name =
                        raw.string("name")
                            ?: return@mapNotNull null

                    id to name
                }
                ?.toMap()
                .orEmpty()

        val result =
            if (
                loaded.isEmpty() &&
                language != "en"
            ) {
                loadSets("en")
            } else {
                loaded
            }

        setsCache[
            language
        ] =
            CacheEntry(
                result,
                now + CACHE_MS
            )

        return result
    }

    private suspend fun loadCardObject(
        language: String,
        cardId: String
    ): JsonObject? =
        runCatching {
            fetchObject(
                "$BASE/$language/cards/$cardId"
            )
        }.getOrNull()

    private fun parseVariants(
        card: JsonObject,
        language: String
    ): List<CatalogVariant> {

        val detailed =
            card["variants_detailed"]
                ?.asArray()
                .orEmpty()
                .mapNotNull {
                    element ->

                    val raw =
                        element.asObject()
                            ?: return@mapNotNull null

                    /*
                     * TCGdex kann einzelne physische Varianten auf bestimmte
                     * Sprachen begrenzen. Varianten, die es in der ausgewählten
                     * Sprache gar nicht gibt, dürfen weder in der UI noch beim
                     * Pricing/eBay-Matching angeboten werden.
                     */
                    val variantLanguages =
                        raw["languages"]
                            ?.asArray()
                            .orEmpty()
                            .mapNotNull { value ->
                                value.asPrimitive()
                                    ?.content
                                    ?.trim()
                                    ?.lowercase()
                                    ?.takeIf(String::isNotBlank)
                            }

                    if (
                        variantLanguages.isNotEmpty() &&
                        language.lowercase() !in variantLanguages
                    ) {
                        return@mapNotNull null
                    }

                    val type =
                        raw.string("type")
                            ?.trim()
                            ?.takeIf {
                                it.isNotBlank()
                            }
                            ?: return@mapNotNull null

                    val subtype =
                        raw.string(
                            "subtype"
                        )

                    val foil =
                        raw.string(
                            "foil"
                        )

                    val size =
                        raw.string(
                            "size"
                        )

                    val stamps =
                        raw["stamp"]
                            ?.asArray()
                            .orEmpty()
                            .mapNotNull {
                                it.asPrimitive()
                                    ?.content
                                    ?.trim()
                                    ?.takeIf(
                                        String::isNotBlank
                                    )
                            }

                    val id =
                        raw.string(
                            "variantId"
                        )
                            ?: listOf(
                                type,
                                subtype.orEmpty(),
                                foil.orEmpty(),
                                stamps.joinToString(
                                    "+"
                                ),
                                size.orEmpty()
                            )
                                .joinToString(
                                    ":"
                                )

                    CatalogVariant(
                        id =
                            id,

                        type =
                            type,

                        subtype =
                            subtype,

                        foil =
                            foil,

                        size =
                            size,

                        stamps =
                            stamps,

                        /*
                         * Nur Kompatibilität für ältere Clients/Backups.
                         * Die exakte Identität bleibt immer id + type/subtype/
                         * foil/stamps/size. Metal/Lenticular dürfen deshalb
                         * beim Matching nie über diesen Legacy-Wert beurteilt
                         * werden.
                         */
                        legacyVariant =
                            legacyVariant(
                                type
                            ),

                        tcgDexEur =
                            exactVariantPrice(
                                raw
                            )
                    )
                }
                .distinctBy {
                    it.id
                }

        if (detailed.isNotEmpty()) {
            return detailed
        }

        val legacy =
            card["variants"]
                ?.asObject()

        if (legacy == null) {
            return listOf(
                legacyVariantDto(
                    "NORMAL"
                )
            )
        }

        val baseVariants =
            mutableListOf<CatalogVariant>()

        if (
            legacy.boolean(
                "normal"
            ) == true
        ) {
            baseVariants +=
                legacyVariantDto(
                    "NORMAL"
                )
        }

        if (
            legacy.boolean(
                "reverse"
            ) == true
        ) {
            baseVariants +=
                legacyVariantDto(
                    "REVERSE"
                )
        }

        if (
            legacy.boolean(
                "holo"
            ) == true
        ) {
            baseVariants +=
                legacyVariantDto(
                    "HOLO"
                )
        }

        if (baseVariants.isEmpty()) {
            baseVariants +=
                legacyVariantDto(
                    "NORMAL"
                )
        }

        val result =
            baseVariants.toMutableList()

        /*
         * Die alten TCGdex-Flags beschreiben zusätzliche physische
         * Ausführungen. Wenn genau ein Basistyp existiert, können wir diese
         * eindeutig auf diesen Typ abbilden. Bei mehreren Basistypen wird
         * bewusst nichts erfunden; lieber keine unsichere Variante.
         */
        val unambiguousBase =
            baseVariants.singleOrNull()

        if (
            legacy.boolean(
                "firstEdition"
            ) == true
        ) {
            result +=
                unambiguousBase
                    ?.copy(
                        id = "${unambiguousBase.id}:first-edition",
                        stamps =
                            unambiguousBase.stamps +
                                "1st-edition"
                    )
                    ?: legacyVariantDto(
                        "FIRST_EDITION"
                    )
        }

        if (
            legacy.boolean(
                "jumbo"
            ) == true &&
            unambiguousBase != null
        ) {
            result +=
                unambiguousBase.copy(
                    id = "${unambiguousBase.id}:jumbo",
                    size = "jumbo"
                )
        }

        if (
            legacy.boolean(
                "preRelease"
            ) == true &&
            unambiguousBase != null
        ) {
            result +=
                unambiguousBase.copy(
                    id = "${unambiguousBase.id}:pre-release",
                    stamps =
                        unambiguousBase.stamps +
                            "pre-release"
                )
        }

        if (
            legacy.boolean(
                "wPromo"
            ) == true &&
            unambiguousBase != null
        ) {
            result +=
                unambiguousBase.copy(
                    id = "${unambiguousBase.id}:w-promo",
                    stamps =
                        unambiguousBase.stamps +
                            "w-promo"
                )
        }

        return result.distinctBy {
            it.id
        }
    }

    private fun legacyVariantDto(
        legacy: String
    ): CatalogVariant {

        val type =
            when (legacy) {
                "REVERSE" ->
                    "Reverse"

                "HOLO" ->
                    "Holo"

                "FIRST_EDITION" ->
                    "First Edition"

                else ->
                    "Normal"
            }

        return CatalogVariant(
            id =
                "legacy:" +
                    legacy.lowercase(),

            type =
                type,

            legacyVariant =
                legacy
        )
    }

    private fun exactVariantPrice(
        variant: JsonObject
    ): Double? {

        val cardmarket =
            variant["pricing"]
                ?.asObject()
                ?.get("cardmarket")
                ?.asObject()
                ?: return null

        return listOf(
            "trend",
            "avg7",
            "avg30",
            "avg",
            "low"
        )
            .firstNotNullOfOrNull {
                key ->

                cardmarket
                    .double(key)
                    ?.takeIf {
                        it.isFinite() &&
                            it > 0.0
                    }
            }
    }

    private fun legacyVariant(
        type: String
    ): String =
        when (
            type
                .lowercase()
                .replace("-", "")
                .replace("_", "")
                .replace(" ", "")
        ) {
            "reverse" ->
                "REVERSE"

            "holo" ->
                "HOLO"

            "firstedition",
            "1stedition" ->
                "FIRST_EDITION"

            /*
             * CardVariant in älteren Clients kennt Metal/Lenticular noch
             * nicht. Diese beiden Typen bleiben ausschließlich für die
             * Kompatibilität NORMAL; die exakten Felder oben bleiben erhalten.
             */
            else ->
                "NORMAL"
        }

    private fun scoreName(
        name: String,
        query: String
    ): Int {

        if (query.isBlank()) {
            return 0
        }

        val value =
            name.lowercase()

        return when {
            value == query ->
                0

            value.startsWith(
                query
            ) ->
                10

            value.contains(
                query
            ) ->
                20

            query
                .split(
                    Regex("\\s+")
                )
                .filter(
                    String::isNotBlank
                )
                .all(
                    value::contains
                ) ->
                30

            else ->
                100
        }
    }

    private fun normalizeNumber(
        value: String
    ): String {

        val number =
            value
                .trim()
                .substringBefore(
                    "/"
                )
                .trim()

        if (number.isBlank()) {
            return ""
        }

        return if (
            number.all(
                Char::isDigit
            )
        ) {
            number
                .trimStart('0')
                .ifBlank {
                    "0"
                }
        } else {
            number.lowercase()
        }
    }

    private suspend fun fetchArray(
        url: String
    ): JsonArray =
        fetchJson(url)
            .jsonArray

    private suspend fun fetchObject(
        url: String
    ): JsonObject =
        fetchJson(url)
            .jsonObject

    private suspend fun fetchJson(
        url: String
    ): JsonElement =
        withContext(
            Dispatchers.IO
        ) {
            try {
                val request =
                    HttpRequest
                        .newBuilder()
                        .uri(
                            URI.create(url)
                        )
                        .timeout(
                            Duration.ofSeconds(20)
                        )
                        .header(
                            "Accept",
                            "application/json"
                        )
                        .header(
                            "User-Agent",
                            "Cardyssey/0.1"
                        )
                        .GET()
                        .build()

                val response =
                    http.send(
                        request,
                        HttpResponse.BodyHandlers
                            .ofString()
                    )

                check(
                    response.statusCode() in 200..299
                ) {
                    "TCGdex returned HTTP ${response.statusCode()}"
                }

                val body =
                    response.body()

                persistentCache.write(
                    url,
                    body
                )

                json.parseToJsonElement(
                    body
                )

            } catch (cause: Exception) {

                val cached =
                    persistentCache.read(
                        url
                    )

                if (cached != null) {
                    println(
                        "TCGdex unavailable, using cache: $url"
                    )

                    json.parseToJsonElement(
                        cached
                    )
                } else {
                    throw cause
                }
            }
        }
}

private fun JsonElement.asObject():
    JsonObject? =
    this as? JsonObject

private fun JsonElement.asArray():
    JsonArray? =
    this as? JsonArray

private fun JsonElement.asPrimitive():
    JsonPrimitive? =
    this as? JsonPrimitive

private fun JsonObject.string(
    key: String
): String? =
    (this[key] as? JsonPrimitive)
        ?.content
        ?.takeIf {
            it.isNotBlank() &&
                it != "null"
        }

private fun JsonObject.double(
    key: String
): Double? =
    (this[key] as? JsonPrimitive)
        ?.doubleOrNull

private fun JsonObject.int(
    key: String
): Int? =
    (this[key] as? JsonPrimitive)
        ?.content
        ?.toIntOrNull()

private fun JsonObject.boolean(
    key: String
): Boolean? =
    (this[key] as? JsonPrimitive)
        ?.booleanOrNull
