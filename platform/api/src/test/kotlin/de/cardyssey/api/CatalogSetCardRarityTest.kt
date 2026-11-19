package de.cardyssey.api

import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class CatalogSetCardRarityTest {
    @Test
    fun `older set cards without rarity remain readable`() {
        val card = Json.decodeFromString<CatalogSetCard>(
            """{"id":"base1-8","localId":"8","name":"Machamp"}"""
        )
        assertNull(card.rarity)
    }

    @Test
    fun `localized catalog rarity is preserved in the set response`() {
        val card = CatalogSetCard("base1-8", "8", "Machomei", rarity = "Holografisch Selten")
        assertEquals(card, Json.decodeFromString<CatalogSetCard>(Json.encodeToString(card)))
    }
}
