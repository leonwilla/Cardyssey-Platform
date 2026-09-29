package de.cardyssey.api


import io.ktor.http.HttpStatusCode
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.put
import io.ktor.server.routing.route

fun Route.collectionRoutes(
    repository: CollectionRepository
) {
    authenticate("auth-jwt") {
        route("/api/v1/collection") {
            get {
                val userId = call.authenticatedUserId()
                if (userId == null) {
                    call.respond(HttpStatusCode.Unauthorized)
                    return@get
                }
                call.respond(repository.list(userId).map(::withCentralValuation))
            }

            post {
                val userId = call.authenticatedUserId()
                if (userId == null) {
                    call.respond(HttpStatusCode.Unauthorized)
                    return@post
                }
                val item = call.receive<CollectionItemDto>()
                if (!item.isValidCollectionItem()) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_collection_item"))
                    return@post
                }
                repository.importCollection(userId, listOf(item))
                call.respond(HttpStatusCode.Created, mapOf("status" to "created", "key" to item.key))
            }

            put("/{key}") {
                val userId = call.authenticatedUserId()
                if (userId == null) {
                    call.respond(HttpStatusCode.Unauthorized)
                    return@put
                }
                val key = call.parameters["key"]?.trim()
                if (key.isNullOrBlank() || key.length > 100) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_key"))
                    return@put
                }
                val item = call.receive<CollectionItemDto>().copy(key = key)
                if (!item.isValidCollectionItem()) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_collection_item"))
                    return@put
                }
                repository.importCollection(userId, listOf(item))
                call.respond(mapOf("status" to "updated", "key" to key))
            }

            delete("/{key}") {
                val userId = call.authenticatedUserId()
                if (userId == null) {
                    call.respond(HttpStatusCode.Unauthorized)
                    return@delete
                }
                val key = call.parameters["key"]?.trim()
                if (key.isNullOrBlank() || key.length > 100) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_key"))
                    return@delete
                }
                if (!repository.deleteByClientKey(userId, key)) {
                    call.respond(HttpStatusCode.NotFound, mapOf("error" to "collection_item_not_found"))
                    return@delete
                }
                call.respond(HttpStatusCode.NoContent)
            }

            post("/import") {
                val userId = call.authenticatedUserId()
                if (userId == null) {
                    call.respond(HttpStatusCode.Unauthorized)
                    return@post
                }
                val items = call.receive<List<CollectionItemDto>>()
                if (items.size > 10_000 || items.any { !it.isValidCollectionItem() }) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_collection_import"))
                    return@post
                }
                val imported = repository.importCollection(userId, items)
                call.respond(CollectionImportResponse(imported, repository.list(userId).size))
            }
        }
    }
}

private fun withCentralValuation(item: CollectionItemDto): CollectionItemDto {
    val condition = PricingCondition.parse(item.condition)
        ?: return item.copy(valuedUnitEur = emptyMap(), positionValueEur = emptyMap())
    val conditionFactor = condition.factor
    val bases = buildMap {
        putAll(item.marketUnitEur)
        if ("TCG" !in this && item.unitEur != null) put("TCG", item.unitEur)
    }
    val valued = bases.mapValues { (_, base) -> roundedUnitEur(base, conditionFactor) }
    return item.copy(
        valuedUnitEur = valued,
        positionValueEur = valued.mapValues { (_, unit) -> roundedUnitEur(unit * item.quantity) }
    )
}

private fun CollectionItemDto.isValidCollectionItem(): Boolean =
    key.isNotBlank() &&
        key.length <= 100 &&
        cardId.isNotBlank() &&
        languageCode.isNotBlank() &&
        languageCode.length <= 20 &&
        name.isNotBlank() &&
        variant.isNotBlank() &&
        PricingCondition.parse(condition) != null &&
        quantity in 1..100_000
