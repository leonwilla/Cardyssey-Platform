package de.cardyssey.api

import kotlinx.coroutines.CancellationException
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

    private val detailCursors = mutableMapOf<String, String>()
    private val imageCursors = mutableMapOf<String, String>()
    private val failures = mutableMapOf<String, String>()

    private fun recordFailure(language: String, error: Throwable) {
        if (error is CancellationException) throw error
        failures[language] = (error.message ?: error::class.java.simpleName).take(1000)
    }

    suspend fun runForever() {
        while (true) {
            val completed =
                runCatching {
                    runAllLanguages()
                }
                    .onFailure { error ->
                        if (error is CancellationException) throw error
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
        detailCursors.clear()
        imageCursors.clear()
        failures.clear()
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
         * restart-safe: unchanged completed files are retained. Changed image
         * URLs are invalidated by the repository and downloaded again.
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
                status = if (language in failures) "partial" else "ready",
                phase = "waiting",
                error = failures[language],
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
            recordFailure(language, error)
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
                limit = detailBatchSize,
                afterCardId = detailCursors[language]
            )

        if (pending.isEmpty()) return false

        for (item in pending) {
            detailCursors[language] = item.cardId
            val details =
                runCatching {
                    catalog.details(
                        cardId = item.cardId,
                        language = language,
                        forceRemote = true
                    )
                }
                    .onFailure { recordFailure(language, it) }
                    .getOrNull()
            if (details == null || details.languageCode != language) {
                failures[language] = "Missing or wrong-language details: ${item.cardId}/$language"
                delay(100L)
                continue
            }

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

            /* Respect the upstream service while the initial import runs. */
            delay(100L)
        }

        return true
    }

    private suspend fun syncImagesBatch(language: String): Boolean {
        val pending =
            mirror.pendingImages(
                language = language,
                limit = imageBatchSize,
                afterCardId = imageCursors[language]
            )

        if (pending.isEmpty()) return false

        for (item in pending) {
            imageCursors[language] = item.cardId
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
                    .onFailure { recordFailure(language, it) }
                    .getOrNull()
            if (downloaded == null) {
                delay(50L)
                continue
            }

            mirror.completeImage(
                language = language,
                cardId = item.cardId,
                path = destination,
                hash = downloaded.first,
                byteCount = downloaded.second
            )

            delay(50L)
        }

        return true
    }

}
