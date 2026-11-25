package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class TcgHistoryRangeTest {
    @Test
    fun defaultsToThirtyDays() {
        assertEquals(30, tcgHistoryDays(null))
        assertEquals(30, tcgHistoryDays(""))
    }

    @Test
    fun acceptsOnlyChartRanges() {
        assertEquals(7, tcgHistoryDays("7"))
        assertEquals(365, tcgHistoryDays("365"))
        assertEquals(0, tcgHistoryDays("0"))
        assertNull(tcgHistoryDays("5"))
        assertNull(tcgHistoryDays("-1"))
        assertNull(tcgHistoryDays("abc"))
    }
}
