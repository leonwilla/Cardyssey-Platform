package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class AnniversaryPromosTest {
    @Test fun productViewKeepsPhysicalPromoIdentities() = runBlocking {
        HikariDataSource().use { database ->
            val service = CardCatalogService(CatalogCacheRepository(database))
            val set = service.setDetails("30th-promos", "de")!!
            assertEquals(8, set.totalCount)
            assertEquals((94..101).map { "mep-" + it.toString().padStart(3, '0') }, set.cards.map { it.id })
            assertEquals("Nidorina", set.cards.last().name)
            assertFalse(set.cards.any { it.id == "mep-030" })
            assertNull(service.setDetails("30th-promos", "ja"))
        }
    }

    @Test fun imagesUseTheirActualLanguageAndMissingScansStayMissing() {
        val german = AnniversaryPromos.cards("de")
        assertEquals(8, german.size)
        german.forEach {
            assertEquals("mep", it.setId)
            assertEquals("de", it.imageLanguage)
            assertTrue(it.imageBase!!.contains("MEP-${it.localId}"))
            assertTrue(it.imageBase!!.contains("Deutsch"))
        }
        val english = AnniversaryPromos.cards("en")
        assertEquals(8, english.count { it.imageBase != null })
        english.forEach {
            assertEquals("en", it.imageLanguage)
            assertTrue(
                it.imageBase!!.contains(
                    "MEP_${it.localId}_R_EN.png"
                ) ||
                    it.localId in setOf(
                        "100",
                        "101"
                    )
            )
        }
        assertEquals(emptyList<CatalogCardDetails>(), AnniversaryPromos.cards("ko"))
    }
}
