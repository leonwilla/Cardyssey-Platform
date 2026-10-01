package de.cardyssey.api

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.nio.file.Path
import java.time.Duration
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive


private val repairHttp =
    HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(10))
        .followRedirects(HttpClient.Redirect.NORMAL)
        .build()

private fun tcgDexEnglishImage(cardId: String): String? =
    runCatching {
        val request =
            HttpRequest.newBuilder()
                .uri(URI.create("https://api.tcgdex.net/v2/en/cards/$cardId"))
                .timeout(Duration.ofSeconds(20))
                .header("Accept", "application/json")
                .header("User-Agent", "Cardyssey-AnniversaryRepair/1.0")
                .GET()
                .build()

        val response =
            repairHttp.send(
                request,
                HttpResponse.BodyHandlers.ofString()
            )

        if (response.statusCode() !in 200..299) return@runCatching null

        Json.parseToJsonElement(response.body())
            .jsonObject["image"]
            ?.jsonPrimitive
            ?.content
            ?.takeIf { it.isNotBlank() }
    }.getOrNull()

/** Idempotent Tiny backfill; no collection rows or physical card identities are changed. */
fun main() {
    var failures = 0
    var downloaded = 0
    var retained = 0
    createDataSource().use { database ->
        val mirror = PermanentCatalogRepository(database,
            Path.of(System.getenv("CATALOG_DIR") ?: "/data/catalog"),
            System.getenv("PUBLIC_API_URL") ?: "https://api.cardyssey.de")
        val hasher = CatalogImageHasher()
        for (language in listOf("de", "en")) {
            for (card in AnniversaryPromos.cards(language)) {
                try {
                    // Seed missing metadata, but never overwrite existing priced print variants.
                    val source =
                        card.imageBase
                            ?: if (language == "en") tcgDexEnglishImage(card.id) else null

                    mirror.upsertCard(
                        language,
                        CatalogCardSearchResult(
                            card.id,
                            card.localId,
                            card.name,
                            card.setId,
                            card.setName,
                            source
                        ),
                        Json.encodeToString(card.copy(imageBase = source, imageLanguage = if (source != null) language else null)),
                        rarity = "Promo"
                    )
                    if (source == null) {
                        println("GAP: $language ${card.id}: no verified image source yet")
                        continue
                    }
                    if (mirror.hasImageSource(language, card.id, source)) {
                        retained++
                        continue
                    }
                    val destination = mirror.imagePath(language, card.id)
                    var lastError: Exception? = null
                    for (attempt in 1..3) {
                        try {
                            val (hash, bytes) = hasher.downloadAndHash(source, destination)
                            mirror.completeImage(language, card.id, destination, hash, bytes)
                            check(mirror.hasImageSource(language, card.id, source))
                            println("OK: $language ${card.id}: $bytes bytes, image and fingerprint stored")
                            downloaded++
                            lastError = null
                            break
                        } catch (error: Exception) {
                            lastError = error
                            if (attempt < 3) Thread.sleep(attempt * 2_000L)
                        }
                    }
                    if (lastError != null) throw lastError
                } catch (error: Exception) {
                    failures++
                    System.err.println("FAIL: $language ${card.id}: ${error.message}")
                }
            }
        }
    }
    println("Anniversary images: downloaded=$downloaded retained=$retained failed=$failures; unresolved EN images stay visible as GAP entries")
    check(failures == 0) { "$failures anniversary image downloads failed; rerun to resume" }
}
