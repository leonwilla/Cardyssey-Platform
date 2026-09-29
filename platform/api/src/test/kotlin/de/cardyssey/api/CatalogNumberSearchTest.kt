package de.cardyssey.api

import com.zaxxer.hikari.HikariDataSource
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class CatalogNumberSearchTest {
    // Seed the normal in-memory cache: no external API or production database in regression tests.
    private fun seed(service: CardCatalogService, field: String, value: Any) {
        val entry = Class.forName("de.cardyssey.api.CacheEntry").declaredConstructors.first()
            .apply { isAccessible = true }.newInstance(value, Long.MAX_VALUE)
        @Suppress("UNCHECKED_CAST")
        val cache = service.javaClass.getDeclaredField(field).apply { isAccessible = true }
            .get(service) as MutableMap<String, Any>
        cache["de"] = entry
    }

    @Test fun denominatorIsFilteredBeforeLimitAndSecretsMayExceedTotal() = runBlocking {
        HikariDataSource().use { dataSource ->
            val service = CardCatalogService(CatalogCacheRepository(dataSource))
            val brief = Class.forName("de.cardyssey.api.BriefCard").declaredConstructors.first()
                .apply { isAccessible = true }
            val cards = (1..80).map { brief.newInstance("wrong$it-136", "136", "A", null) } + listOf(
                brief.newInstance("sv09-136", "136", "Hops Zwollock", null),
                brief.newInstance("pbl-115", "115", "Mega Chandelure ex", null)
            )
            seed(service, "cardsCache", cards)
            seed(service, "setsCache", mapOf("sv09" to "Reisegefährten", "pbl" to "Pitch Black"))
            seed(service, "setSummaryCache", listOf(
                CatalogSetSummary("sv09", "Reisegefährten", officialCount = 159),
                CatalogSetSummary("pbl", "Pitch Black", officialCount = 84)
            ))
            assertEquals(listOf("sv09-136"), service.search("", "136/159", "de", 1).map { it.id })
            assertEquals(listOf("pbl-115"), service.search("", "115/084", "de", 1).map { it.id })
            assertEquals(81, service.search("", "136", "de", 250).size)
            assertTrue(service.search("", "136/999", "de", 250).isEmpty())
        }
    }

    @Test fun unitCentsAgreeWithQuantity() {
        assertEquals(0.05, roundedUnitEur(0.05, 0.92), 0.000001)
        assertEquals(0.20, roundedUnitEur(roundedUnitEur(0.05, 0.92) * 4), 0.000001)
        assertEquals(1.01, roundedUnitEur(1.005), 0.000001)
    }
}
