package de.cardyssey.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
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

/*
 * TCGdex hat die 30th Classic Collection bereits katalogisiert, liefert
 * aktuell aber noch keine Bildfelder. Bis die Quelle nachzieht, verwenden
 * wir die veröffentlichten Reprint-Abbildungen. Sobald TCGdex ein Bild
 * liefert, gewinnt dieses automatisch vor dem Fallback.
 */
private val CLASSIC_COLLECTION_IMAGE_FALLBACKS =
    mapOf(
        "30th-c-001" to "https://images.ctfassets.net/0hawnqdvsfxb/4uLdwLq8x7naSZfKlZPpqA/dee4ec4267c9644327c1ad1f8a947a15/02-charizard-base-set_rc.png",
        "30th-c-002" to "https://images.ctfassets.net/0hawnqdvsfxb/3VdBxMmef0IipVgvNAFwcS/db634329df5b0038a70c7104f78d53df/08-delcatty-ex-ruby-sapphire_rc.png",
        "30th-c-003" to "https://images.ctfassets.net/0hawnqdvsfxb/1vyQjQA51yGqr4pDTc6Lqf/b7ee7d5a8809f93f6e6b17ff18c6a20d/11-metagross-ex-delta-species_rc.png",
        "30th-c-004" to "https://images.ctfassets.net/0hawnqdvsfxb/3eq946ECMyl2SN43sA3FrP/cc3a2991743394af196ab5a26bc3b7b2/19-genesect-ex-plasma-blast_rc.png",
        "30th-c-005" to "https://images.ctfassets.net/0hawnqdvsfxb/4D20PvDNVNYWgMr4rVlTGJ/f7b679447fe90d8990adca83078da86a/03-misty-gym-heroes_rc.png",
        "30th-c-006" to "https://images.ctfassets.net/0hawnqdvsfxb/1fXBGs65bxydv5zO8SQs1Z/293f4995e421cf438125527645e43e60/09-dark-tyranitar-ex-team-rocket-returns_rc.png",
        "30th-c-007" to "https://images.ctfassets.net/0hawnqdvsfxb/ECILlMWXDqwMjyfqx6yUe/96d8b4de0ab4bc66ce3e36078f3a2838/05-sneasel-neo-genesis_rc.png",
        "30th-c-008" to "https://images.ctfassets.net/0hawnqdvsfxb/20sxHnek2vNXPQX7u9NimG/902e7df257e361bea05a244b6ce1ede6/24-pikachu-zekrom-gx-team-up_rc.png",
        "30th-c-009" to "https://images.ctfassets.net/0hawnqdvsfxb/6Xr3wT9oR9mbCkFlPO9KRh/df2ff203a58f12bba2324d9448165d65/21-greninja-break-breakpoint_rc.png",
        "30th-c-010" to "https://images.ctfassets.net/0hawnqdvsfxb/6Kw0RTJTWpaqIBZrT3szWL/e8d95dd3ab514daf81002120ad4bf4cc/13-uxie-legends-awakened_rc.png",
        "30th-c-011" to "https://images.ctfassets.net/0hawnqdvsfxb/4fJSqhOhCt3coWSjCK5YFS/d7ac4e2d51304966586604c1a14aa230/14-crobat-g-platinum_rc.png",
        "30th-c-012" to "https://images.ctfassets.net/0hawnqdvsfxb/44mFpNvtHu2vxPU4IUn0kU/7af89dcd2a7aca7f514123b9cd1f92d6/26-raikou-vivid-voltage_rc.png",
        "30th-c-013" to "https://images.ctfassets.net/0hawnqdvsfxb/6PaO4X7A7OBo6MKGKelYcz/42e547cef01814a8ffa5462d71754db7/23-buzzwole-gx-crimson-invasion_rc.png",
        "30th-c-014" to "https://images.ctfassets.net/0hawnqdvsfxb/698jDlMm2wGE2U27UN3JRb/18d8e3529165e92b325da03f49a4048a/01-pikachu-base-set_rc.png",
        "30th-c-015" to "https://images.ctfassets.net/0hawnqdvsfxb/6oA5XBqPx6TdEOSJdm8lU0/897646c71d35bd452c33a89ddc16741a/04-erikas-jigglypuff-gym-challenge_rc.png",
        "30th-c-016" to "https://images.ctfassets.net/0hawnqdvsfxb/5bLOEGhjUaWMeltym4PFdf/b34fc9e640074ce808c34142cab35c91/18-rayquaza-ex-dragons-exalted_rc.png",
        "30th-c-017" to "https://images.ctfassets.net/0hawnqdvsfxb/aNwIpDivxhXCEleKcMz0c/f21e8be54189509ad95db2d7a262857e/22-solgaleo-gx-sun-moon_rc.png",
        "30th-c-018" to "https://images.ctfassets.net/0hawnqdvsfxb/62GC59fcrIL4Wa5yZSM20U/6aa0d27ed16a497def41e396b7713e62/15-gengar-prime-hgss-triumphant_rc.png",
        "30th-c-019" to "https://images.ctfassets.net/0hawnqdvsfxb/5UQBHt5UiOdZT2K9iUT4sU/054b5c179d3d5ae0bfe4eddb2d3c638b/16-darkrai-cresselia-legend-connected_rc.png",
        "30th-c-020" to "https://images.ctfassets.net/0hawnqdvsfxb/5UQBHt5UiOdZT2K9iUT4sU/054b5c179d3d5ae0bfe4eddb2d3c638b/16-darkrai-cresselia-legend-connected_rc.png",
        "30th-c-021" to "https://images.ctfassets.net/0hawnqdvsfxb/2mQq5sfqTvFQDYSDYc5Dmy/2571082f46839b3ba16fa3aa08f219ed/17-n-noble-victories_rc.png",
        "30th-c-022" to "https://images.ctfassets.net/0hawnqdvsfxb/1UVnLlAEbGzEaYbjZb2faJ/461721da6078f07fecfb0c663c8ce5d1/12-palkia-lvx-great-encounters_rc.png",
        "30th-c-023" to "https://images.ctfassets.net/0hawnqdvsfxb/1OsF109it2ou8HaexpFJ3V/ef3f33d454ab8c02c40bf9b6460c074d/20-m-gardevoir-ex-primal-clash_rc.png",
        "30th-c-024" to "https://images.ctfassets.net/0hawnqdvsfxb/68uGXmVSeSZ76BuO6ayY4n/f3a765cd2ba48d1fe50613c309abf8f2/06-shining-celebi-neo-destiny_rc.png",
        "30th-c-025" to "https://images.ctfassets.net/0hawnqdvsfxb/SPcQBEdhdZS7MWbfEqCBz/fa80e2dba0e809ef4678c55e68538759/10-scizor-ex-ex-unseen-forces_rc.png",
        "30th-c-026" to "https://images.ctfassets.net/0hawnqdvsfxb/1EEqiLOcyR22TadQcVowQZ/efa83ec19f2a8f71116e255d8fa46cc0/27-mew-vmax-fusion-strike_rc.png",
        "30th-c-027" to "https://images.ctfassets.net/0hawnqdvsfxb/5K8vMosl2VmW1mFY8IZepe/be59c9c826277dbc376c281df77c4e53/28-arceus-vstar-brilliant-stars_rc.png",
        "30th-c-028" to "https://images.ctfassets.net/0hawnqdvsfxb/46zgQSPxiTgByfWxeP4PXa/5a80a2e1832e78a12cd029d050dc99e3/25-zacian-v-sword-shield_rc.png",
        "30th-c-029" to "https://images.ctfassets.net/0hawnqdvsfxb/6K89w3NX2qJgfuVZ02YMBp/2d164320873dfd19f90a8045b4c0f3c2/07-crystal-lugia-aquapolis_rc.png",
        "30th-c-030" to "https://images.ctfassets.net/0hawnqdvsfxb/0xFDSWaaVQ4PEnvs3YOas/877c8ca708e99fe4463744626e6fdfb8/29-magikarp-paldea-evolved_rc.png"
    )

