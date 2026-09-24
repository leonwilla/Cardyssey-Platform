package de.cardyssey.api

import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.response.header
import io.ktor.server.response.respond
import io.ktor.server.response.respondFile
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.route

fun Route.cardCatalogRoutes(
    catalog: CardCatalogService,
    mirror: PermanentCatalogRepository
) {

    /*
     * Mirrored images are immutable public catalog assets. The URL keeps the
     * TCGdex-style quality suffix so existing Android/Web image helpers can
     * switch to Tiny without special cases.
     */
    get(
        "/api/v1/catalog/assets/{language}/{cardId}/{file}"
    ) {
        val language =
            call.parameters["language"]
                ?.trim()
                ?.lowercase()

        val cardId =
            call.parameters["cardId"]
                ?.trim()

        if (
            language == null ||
            cardId.isNullOrBlank() ||
            !catalog.validLanguage(language)
        ) {
            call.respond(HttpStatusCode.BadRequest)
            return@get
        }

        val image =
            mirror.storedImage(
                language = language,
                cardId = cardId
            )

        if (image == null) {
            call.respond(HttpStatusCode.NotFound)
            return@get
        }

        call.response.header(
            HttpHeaders.CacheControl,
            "public, max-age=31536000, immutable"
        )
        call.respondFile(
            image.toFile()
        )
    }

    authenticate("auth-jwt") {

        get("/api/v1/catalog/mirror/status") {
            call.respond(
                mirror.statuses()
            )
        }

        route("/api/v1/cards") {

            get("/search") {

                val query =
                    call.request
                        .queryParameters[
                            "q"
                        ]
                        .orEmpty()

                val number =
                    call.request
                        .queryParameters[
                            "number"
                        ]

                val language =
                    call.request
                        .queryParameters[
                            "language"
                        ]
                        ?.trim()
                        ?.lowercase()
                        ?: "de"

                val limit =
                    call.request
                        .queryParameters[
                            "limit"
                        ]
                        ?.toIntOrNull()
                        ?: 20

                if (
                    !catalog.validLanguage(
                        language
                    )
                ) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf(
                            "error" to
                                "invalid_language"
                        )
                    )
                    return@get
                }

                call.respond(
                    catalog.search(
                        query =
                            query,

                        number =
                            number,

                        language =
                            language,

                        limit =
                            limit
                    )
                )
            }


            get("/{id}") {

                val id =
                    call.parameters[
                        "id"
                    ]
                        ?.trim()
                        ?.takeIf {
                            it.isNotBlank()
                        }

                if (id == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf(
                            "error" to
                                "invalid_card_id"
                        )
                    )
                    return@get
                }

                val language =
                    call.request
                        .queryParameters[
                            "language"
                        ]
                        ?.trim()
                        ?.lowercase()
                        ?: "de"

                if (
                    !catalog.validLanguage(
                        language
                    )
                ) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf(
                            "error" to
                                "invalid_language"
                        )
                    )
                    return@get
                }

                val details =
                    catalog.details(
                        cardId =
                            id,

                        language =
                            language
                    )

                if (details == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf(
                            "error" to
                                "card_not_found"
                        )
                    )
                    return@get
                }

                call.respond(details)
            }
        }
    }
}
