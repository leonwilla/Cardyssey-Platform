package de.cardyssey.api

import io.ktor.server.application.ApplicationCall
import io.ktor.server.auth.jwt.JWTPrincipal
import io.ktor.server.auth.principal
import java.util.UUID

fun ApplicationCall.authenticatedUserId(): UUID? =
    principal<JWTPrincipal>()
        ?.payload
        ?.subject
        ?.let { subject ->
            runCatching {
                UUID.fromString(subject)
            }.getOrNull()
        }
