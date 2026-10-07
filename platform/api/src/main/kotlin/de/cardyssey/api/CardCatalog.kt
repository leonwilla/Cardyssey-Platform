package de.cardyssey.api

import kotlinx.coroutines.CancellationException
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
import java.net.URLEncoder
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.charset.StandardCharsets
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
    val tcgDexEur: Double? = null,
    val tcgPlayerId: String? = null,
    val cardmarketProductId: String? = null
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

data class CatalogSourceSnapshot(
    val sets: List<CatalogSetSummary>,
    val cards: List<CatalogCardSearchResult>
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

private fun catalogImageFallback(cardId: String): String? = CLASSIC_COLLECTION_IMAGE_FALLBACKS[cardId]

class CardCatalogService(
    private val persistentCache: CatalogCacheRepository,
    private val supplemental: SupplementalCatalogRepository? = null,
    private val mirror: PermanentCatalogRepository? = null
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
                "zh-cn",
                "id",
                "th",
                "nl",
                "pl",
                "ru"
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
        listOf("de", "en", "ko", "ja", "zh-tw", "zh-cn")
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

    suspend fun search(query: String, number: String?, language: String, limit: Int): List<CatalogCardSearchResult> {
        val images = anniversaryCards(language).associateBy { it.id }
        return searchMerged(query, number, language, limit).map { card ->
            card.copy(
                imageBase =
                    mirror?.completeImageBase(language, card.id)
                        ?: images[card.id]?.imageBase
                        ?: card.imageBase
            )
        }
    }

    private suspend fun searchMerged(query: String, number: String?, language: String, limit: Int): List<CatalogCardSearchResult> {
        val extra = supplemental?.cards(language).orEmpty()
        if (extra.isEmpty()) return searchPrimary(query, number, language, limit)
        val expectedTotal = number?.substringAfter('/', "")?.trim()?.toIntOrNull()
        val candidates = extra.filter { card ->
            (expectedTotal == null || card.officialCount == expectedTotal) &&
            (number.isNullOrBlank() || normalizeNumber(card.localId) == normalizeNumber(number)) &&
                (query.isBlank() || scoreName(card.name, query.trim().lowercase()) < 100)
        }.map { card ->
            CatalogCardSearchResult(card.id, card.localId, card.name, card.setId, card.setName, card.imageBase)
        }
        val primary = searchPrimary(query, number, language, limit)
        if (query.isBlank() && number.isNullOrBlank()) return emptyList()
        val images = extra.associateBy { it.id }
        return (primary.map { card ->
            val supplement = images[card.id]
            if (supplement?.imageBase == null) card else card.copy(imageBase = supplement.imageBase)
        } + candidates).distinctBy { it.id }
            .sortedWith(compareBy<CatalogCardSearchResult> { scoreName(it.name, query.trim().lowercase()) }.thenBy { it.name })
            .take(limit.coerceIn(1, 250))
    }

    private fun anniversaryCards(language: String, localImages: Boolean = true): List<CatalogCardDetails> =
        AnniversaryPromos.cards(language).map { card ->
            val source = card.imageBase
            if (localImages && source != null && mirror?.hasImageSource(language, card.id, source) == true)
                card.copy(imageBase = mirror.imageBase(language, card.id)) else card
        }

    suspend fun details(cardId: String, language: String, forceRemote: Boolean = false): CatalogCardDetails? {
        val curated = anniversaryCards(language, localImages = !forceRemote).firstOrNull { it.id == cardId }
        val extra = if (forceRemote) null else supplemental?.cards(language)?.firstOrNull { it.id == cardId }
        if (cardId.startsWith("official_")) return extra
        val fetched = detailsPrimary(cardId, language, forceRemote)
        val primary = if (curated != null && fetched?.languageCode != language) curated else fetched ?: curated ?: return extra
        // Prefer a verified image mirrored for the requested language. This avoids
        // showing an English fallback for a German card when Tiny already has the
        // localized scan.
        val localizedImage =
            if (forceRemote) null
            else mirror?.completeImageBase(language, cardId)

        // Retain richer physical variants/prices when the primary provider has them.
        return when {
            localizedImage != null ->
                primary.copy(imageBase = localizedImage, imageLanguage = language)
            curated?.imageBase != null ->
                primary.copy(imageBase = curated.imageBase, imageLanguage = language)
            !forceRemote && extra?.imageBase != null ->
                primary.copy(imageBase = extra.imageBase, imageLanguage = language)
            else -> primary
        }
    }

    suspend fun sets(language: String): List<CatalogSetSummary> {
        val listed = setsPrimary(language)
        val listedIds = listed.map { it.id.lowercase() }.toSet()
        val promoIds = setOf("basep", "wbsp", "np", "dpp", "hgssp", "bwp", "xyp", "smp", "swshp", "svp", "mep")
        val indexedCards = loadCards(language).groupBy { it.id.substringBeforeLast("-", "") }
        val missingPromos = indexedCards
            .filterKeys { id -> id.lowercase() !in listedIds &&
                (id.lowercase() in promoIds || id.matches(Regex("(?i)(?:bw|xy|sm|s|sv|me)-p"))) }
            .map { (id, cards) -> CatalogSetSummary(id, "${id.uppercase()} Promos", totalCount = cards.size) }
        /*
         * AnniversaryPromos is a product grouping inside the 30th set detail,
         * not a top-level physical set. Keep the canonical cards in MEP and
         * avoid showing a duplicate "30 Jahre – Promos" entry in the library.
         */
        val primary = listed + missingPromos
        val extra = supplemental?.cards(language).orEmpty().groupBy { it.setId }
        val byId = primary.associateBy { it.id.lowercase() }
        return primary.map { set ->
            val cards = extra.entries.firstOrNull { it.key.equals(set.id, true) }?.value.orEmpty()
            set.copy(totalCount = maxOf(set.totalCount, cards.size, if (set.id == "mep") indexedCards[set.id].orEmpty().size else 0))
        } + extra.filterKeys { it.lowercase() !in byId }.map { (id, cards) ->
            CatalogSetSummary(id, cards.first().setName, officialCount = cards.maxOf { it.officialCount }, totalCount = cards.size)
        }
    }

    suspend fun setDetails(setId: String, language: String): CatalogSetDetails? {
        val curated = anniversaryCards(language)
        if (setId == AnniversaryPromos.SET_ID) {
            if (curated.isEmpty()) return null
            return CatalogSetDetails(setId, AnniversaryPromos.title(language), totalCount = curated.size,
                cards = curated.map { CatalogSetCard(it.id, it.localId, it.name, it.imageBase) })
        }
        val extra = ((if (setId.equals("mep", true)) curated else emptyList()) +
            supplemental?.cards(language).orEmpty().filter { it.setId.equals(setId, true) }).distinctBy { it.id }
        val primary = setDetailsPrimary(setId, language) ?: loadCards(language)
            .filter { it.id.substringBeforeLast("-", "").equals(setId, true) }
            .takeIf { it.isNotEmpty() }?.let { cards ->
                CatalogSetDetails(setId, "${setId.uppercase()} Promos", totalCount = cards.size,
                    cards = cards.map { CatalogSetCard(it.id, it.localId, it.name, it.imageBase) })
            }
        if (extra.isEmpty()) return primary
        val images = extra.associateBy { it.id }
        val cards = (primary?.cards.orEmpty().map { card ->
            card.copy(
                imageBase =
                    mirror?.completeImageBase(language, card.id)
                        ?: images[card.id]?.imageBase
                        ?: card.imageBase
            )
        } + extra.map { card ->
            CatalogSetCard(
                card.id,
                card.localId,
                card.name,
                mirror?.completeImageBase(language, card.id) ?: card.imageBase
            )
        })
            .distinctBy { it.id }.sortedWith(compareBy<CatalogSetCard> { it.localId.toIntOrNull() ?: Int.MAX_VALUE }.thenBy { it.localId })
        return (primary ?: CatalogSetDetails(setId, extra.first().setName,
            officialCount = extra.maxOf { it.officialCount }, totalCount = cards.size, cards = cards))
            .copy(cards = cards, totalCount = maxOf(primary?.totalCount ?: 0, cards.size))
    }

    private suspend fun searchPrimary(
        query: String,
        number: String?,
        language: String,
        limit: Int
    ): List<CatalogCardSearchResult> {

        val safeLimit =
            limit.coerceIn(1, 250)

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

        val expectedTotal = number?.substringAfter('/', "")?.trim()?.toIntOrNull()
        if (expectedTotal != null) {
            val matchingSets = setsPrimary(language).filter { it.officialCount == expectedTotal }.map { it.id }.toSet()
            cards = cards.filter { it.id.substringBeforeLast("-", "") in matchingSets }
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

    private suspend fun detailsPrimary(
        cardId: String,
        language: String,
        forceRemote: Boolean = false
    ): CatalogCardDetails? {

        val requested =
            loadCardObject(
                language,
                cardId,
                forceRemote
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
                    cardId,
                    forceRemote
                )
            } else {
                null
            }

        val source =
            requested
                ?: english
                ?: return AnniversaryPromos.cards(language).firstOrNull { it.id == cardId }

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


    private suspend fun setsPrimary(
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
                        (
                            set.totalCount
                                .takeIf {
                                    it > 0
                                }
                                ?: fallback
                                    ?.totalCount
                                ?: 0
                        ).let { count ->
                            if (
                                language == "de" &&
                                set.id == "mep"
                            ) {
                                maxOf(
                                    count,
                                    89
                                )
                            } else {
                                count
                            }
                        }
                )
            }
            .let { sets ->
                if (language == "zh-cn") {
                    sets.filter { it.id.equals("CSMPiC", ignoreCase = true) }
                } else {
                    sets
                }
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


    private suspend fun setDetailsPrimary(
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
                    maxOf(
                        sourceCount
                            ?.int("total")
                            ?: 0,
                        englishCount
                            ?.int("total")
                            ?: 0,
                        cards.size
                    ),
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


    suspend fun refreshSourceIndex(
        language: String
    ): CatalogSourceSnapshot {
        require(validLanguage(language)) {
            "Unsupported catalog language: $language"
        }

        cardsCache.remove(language)
        setsCache.remove(language)
        setSummaryCache.remove(language)
        setDetailsCache.keys.removeIf { it.startsWith("$language:") }

        val cards =
            loadCards(
                language = language,
                forceRemote = true,
                allowEnglishFallback = false
            )

        val setNames =
            loadSets(
                language = language,
                forceRemote = true,
                allowEnglishFallback = false
            )

        val basicSets =
            setNames.map { (id, name) ->
                CatalogSetSummary(
                    id = id,
                    name = name
                )
            }

        val detailedSets =
            runCatching {
                setsPrimary(language)
            }
                .getOrDefault(basicSets)
                .ifEmpty {
                    basicSets
                }

        val namesById =
            detailedSets.associateBy {
                it.id
            }

        val cardResults =
            cards.map { card ->
                val setId =
                    card.id.substringBeforeLast(
                        "-",
                        "unknown"
                    )

                CatalogCardSearchResult(
                    id = card.id,
                    localId = card.localId,
                    name = card.name,
                    setId = setId,
                    setName =
                        namesById[setId]
                            ?.name
                            ?: setNames[setId],
                    imageBase = card.imageBase
                )
            }

        return CatalogSourceSnapshot(
            sets = detailedSets,
            cards = cardResults
        )
    }

    private suspend fun loadCards(
        language: String,
        forceRemote: Boolean = false,
        allowEnglishFallback: Boolean = true
    ): List<BriefCard> {

        val now =
            System.currentTimeMillis()

        cardsCache[
            language
        ]
            ?.takeIf {
                !forceRemote && it.expiresAtMs > now
            }
            ?.let {
                return it.value
            }

        val loaded =
            runCatching {
                fetchArray(
                    "$BASE/$language/cards",
                    forceRemote = forceRemote
                )
            }
                .onFailure {
                    if (it is CancellationException || forceRemote) throw it
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
                .let { cards ->
                    // TCGdex currently labels Taiwan/traditional SV data as zh-cn.
                    // Until a verified Simplified-Chinese source is configured,
                    // only keep the genuine Simplified-Chinese CSMPiC set.
                    if (language == "zh-cn") {
                        cards.filter { it.id.startsWith("CSMPiC-", ignoreCase = true) }
                    } else {
                        cards
                    }
                }

        val result =
            if (
                loaded.isEmpty() &&
                language != "en" &&
                allowEnglishFallback
            ) {
                loadCards(
                    language = "en",
                    forceRemote = forceRemote,
                    allowEnglishFallback = true
                )
            } else {
                loaded
            }

        val curated = AnniversaryPromos.cards(language).associateBy { it.id }
        val completeResult = (result.map { card ->
            val promo = curated[card.id]
            if (promo?.imageBase != null) card.copy(imageBase = promo.imageBase) else card
        } + curated.values.map { BriefCard(it.id, it.localId, it.name, it.imageBase) }).distinctBy { it.id }

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
        language: String,
        forceRemote: Boolean = false,
        allowEnglishFallback: Boolean = true
    ): Map<String, String> {

        val now =
            System.currentTimeMillis()

        setsCache[
            language
        ]
            ?.takeIf {
                !forceRemote && it.expiresAtMs > now
            }
            ?.let {
                return it.value
            }

        val loaded =
            runCatching {
                fetchArray(
                    "$BASE/$language/sets",
                    forceRemote = forceRemote
                )
            }
                .onFailure {
                    if (it is CancellationException || forceRemote) throw it
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
                .let { sets ->
                    if (language == "zh-cn") {
                        sets.filterKeys { it.equals("CSMPiC", ignoreCase = true) }
                    } else {
                        sets
                    }
                }

        val result =
            if (
                loaded.isEmpty() &&
                language != "en" &&
                allowEnglishFallback
            ) {
                loadSets(
                    language = "en",
                    forceRemote = forceRemote,
                    allowEnglishFallback = true
                )
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
        cardId: String,
        forceRemote: Boolean = false
    ): JsonObject? =
        runCatching {
            fetchObject(
                "$BASE/$language/cards/${encodePathSegment(cardId)}",
                forceRemote = forceRemote
            )
        }.getOrNull()

    private fun encodePathSegment(
        value: String
    ): String =
        URLEncoder
            .encode(
                value,
                StandardCharsets.UTF_8
            )
            .replace("+", "%20")

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

                    val thirdParty =
                        raw["thirdParty"]
                            ?.asObject()

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
                                raw,
                                type
                            ),

                        tcgPlayerId =
                            thirdParty
                                ?.get("tcgplayer")
                                ?.asPrimitive()
                                ?.content,

                        cardmarketProductId =
                            thirdParty
                                ?.get("cardmarket")
                                ?.asPrimitive()
                                ?.content
                    )
                }
                .distinctBy {
                    it.id
                }

        val curated =
            curatedPhysicalVariants(
                card =
                    card,
                language =
                    language
            )

        if (detailed.isNotEmpty()) {
            return (
                detailed +
                    curated
                )
                .distinctBy {
                    it.id
                }
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

        return (
            result +
                curated
            )
            .distinctBy {
                it.id
            }
    }

    /*
     * Curated physical printings that are documented but still missing from
     * the upstream variant metadata. Keep these tightly scoped by language,
     * set and card number so they cannot leak onto another printing.
     */
    private fun curatedPhysicalVariants(
        card: JsonObject,
        language: String
    ): List<CatalogVariant> {
        val supportedLanguage = language.lowercase()
        if (supportedLanguage !in setOf("de", "en")) {
            return emptyList()
        }

        val localId =
            card.string(
                "localId"
            )
                ?.trim()
                ?.trimStart(
                    '0'
                )
                ?.ifBlank {
                    "0"
                }

        val setId =
            card["set"]
                ?.asObject()
                ?.string(
                    "id"
                )
                ?.trim()
                ?.lowercase()

        /*
         * English Black & White promos with documented deck/tin holo
         * printings that upstream TCGdex currently collapses to one generated
         * Normal variant. TCGplayer exposes these as distinct products.
         */
        if (
            supportedLanguage == "en" &&
            setId == "bwp" &&
            localId in setOf("BW13", "BW25", "BW33", "BW34", "BW80")
        ) {
            val result =
                mutableListOf<CatalogVariant>()

            if (localId == "BW80") {
                result +=
                    CatalogVariant(
                        id = "curated:en:bwp:BW80:holo",
                        type = "Holo",
                        size = "standard",
                        legacyVariant = "HOLO",
                        tcgDexEur = null
                    )
            }

            result +=
                CatalogVariant(
                    id = "curated:en:bwp:$localId:cosmos-holo",
                    type = "Holo",
                    foil = "cosmos",
                    size = "standard",
                    legacyVariant = "HOLO",
                    tcgDexEur = null
                )

            if (localId in setOf("BW13", "BW25", "BW34")) {
                result +=
                    CatalogVariant(
                        id = "curated:en:bwp:$localId:cracked-ice-holo",
                        type = "Holo",
                        foil = "cracked-ice",
                        size = "standard",
                        legacyVariant = "HOLO",
                        tcgDexEur = null
                    )
            }

            return result
        }

        if (
            supportedLanguage == "en" &&
            setId == "smp" &&
            localId == "SM184"
        ) {
            return listOf(
                CatalogVariant(
                    id = "curated:en:smp:SM184:cosmos-holo",
                    type = "Holo",
                    foil = "cosmos",
                    size = "standard",
                    legacyVariant = "HOLO",
                    tcgDexEur = null
                )
            )
        }

        // German SV01 Felori 013/198 also exists as a Holo printing and
        // as the stamped Grass/leaf-symbol reverse printing. Upstream currently
        // exposes only Normal + Reverse for this German card.
        if (
            supportedLanguage == "de" &&
            setId == "sv01" &&
            localId == "13"
        ) {
            return listOf(
                CatalogVariant(
                    id = "curated:de:sv01:013:holo",
                    type = "Holo",
                    size = "standard",
                    legacyVariant = "HOLO",
                    tcgDexEur = null
                ),
                CatalogVariant(
                    id = "curated:de:sv01:013:grass-stamp",
                    type = "Reverse",
                    foil = "Grass symbol",
                    size = "standard",
                    stamps = listOf("grass-symbol"),
                    legacyVariant = "REVERSE",
                    tcgDexEur = null
                )
            )
        }

        if (
            supportedLanguage == "en" &&
            setId ==
                "sv02" &&
            localId ==
                "62"
        ) {
            return listOf(
                CatalogVariant(
                    id =
                        "curated:pumpkin-pikachu-stamp:2023",
                    type =
                        "holo",
                    foil =
                        "mirage",
                    size =
                        "standard",
                    stamps =
                        listOf(
                            "pumpkin-pikachu"
                        ),
                    legacyVariant =
                        "HOLO",
                    tcgDexEur =
                        null
                )
            )
        }

        return emptyList()
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
        variant: JsonObject,
        type: String
    ): Double? {

        val cardmarket =
            variant["pricing"]
                ?.asObject()
                ?.get(
                    "cardmarket"
                )
                ?.asObject()
                ?: return null

        val normalizedType =
            type
                .trim()
                .lowercase()

        val foil =
            variant.string(
                "foil"
            )

        val holoLike =
            normalizedType ==
                "reverse" ||
                normalizedType ==
                    "holo" ||
                !foil.isNullOrBlank()

        val keys =
            if (holoLike) {
                listOf(
                    "trend-holo",
                    "avg7-holo",
                    "avg30-holo",
                    "avg-holo",
                    "low-holo",
                    "trend",
                    "avg7",
                    "avg30",
                    "avg",
                    "low"
                )
            } else {
                listOf(
                    "trend",
                    "avg7",
                    "avg30",
                    "avg",
                    "low"
                )
            }

        return keys
            .firstNotNullOfOrNull {
                key ->

                cardmarket
                    .double(
                        key
                    )
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
        url: String,
        forceRemote: Boolean = false
    ): JsonArray =
        fetchJson(
            url = url,
            forceRemote = forceRemote
        )
            .jsonArray

    private suspend fun fetchObject(
        url: String,
        forceRemote: Boolean = false
    ): JsonObject =
        fetchJson(
            url = url,
            forceRemote = forceRemote
        )
            .jsonObject

    private suspend fun fetchJson(
        url: String,
        forceRemote: Boolean = false
    ): JsonElement =
        withContext(
            Dispatchers.IO
        ) {
            if (!forceRemote) {
                persistentCache
                    .read(url, maxAgeHours = 6L)
                    ?.let { cached ->
                        return@withContext json
                            .parseToJsonElement(
                                cached
                            )
                    }
            }

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
                if (cause is CancellationException || forceRemote) throw cause

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

