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
            runAllLanguages()

            delay(
                syncIntervalHours
                    .coerceAtLeast(1L) *
                    60L * 60L * 1000L
            )
        }
    }

    suspend fun runAllLanguages() {
        for (language in languages.distinct()) {
            runLanguage(language)
        }
    }

    private suspend fun runLanguage(language: String) {
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

            mirror.updateStatus(
                language = language,
                status = "running",
                phase = "details"
            )

            syncMissingDetails(language)

            if (imagesEnabled) {
                mirror.updateStatus(
                    language = language,
                    status = "running",
                    phase = "images"
                )

                syncMissingImages(language)
            }

            mirror.updateStatus(
                language = language,
                status = "ready",
                phase = "waiting",
                nextSyncHours =
                    syncIntervalHours
            )
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

    private suspend fun syncMissingDetails(language: String) {
        while (true) {
            val pending =
                mirror.pendingDetails(
                    language = language,
                    limit = detailBatchSize
                )

            if (pending.isEmpty()) {
                return
            }

            var completed = 0

            for (item in pending) {
                val details =
                    runCatching {
                        catalog.details(
                            cardId = item.cardId,
                            language = language
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
                delay(35L)
            }

            if (completed == 0) {
                return
            }
        }
    }

    private suspend fun syncMissingImages(language: String) {
        while (true) {
            val pending =
                mirror.pendingImages(
                    language = language,
                    limit = imageBatchSize
                )

            if (pending.isEmpty()) {
                return
            }

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
                delay(20L)
            }

            if (completed == 0) {
                return
            }
        }
    }
}
