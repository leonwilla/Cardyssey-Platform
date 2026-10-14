package de.cardyssey.api

import kotlinx.serialization.Serializable

@Serializable
data class VariantSpecDto(
    val id: String,
    val type: String,
    val foil: String? = null,
    val size: String? = null,
    val subtype: String? = null,
    val stamps: List<String> = emptyList()
)

@Serializable
data class CollectionItemDto(
    val id: String? = null,
    val key: String,
    val cardId: String,
    val languageCode: String,
    val name: String,
    val setId: String? = null,
    val setName: String? = null,
    val localId: String? = null,
    val imageBase: String? = null,
    val imageLanguage: String? = null,
    val variant: String,
    val variantSpec: VariantSpecDto? = null,
    val condition: String,
    val quantity: Int,
    val unitEur: Double? = null,
    val unitUsd: Double? = null,
    val marketUnitEur: Map<String, Double> = emptyMap(),
    val marketUpdatedAtMs: Map<String, Long> = emptyMap(),
    val marketSampleCount: Map<String, Int> = emptyMap(),
    // Read model: these values are calculated centrally by Tiny.
    val valuedUnitEur: Map<String, Double> = emptyMap(),
    val positionValueEur: Map<String, Double> = emptyMap(),
    // Informational only. NEVER used by portfolio valuation or sale pricing.
    val referenceUnitEur: Double? = null,
    val referenceSource: String? = null,
    val referenceUpdatedAtMs: Long? = null,
    val referenceNote: String? = null
)

@Serializable
data class CollectionImportResponse(
    val imported: Int,
    val total: Int
)
