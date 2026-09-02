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
    val text: String,
    val language: String = "de"
)

@Serializable
data class CardRecognitionResponse(
    val detectedNumber: String? = null,
    val detectedQuery: String? = null,
    val candidates: List<CatalogCardSearchResult>
)

fun Route.cardRecognitionRoutes(
    catalog: CardCatalogService
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

            if (text.isBlank()) {
                call.respond(
                    HttpStatusCode.BadRequest,
                    mapOf(
                        "error" to "empty_ocr_text"
                    )
                )
                return@post
            }

            val number =
                extractCardNumber(text)

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

            call.respond(
                CardRecognitionResponse(
                    detectedNumber = number,
                    detectedQuery =
                        lines.firstOrNull(),
                    candidates =
                        candidates
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
