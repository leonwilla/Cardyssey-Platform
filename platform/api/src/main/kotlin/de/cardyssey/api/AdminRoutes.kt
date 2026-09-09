package de.cardyssey.api

import io.ktor.http.HttpStatusCode
import io.ktor.server.application.ApplicationCall
import io.ktor.server.application.call
import io.ktor.server.auth.authenticate
import io.ktor.server.request.queryParameters
import io.ktor.server.response.respond
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.route
import java.util.UUID

fun Route.adminRoutes(
    roles: RoleRepository,
    admin: AdminRepository,
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
