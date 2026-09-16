package de.cardyssey.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.jsoup.Jsoup
import org.jsoup.nodes.Element
import java.net.URI
import java.net.URLEncoder
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.charset.StandardCharsets
import java.time.Duration
import java.time.LocalDate
import java.time.ZoneOffset
import java.util.Locale

/**
 * Liest die öffentlich sichtbaren, als verkauft markierten ebay.de-Suchergebnisse.
 *
 * Der Collector ist absichtlich konservativ:
 * - alle Requests laufen seriell und mit Mindestabstand,
 * - Captcha-/Challenge-Seiten gelten als Fehler,
 * - Angebote ohne eindeutigen Preis oder Verkaufsdatum werden verworfen,
 * - angenommene Preisvorschläge werden nicht als Verkaufspreis interpretiert.
 *
 * Die fachliche Karten-, Sprach- und Variantenprüfung bleibt im zentralen
 * Ebay-Quote-Provider. Diese Klasse ersetzt nur die Rohdatenlieferung.
 */
class EbayDirectSoldListingCollector(
    private val cookieHeader: String = "",
    private val requestSpacingMs: Long = 2_000L
) {
    private val http =
        HttpClient
            .newBuilder()
            .connectTimeout(Duration.ofSeconds(12))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build()

    private val requestLock = Any()

    @Volatile
    private var lastRequestAtMs: Long = 0L

    suspend fun search(
        query: String
    ): List<JsonObject>? =
        withContext(Dispatchers.IO) {
            synchronized(requestLock) {
                val waitMs =
                    requestSpacingMs -
                        (System.currentTimeMillis() - lastRequestAtMs)

                if (waitMs > 0L) {
                    Thread.sleep(waitMs)
                }

                try {
                    val requestBuilder =
                        HttpRequest
                            .newBuilder(
                                URI.create(
                                    SEARCH_URL +
                                        "?_nkw=" + encode(query) +
                                        "&_sacat=" + POKEMON_SINGLE_CARD_CATEGORY +
                                        "&LH_Sold=1" +
                                        "&LH_Complete=1" +
                                        "&_sop=13" +
                                        "&_ipg=240"
                                )
                            )
                            .timeout(Duration.ofSeconds(35))
                            .header(
                                "Accept",
                                "text/html,application/xhtml+xml"
                            )
                            .header(
                                "Accept-Language",
                                "de-DE,de;q=0.9,en;q=0.6"
                            )
                            .header(
                                "User-Agent",
                                "Cardyssey/0.2 (+https://cardyssey.de)"
                            )

                    if (cookieHeader.isNotBlank()) {
                        requestBuilder.header(
                            "Cookie",
                            cookieHeader
                        )
                    }

                    val request =
                        requestBuilder
                            .GET()
                            .build()

                    val response =
                        http.send(
                            request,
                            HttpResponse.BodyHandlers.ofString()
                        )

                    lastRequestAtMs = System.currentTimeMillis()

                    if (response.statusCode() !in 200..299) {
                        println(
                            "eBay direct request failed: HTTP ${response.statusCode()}"
                        )
                        return@synchronized null
                    }

                    if (
                        response.uri().host.equals(
                            "signin.ebay.de",
                            ignoreCase = true
                        )
                    ) {
                        println(
                            "eBay direct request needs a renewed server session"
                        )
                        return@synchronized null
                    }

                    val body = response.body()
                    if (looksLikeChallenge(body)) {
                        println("eBay direct request blocked by challenge page")
                        return@synchronized null
                    }

                    parse(body).also { items ->
                        println(
                            "eBay direct request: queryLength=${query.length} parsed=${items.size}"
                        )
                    }
                } catch (error: Exception) {
                    lastRequestAtMs = System.currentTimeMillis()
                    println(
                        "eBay direct request failed: ${error.message}"
                    )
                    null
                }
            }
        }

    internal fun parse(
        html: String
    ): List<JsonObject> {
        val document = Jsoup.parse(html, SEARCH_URL)
        val result = linkedMapOf<String, JsonObject>()

        document
            .select("li.s-item, div.s-card")
            .forEach { element ->
                parseListing(element)?.let { listing ->
                    val stableId =
                        listing["itemId"]
                            ?.toString()
                            ?.takeIf(String::isNotBlank)
                            ?: listing["url"].toString()

                    result.putIfAbsent(stableId, listing)
                }
            }

        if (result.isEmpty() && !looksLikeEmptyResult(document.text())) {
            throw IllegalStateException(
                "eBay result markup was not recognized"
            )
        }

        return result.values.toList()
    }

    private fun parseListing(
        element: Element
    ): JsonObject? {
        val linkElement =
            element.selectFirst(
                "a.s-item__link[href], a.s-card__link[href], a[href*=\"/itm/\"]"
            ) ?: return null

        val url =
            linkElement
                .absUrl("href")
                .substringBefore('?')
                .takeIf {
                    it.startsWith(
                        "https://",
                        ignoreCase = true
                    )
                }
                ?: return null

        val itemId =
            ITEM_ID_REGEX
                .find(url)
                ?.groupValues
                ?.getOrNull(1)
                ?: return null

        val rawTitle =
            element
                .selectFirst(
                    ".s-item__title, .s-card__title, [role=heading]"
                )
                ?.text()
                ?.trim()
                .orEmpty()

        val title =
            rawTitle
                .removePrefix("Neues Angebot")
                .removePrefix("New Listing")
                .trim()

        if (
            title.isBlank() ||
            title.equals(
                "Shop on eBay",
                ignoreCase = true
            )
        ) {
            return null
        }

        val fullText = element.text()

        /*
         * eBay listet bei abgeschlossenen Suchen teilweise auch Angebote,
         * die vom Verkäufer nur beendet wurden. Nur ein ausdrücklich als
         * verkauft markierter Eintrag darf als Vergleichsverkauf gelten.
         */
        if (!hasExplicitSoldStatus(fullText)) {
            return null
        }

        val endedAt =
            parseSoldDate(fullText)
                ?.toString()
                ?: return null

        val bestOfferAccepted =
            BEST_OFFER_MARKERS.any {
                fullText.contains(
                    it,
                    ignoreCase = true
                )
            }

        val priceText =
            element
                .selectFirst(
                    ".s-item__price, .s-card__price"
                )
                ?.text()
                ?.trim()
                ?: return null

        val soldPrice =
            parseEuroPrice(priceText)
                ?: return null

        val condition =
            element
                .selectFirst(
                    ".SECONDARY_INFO, .s-item__subtitle, .s-card__subtitle"
                )
                ?.text()
                ?.trim()
                ?.takeIf(String::isNotBlank)

        val fields =
            linkedMapOf<String, JsonPrimitive>(
                "itemId" to JsonPrimitive(itemId),
                "title" to JsonPrimitive(title),
                "soldPrice" to JsonPrimitive(soldPrice),
                "soldCurrency" to JsonPrimitive("EUR"),
                "endedAt" to JsonPrimitive(endedAt),
                "url" to JsonPrimitive(url),
                "bestOfferAccepted" to JsonPrimitive(bestOfferAccepted)
            )

        condition?.let {
            fields["condition"] = JsonPrimitive(it)
        }

        return JsonObject(fields)
    }

    private fun parseEuroPrice(
        text: String
    ): Double? {
        val normalizedText =
            text
                .lowercase(Locale.GERMANY)
                .replace(Regex("\\s+"), " ")
                .trim()

        /*
         * eBay kennzeichnet umgerechnete Fremdwährungspreise als ungefähr
         * (zum Beispiel "ca. EUR"). Diese Werte hängen von eBays eigener
         * Umrechnung ab und werden nicht als belastbarer Verkaufspreis
         * übernommen. Bis Cardyssey Originalwährung und ECB-Kurs gemeinsam
         * gespeichert hat, akzeptieren wir nur echte EUR-Preise.
         */
        if (
            APPROXIMATE_PRICE_MARKERS.any {
                it in normalizedText
            } ||
            FOREIGN_CURRENCY_MARKERS.any {
                it in normalizedText
            }
        ) {
            return null
        }

        if (
            !text.contains("EUR", ignoreCase = true) &&
            '€' !in text
        ) {
            return null
        }

        val matches =
            PRICE_REGEX
                .findAll(text)
                .map { it.value.trim() }
                .toList()

        if (matches.size != 1) return null

        val raw =
            matches.single()
                .replace(" ", "")
                .replace("\u00A0", "")

        val normalized =
            when {
                ',' in raw && '.' in raw ->
                    if (raw.lastIndexOf(',') > raw.lastIndexOf('.')) {
                        raw.replace(".", "").replace(',', '.')
                    } else {
                        raw.replace(",", "")
                    }

                ',' in raw ->
                    raw.replace(".", "").replace(',', '.')

                else ->
                    raw
            }

        return normalized
            .toDoubleOrNull()
            ?.takeIf {
                it.isFinite() &&
                    it > 0.0
            }
    }

    private fun hasExplicitSoldStatus(
        text: String
    ): Boolean {
        val normalized =
            text
                .lowercase(Locale.GERMANY)
                .replace(Regex("\\s+"), " ")
                .trim()

        if (
            ENDED_WITHOUT_SALE_MARKERS.any {
                it in normalized
            }
        ) {
            return false
        }

        return EXPLICIT_SOLD_MARKERS.any {
            it in normalized
        }
    }

    private fun parseSoldDate(
        text: String
    ): LocalDate? {
        val normalized =
            text
                .lowercase(Locale.GERMANY)
                .replace(",", " ")
                .replace(Regex("\\s+"), " ")

        val today = LocalDate.now(ZoneOffset.UTC)

        if (
            "heute verkauft" in normalized ||
            "verkauft heute" in normalized ||
            "sold today" in normalized
        ) {
            return today
        }

        if (
            "gestern verkauft" in normalized ||
            "verkauft gestern" in normalized ||
            "sold yesterday" in normalized
        ) {
            return today.minusDays(1)
        }

        GERMAN_DATE_REGEX.find(normalized)?.let { match ->
            val day =
                match.groupValues[1]
                    .toIntOrNull()
                    ?: return@let

            val month =
                MONTHS[match.groupValues[2]]
                    ?: return@let

            val explicitYear =
                match.groupValues[3]
                    .toIntOrNull()

            var date =
                runCatching {
                    LocalDate.of(
                        explicitYear ?: today.year,
                        month,
                        day
                    )
                }.getOrNull()
                    ?: return@let

            if (
                explicitYear == null &&
                date.isAfter(today.plusDays(1))
            ) {
                date = date.minusYears(1)
            }

            return date
        }

        ENGLISH_DATE_REGEX.find(normalized)?.let { match ->
            val month =
                MONTHS[match.groupValues[1]]
                    ?: return@let

            val day =
                match.groupValues[2]
                    .toIntOrNull()
                    ?: return@let

            val year =
                match.groupValues[3]
                    .toIntOrNull()
                    ?: return@let

            return runCatching {
                LocalDate.of(year, month, day)
            }.getOrNull()
        }

        return null
    }

    private fun looksLikeChallenge(
        html: String
    ): Boolean {
        val normalized = html.lowercase(Locale.ROOT)
        return normalized.length < 1_000 ||
            "pardon our interruption" in normalized ||
            "security measure" in normalized ||
            "captcha" in normalized ||
            "verify you are human" in normalized ||
            "bestätigen sie, dass sie ein mensch" in normalized
    }

    private fun looksLikeEmptyResult(
        text: String
    ): Boolean {
        val normalized = text.lowercase(Locale.GERMANY)
        return "0 ergebnisse" in normalized ||
            "keine exakten treffer" in normalized ||
            "no exact matches found" in normalized ||
            "0 results" in normalized
    }

    private fun encode(
        value: String
    ): String =
        URLEncoder.encode(
            value,
            StandardCharsets.UTF_8
        )

    companion object {
        private const val SEARCH_URL =
            "https://www.ebay.de/sch/i.html"

        private const val POKEMON_SINGLE_CARD_CATEGORY =
            "183454"

        private val ITEM_ID_REGEX =
            Regex("""/itm/(?:[^/?]+/)?([0-9]{9,15})(?:[/?]|$)""")

        private val PRICE_REGEX =
            Regex("""[0-9][0-9.\s\u00A0]*[,.][0-9]{2}""")

        private val GERMAN_DATE_REGEX =
            Regex(
                """(?:verkauft(?:\s+am)?|sold(?:\s+on)?)?\s*([0-9]{1,2})\.\s*([a-zäöü]+)\.?\s*([0-9]{4})?"""
            )

        private val ENGLISH_DATE_REGEX =
            Regex(
                """(?:sold(?:\s+on)?\s*)?([a-z]+)\s+([0-9]{1,2})\s+([0-9]{4})"""
            )

        private val EXPLICIT_SOLD_MARKERS =
            listOf(
                "verkauft",
                "wurde verkauft",
                "sold"
            )

        private val ENDED_WITHOUT_SALE_MARKERS =
            listOf(
                "beendet",
                "nicht mehr verfügbar",
                "nicht mehr verfugbar",
                "ended",
                "no longer available"
            )

        private val APPROXIMATE_PRICE_MARKERS =
            listOf(
                "ca.",
                "ca ",
                "circa",
                "ungefähr",
                "ungefahr",
                "approx",
                "approximately"
            )

        private val FOREIGN_CURRENCY_MARKERS =
            listOf(
                "us $",
                "usd",
                "gbp",
                "£",
                "cad",
                "c $",
                "aud",
                "au $",
                "jpy",
                "¥"
            )

        private val BEST_OFFER_MARKERS =
            listOf(
                "preisvorschlag angenommen",
                "accepted best offer",
                "best offer accepted"
            )

        private val MONTHS =
            mapOf(
                "jan" to 1,
                "januar" to 1,
                "january" to 1,
                "feb" to 2,
                "februar" to 2,
                "february" to 2,
                "mär" to 3,
                "maerz" to 3,
                "märz" to 3,
                "mar" to 3,
                "march" to 3,
                "apr" to 4,
                "april" to 4,
                "mai" to 5,
                "may" to 5,
                "jun" to 6,
                "juni" to 6,
                "june" to 6,
                "jul" to 7,
                "juli" to 7,
                "july" to 7,
                "aug" to 8,
                "august" to 8,
                "sep" to 9,
                "sept" to 9,
                "september" to 9,
                "okt" to 10,
                "oktober" to 10,
                "oct" to 10,
                "october" to 10,
                "nov" to 11,
                "november" to 11,
                "dez" to 12,
                "dezember" to 12,
                "dec" to 12,
                "december" to 12
            )
    }
}
