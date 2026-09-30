package de.cardyssey.api

import java.nio.file.Path
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

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
                    mirror.upsertCard(language,
                        CatalogCardSearchResult(card.id, card.localId, card.name, card.setId, card.setName, card.imageBase),
                        Json.encodeToString(card), rarity = "Promo")
                    val source = card.imageBase
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
    println("Anniversary images: downloaded=$downloaded retained=$retained failed=$failures; EN 094–099 still need verified scans")
    check(failures == 0) { "$failures anniversary image downloads failed; rerun to resume" }
}
