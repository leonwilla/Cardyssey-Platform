package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.post
import kotlinx.serialization.Serializable

@Serializable
data class CardRecognitionRequest(
    val text: String = "",
    val language: String = "de",
    val imageBase64: String? = null,
    val number: String? = null,
    val setCode: String? = null
)

@Serializable
data class CardRecognitionResponse(
    val detectedNumber: String? = null,
    val detectedQuery: String? = null,
    val candidates: List<CatalogCardSearchResult>
)

fun Route.cardRecognitionRoutes(
    catalog: CardCatalogService,
    mirror: PermanentCatalogRepository,
    imageHasher: CatalogImageHasher
) {
    authenticate("auth-jwt") {

        post("/api/v1/cards/recognize") {

            val request =
                call.receive<CardRecognitionRequest>()

            val language =
                request.language
                    .trim()
                    .lowercase()

            if (!catalog.validLanguage(language)) {
                call.respond(
                    HttpStatusCode.BadRequest,
                    mapOf(
                        "error" to "invalid_language"
                    )
                )
                return@post
            }

            val text =
                request.text.trim()

            if (
                text.isBlank() &&
                request.imageBase64.isNullOrBlank()
            ) {
                call.respond(
                    HttpStatusCode.BadRequest,
                    mapOf(
                        "error" to "empty_recognition_input"
                    )
                )
                return@post
            }

            val number =
                request.number
                    ?.trim()
                    ?.takeIf(String::isNotBlank)
                    ?: extractCardNumber(text)

            val lines =
                recognitionLines(text)

            val candidates =
                if (number != null) {

                    catalog.search(
                        query = "",
                        number = number,
                        language = language,
                        limit = 50
                    )
                        .sortedBy {
                            recognitionScore(
                                it.name,
                                text
                            )
                        }
                        .take(15)

                } else {

                    val found =
                        linkedMapOf<
                            String,
                            CatalogCardSearchResult
                        >()

                    for (line in lines.take(6)) {

                        val results =
                            catalog.search(
                                query = line,
                                number = null,
                                language = language,
                                limit = 10
                            )

                        for (card in results) {
                            found.putIfAbsent(
                                card.id,
                                card
                            )
                        }
                    }

                    found.values
                        .sortedBy {
                            recognitionScore(
                                it.name,
                                text
                            )
                        }
                        .take(15)
                }

            val visualCandidates =
                request.imageBase64
                    ?.takeIf {
                        it.length <=
                            12_000_000
                    }
                    ?.let { encoded ->
                        runCatching {
                            val bytes =
                                java.util.Base64
                                    .getDecoder()
                                    .decode(
                                        encoded.substringAfter(
                                            ","
                                        )
                                    )

                            val hash =
                                imageHasher.hash(bytes)

                            val narrowed =
                                mirror.visualMatches(
                                    language = language,
                                    hash = hash,
                                    number = number?.substringBefore("/"),
                                    setCode = request.setCode,
                                    limit = 20
                                )

                            val matches = narrowed

                            matches
                                .filter {
                                    it.distance <= 26
                                }
                                .map {
                                    it.card
                                }
                        }
                            .getOrDefault(
                                emptyList()
                            )
                    }
                    .orEmpty()

            /*
             * A good local image hit is the strongest signal. OCR results are
             * retained as corroboration/fallback for glare, missing artwork
             * and cards which have not been mirrored yet.
             */
            val combined =
                (
                    /*
                     * Visual matches are already ordered by perceptual hash
                     * distance (best image hit first). Keep that order ahead
                     * of OCR/name candidates. Previously OCR candidates were
                     * prepended here, so two cards with the same printed name
                     * could make the normal printing shadow the visually
                     * correct illustration/secret rare.
                     */
                    visualCandidates +
                        candidates
                    )
                    .distinctBy {
                        it.id
                    }
                    .take(15)

            call.respond(
                CardRecognitionResponse(
                    detectedNumber = number,
                    detectedQuery =
                        lines.firstOrNull(),
                    candidates =
                        combined
                )
            )
        }
    }
}

private fun extractCardNumber(
    text: String
): String? {

    val match =
        Regex(
            """(?<!\d)(\d{1,3})\s*/\s*(\d{2,3})(?!\d)"""
        )
            .find(text)
            ?: return null

    return "${match.groupValues[1]}/${match.groupValues[2]}"
}

private fun recognitionLines(
    text: String
): List<String> {

    val ignored =
        setOf(
            "basic",
            "stage",
            "trainer",
            "pokemon",
            "pokémon",
            "weakness",
            "resistance",
            "retreat",
            "illus",
            "illustrator"
        )

    return text
        .lines()
        .map {
            it.trim()
                .replace(
                    Regex("""\s+"""),
                    " "
                )
        }
        .filter {
            it.length in 2..40
        }
        .filter {
            it.any(Char::isLetter)
        }
        .filterNot {
            "/" in it
        }
        .filterNot {
            it.lowercase() in ignored
        }
        .distinct()
}

private fun recognitionScore(
    cardName: String,
    ocrText: String
): Int {

    val card =
        cardName
            .lowercase()
            .trim()

    val text =
        ocrText.lowercase()

    if (text.contains(card)) {
        return 0
    }

    val tokens =
        card
            .split(
                Regex("""\s+""")
            )
            .filter {
                it.length >= 3
            }

    val hits =
        tokens.count {
            text.contains(it)
        }

    return 100 - hits * 20
}
