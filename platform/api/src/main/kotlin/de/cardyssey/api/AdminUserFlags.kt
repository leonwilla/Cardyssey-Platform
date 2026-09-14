package de.cardyssey.api

fun isRuntimeSmokeBotEmail(email: String): Boolean {
    val normalized = email.trim().lowercase()

    return normalized.startsWith("runtime-smoke-") &&
        normalized.endsWith("@cardyssey.de")
}