private const val NIDORINA_PROMO_IMAGE =
    "https://images.pokemoncard.io/images/mep/mep-101_hiresopt.jpg"

private fun catalogImageFallback(
    cardId: String
): String? =
    CLASSIC_COLLECTION_IMAGE_FALLBACKS[cardId]
        ?: if (cardId == "mep-101") {
            NIDORINA_PROMO_IMAGE
        } else {
            null
        }

private fun nidorinaPromoDetails(
    language: String
): CatalogCardDetails? =
    if (language == "de" || language == "en") {
        CatalogCardDetails(
            id = "mep-101",
            localId = "101",
            name = "Nidorina",
            languageCode = language,
            imageBase = NIDORINA_PROMO_IMAGE,
            imageLanguage = "en",
            setId = "mep",
            setName = "MEP Black Star Promos",
            officialCount = 0,
            rarity = "Promo",
            variants =
                listOf(
                    CatalogVariant(
                        id = "legacy:holo",
                        type = "Holo",
                        legacyVariant = "HOLO"
                    )
                )
        )
    } else {
        null
    }

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

    /*
     * Lädt die kompakten Karten- und Setkataloge aller unterstützten
     * Sprachen beim Serverstart vor. fetchJson schreibt jede erfolgreiche
     * Antwort zusätzlich in PostgreSQL. Android und Web arbeiten danach
     * gegen Tiny; TCGdex bleibt nur die zentrale Aktualisierungsquelle.
     */
    suspend fun preload() = coroutineScope {
        ALLOWED_LANGUAGES
            .map { language ->
                async {
                    runCatching {
                        loadCards(language)
                        sets(language)
                    }.onFailure { error ->
                        println(
                            "Catalog preload failed: language=$language error=${error.message}"
                        )
                    }
                }
            }
            .awaitAll()
    }

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
                ?: return nidorinaPromoDetails(
                    language = language
                )?.takeIf {
                    it.id == cardId
                }

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
                ?: catalogImageFallback(
                    cardId
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
                                ?: catalogImageFallback(
                                    card.id
                                )
                    )
                }
            }
                .let { currentCards ->
                    if (
                        language == "de" &&
                        setId == "mep" &&
                        currentCards.none {
                            it.id == "mep-101"
                        }
                    ) {
                        currentCards +
                            CatalogSetCard(
                                id = "mep-101",
                                localId = "101",
                                name = "Nidorina",
                                imageBase =
                                    NIDORINA_PROMO_IMAGE
                            )
                    } else {
                        currentCards
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

        val completeResult =
            if (
                language == "de" &&
                result.none {
                    it.id == "mep-101"
                }
            ) {
                result +
                    BriefCard(
                        id = "mep-101",
                        localId = "101",
                        name = "Nidorina",
                        imageBase =
                            NIDORINA_PROMO_IMAGE
                    )
            } else {
                result
            }

        cardsCache[
            language
        ] =
            CacheEntry(
                completeResult,
                now + CACHE_MS
            )

        return completeResult
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
