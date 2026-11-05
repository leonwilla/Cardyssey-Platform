package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class DigitalPocketCatalogExclusionTest {
    @Test fun pocketSetsExcludedAcrossCases() {
        listOf("A1", "A1a", "A3", "B2a", "P-A", "p-a").forEach { assertTrue(isDigitalPocketSetId(it), it) }
    }
    @Test fun physicalSetIdsStillAllowed() {
        listOf("base1", "sv01", "ex11", "30th", "bwp", "mep", "sv1a").forEach { assertFalse(isDigitalPocketSetId(it), it) }
    }
}
