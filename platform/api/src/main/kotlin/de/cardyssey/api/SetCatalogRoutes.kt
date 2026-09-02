package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.route

fun Route.setCatalogRoutes(
    catalog: CardCatalogService
) {
    authenticate("auth-jwt") {

        route("/api/v1/sets") {

            get {
                val language =
                    call.request.queryParameters["language"]
                        ?.trim()
                        ?.lowercase()
                        ?: "de"

                if (!catalog.validLanguage(language)) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_language")
                    )
                    return@get
                }

                call.respond(
                    catalog.sets(language)
                )
            }

            get("/{id}") {
                val id =
                    call.parameters["id"]
                        ?.trim()
                        ?.takeIf { it.isNotBlank() }

                if (id == null) {
                    call.respond(HttpStatusCode.BadRequest)
                    return@get
                }

                val language =
                    call.request.queryParameters["language"]
                        ?.trim()
                        ?.lowercase()
                        ?: "de"

                val set =
                    catalog.setDetails(
                        id,
                        language
                    )

                if (set == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf("error" to "set_not_found")
                    )
                    return@get
                }

                call.respond(set)
            }
        }
    }
}
