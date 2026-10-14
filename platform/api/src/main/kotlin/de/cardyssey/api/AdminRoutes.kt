package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.ApplicationCall
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.delete
import io.ktor.server.routing.get
import io.ktor.server.routing.put
import io.ktor.server.routing.route
import java.util.UUID

fun Route.adminRoutes(
    roles: RoleRepository,
    admin: AdminRepository,
    priceMonitor: AdminPriceMonitorRepository,
    priceReview: AdminPriceReviewRepository,
    priceCoverage: AdminPriceCoverageRepository,
    userManagement: AdminUserManagementRepository,
    registrationSettings: RegistrationSettingsRepository,
    justTcgConfigured: Boolean,
    soldCompsConfigured: Boolean
) {
    authenticate("auth-jwt") {
        route("/api/v1/admin") {

            get("/access") {
                val userId = call.authenticatedUserId()

                if (userId == null) {
                    call.respond(HttpStatusCode.Unauthorized)
                    return@get
                }

                val access = roles.accessFor(userId)

                if (access == null) {
                    call.respond(HttpStatusCode.Unauthorized)
                    return@get
                }

                call.respond(access)
            }

            get("/overview") {
                if (!call.requireAdmin(roles)) {
                    return@get
                }

                call.respond(admin.overview())
            }

            get("/price-monitor") {
                if (!call.requireAdmin(roles)) {
                    return@get
                }

                call.respond(
                    priceMonitor.openCases(
                        language = call.request.queryParameters["language"],
                        status = call.request.queryParameters["status"]
                    )
                )
            }

            get("/price-review") {
                if (!call.requireAdmin(roles)) return@get
                call.respond(priceReview.list(call.request.queryParameters["language"]?.takeIf { it in setOf("de","en","ko","ja","zh-tw","zh-cn") }))
            }

            get("/price-coverage") {
                if (!call.requireAdmin(roles)) return@get
                val language = call.request.queryParameters["language"]?.trim()?.lowercase()?.takeIf { it.isNotBlank() && it != "all" }
                if (language != null && language !in AdminPriceCoverageRepository.languages) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_language"))
                    return@get
                }
                call.respond(priceCoverage.overview(language))
            }

            get("/price-coverage/cards") {
                if (!call.requireAdmin(roles)) return@get
                val language = call.request.queryParameters["language"]?.trim()?.lowercase()
                val setId = call.request.queryParameters["setId"]?.trim()
                val rawOffset = call.request.queryParameters["offset"]
                val offset = if (rawOffset == null) 0 else rawOffset.toIntOrNull()
                if (language !in AdminPriceCoverageRepository.languages || setId.isNullOrBlank() || setId.length > 160 || offset == null || offset < 0) {
                    call.respond(HttpStatusCode.BadRequest, mapOf("error" to "invalid_coverage_filter"))
                    return@get
                }
                call.respond(priceCoverage.cards(language!!, setId, offset))
            }

            get("/users") {
                if (!call.requireAdmin(roles)) {
                    return@get
                }

                call.respond(
                    admin.users(
                        call.request.queryParameters["q"]
                    )
                )
            }

            get("/users/{id}") {
                if (!call.requireAdmin(roles)) {
                    return@get
                }

                val userId =
                    call.parameters["id"]
                        ?.let {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }

                if (userId == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_user_id")
                    )
                    return@get
                }

                val detail = admin.user(userId)

                if (detail == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf("error" to "user_not_found")
                    )
                    return@get
                }

                call.respond(detail)
            }

            get("/users/{id}/duplicates") {
                if (!call.requireAdmin(roles)) {
                    return@get
                }

                val userId =
                    call.parameters["id"]
                        ?.let {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }

                if (userId == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_user_id")
                    )
                    return@get
                }

                if (admin.user(userId) == null) {
                    call.respond(
                        HttpStatusCode.NotFound,
                        mapOf("error" to "user_not_found")
                    )
                    return@get
                }

                call.respond(
                    admin.duplicates(userId)
                )
            }

            delete("/users/{id}") {
                val actorUserId = call.authenticatedUserId()

                if (actorUserId == null) {
                    call.respond(HttpStatusCode.Unauthorized)
                    return@delete
                }

                if (!call.requireFounder(roles)) {
                    return@delete
                }

                val userId =
                    call.parameters["id"]
                        ?.let {
                            runCatching {
                                UUID.fromString(it)
                            }.getOrNull()
                        }

                if (userId == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "invalid_user_id")
                    )
                    return@delete
                }

                when (
                    userManagement.deleteUser(
                        userId = userId,
                        actorUserId = actorUserId
                    )
                ) {
                    AdminDeleteUserResult.DELETED ->
                        call.respond(
                            HttpStatusCode.OK,
                            mapOf(
                                "deleted" to true,
                                "id" to userId.toString()
                            )
                        )

                    AdminDeleteUserResult.NOT_FOUND ->
                        call.respond(
                            HttpStatusCode.NotFound,
                            mapOf("error" to "user_not_found")
                        )

                    AdminDeleteUserResult.SELF_FORBIDDEN ->
                        call.respond(
                            HttpStatusCode.Conflict,
                            mapOf("error" to "cannot_delete_self")
                        )

                    AdminDeleteUserResult.FOUNDER_FORBIDDEN ->
                        call.respond(
                            HttpStatusCode.Forbidden,
                            mapOf("error" to "cannot_delete_founder")
                        )

                    AdminDeleteUserResult.SYSTEM_BOT_FORBIDDEN ->
                        call.respond(
                            HttpStatusCode.Conflict,
                            mapOf("error" to "cannot_delete_system_bot")
                        )
                }
            }

            get("/registration") {
                if (!call.requireFounder(roles)) {
                    return@get
                }

                call.respond(
                    registrationSettings.get()
                )
            }

            put("/registration") {
                if (!call.requireFounder(roles)) {
                    return@put
                }

                val request =
                    call.receive<UpdateRegistrationSettingsRequest>()

                call.respond(
                    registrationSettings.setRegistrationsEnabled(
                        request.enabled
                    )
                )
            }

            get("/system") {
                if (!call.requireFounder(roles)) {
                    return@get
                }

                call.respond(
                    admin.system(
                        justTcgConfigured = justTcgConfigured,
                        soldCompsConfigured = soldCompsConfigured
                    )
                )
            }
        }
    }
}

private suspend fun ApplicationCall.requireAdmin(
    roles: RoleRepository
): Boolean {
    val userId = authenticatedUserId()

    if (userId == null) {
        respond(HttpStatusCode.Unauthorized)
        return false
    }

    val role = roles.roleFor(userId)

    if (role == null) {
        respond(HttpStatusCode.Unauthorized)
        return false
    }

    if (!role.canAdmin) {
        respond(
            HttpStatusCode.Forbidden,
            mapOf("error" to "admin_required")
        )
        return false
    }

    return true
}

private suspend fun ApplicationCall.requireFounder(
    roles: RoleRepository
): Boolean {
    val userId = authenticatedUserId()

    if (userId == null) {
        respond(HttpStatusCode.Unauthorized)
        return false
    }

    val role = roles.roleFor(userId)

    if (role == null) {
        respond(HttpStatusCode.Unauthorized)
        return false
    }

    if (!role.canFounder) {
        respond(
            HttpStatusCode.Forbidden,
            mapOf("error" to "founder_required")
        )
        return false
    }

    return true
}
