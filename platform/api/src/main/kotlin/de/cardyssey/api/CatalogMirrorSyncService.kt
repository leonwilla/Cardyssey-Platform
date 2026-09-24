package de.cardyssey.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

class CatalogMirrorSyncService(
    private val catalog: CardCatalogService,
    private val mirror: PermanentCatalogRepository,
    private val images: CatalogImageHasher,
    private val languages: List<String>,
    private val syncIntervalHours: Long,
    private val detailBatchSize: Int,
    private val imageBatchSize: Int,
    private val imagesEnabled: Boolean
) {
    private val json =
        Json {
            encodeDefaults = true
            ignoreUnknownKeys = true
        }

    suspend fun runForever() {
        while (true) {
            val completed =
                runCatching {
                    runAllLanguages()
                }
                    .onFailure { error ->
                        println(
                            "Catalog mirror cycle failed: " +
                                (error.message
                                    ?: error::class.java.simpleName)
                        )
                    }
                    .isSuccess

            val waitMs =
                if (completed) {
                    syncIntervalHours
                        .coerceAtLeast(1L) *
                        60L * 60L * 1000L
                } else {
                    15L * 60L * 1000L
                }

            delay(waitMs)
        }
    }

    suspend fun runAllLanguages() {
        val activeLanguages = languages.distinct()

        /*
         * Index every language first. A very large German or English image
         * import must not prevent newer Japanese/Korean/Chinese sets from
         * becoming searchable for hours or days.
         */
        for (language in activeLanguages) {
            indexLanguage(language)
        }

        /*
         * Materialise one batch per language in a round-robin. The process is
         * restart-safe: completed rows and files are never downloaded again.
         */
        while (true) {
            var progressed = false

            for (language in activeLanguages) {
                mirror.updateStatus(language, "running", "details")
                progressed = syncDetailsBatch(language) || progressed

                if (imagesEnabled) {
                    mirror.updateStatus(language, "running", "images")
                    progressed = syncImagesBatch(language) || progressed
                }
            }

            if (!progressed) break
        }

        activeLanguages.forEach { language ->
            mirror.updateStatus(
                language = language,
                status = "ready",
                phase = "waiting",
                nextSyncHours = syncIntervalHours
            )
        }
    }

    private suspend fun indexLanguage(language: String) {
        mirror.updateStatus(
            language = language,
            status = "running",
            phase = "index"
        )

        runCatching {
            val snapshot =
                catalog.refreshSourceIndex(language)

            snapshot.sets.forEach { set ->
                mirror.upsertSet(
                    language = language,
                    set = set,
                    rawPayload =
                        json.encodeToString(set)
                )
            }

            snapshot.cards.forEach { card ->
                mirror.upsertCard(
                    language = language,
                    card = card,
                    rawPayload =
                        json.encodeToString(card)
                )
            }

        }.onFailure { error ->
            mirror.updateStatus(
                language = language,
                status = "error",
                phase = "waiting",
                error =
                    error.message
                        ?.take(1000)
                        ?: error::class.java.simpleName,
                nextSyncHours = 1L
            )
        }
    }

    private suspend fun syncDetailsBatch(language: String): Boolean {
        val pending =
            mirror.pendingDetails(
                language = language,
                limit = detailBatchSize
            )

        if (pending.isEmpty()) return false

        var completed = 0

        for (item in pending) {
            val details =
                runCatching {
                    catalog.details(
                        cardId = item.cardId,
                        language = language,
                        forceRemote = true
                    )
                }
                    .getOrNull()
                    ?: continue

            val card =
                CatalogCardSearchResult(
                    id = details.id,
                    localId = details.localId,
                    name = details.name,
                    setId = details.setId,
                    setName = details.setName,
                    imageBase = details.imageBase
                )

            mirror.upsertCard(
                language = language,
                card = card,
                rarity = details.rarity,
                variantsJson =
                    json.encodeToString(
                        details.variants
                    ),
                rawPayload =
                    json.encodeToString(details),
                detailsComplete = true
            )

            completed += 1

            /* Respect the upstream service while the initial import runs. */
            delay(100L)
        }

        return completed > 0
    }

    private suspend fun syncImagesBatch(language: String): Boolean {
        val pending =
            mirror.pendingImages(
                language = language,
                limit = imageBatchSize
            )

        if (pending.isEmpty()) return false

        var completed = 0

        for (item in pending) {
            val source =
                item.sourceUrl
                    ?.takeIf(String::isNotBlank)
                    ?: continue

            val destination =
                mirror.imagePath(
                    language = language,
                    cardId = item.cardId
                )

            val downloaded =
                runCatching {
                    withContext(Dispatchers.IO) {
                        images.downloadAndHash(
                            imageBase = source,
                            destination = destination
                        )
                    }
                }
                    .getOrNull()
                    ?: continue

            mirror.completeImage(
                language = language,
                cardId = item.cardId,
                path = destination,
                hash = downloaded.first,
                byteCount = downloaded.second
            )

            completed += 1
            delay(50L)
        }

        return completed > 0
    }

}
