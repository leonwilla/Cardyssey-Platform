package de.cardyssey.api

import java.time.OffsetDateTime
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class TcgPriceRefreshWindowTest {
    @Test fun onlySundayWeeklyLaneAllowsExistingPrices() {
        for (stamp in listOf(
            "2026-10-10T17:00:00Z", "2026-10-11T04:16:59Z",
            "2026-10-12T00:00:00Z", "2026-10-14T04:17:00Z"
        )) assertFalse(weeklyPriceRefreshAllowed(OffsetDateTime.parse(stamp)), stamp)
        for (stamp in listOf("2026-10-11T04:17:00Z", "2026-10-11T23:59:59Z"))
            assertTrue(weeklyPriceRefreshAllowed(OffsetDateTime.parse(stamp)), stamp)
    }

    @Test fun scheduleUsesUTCRatherThanClientOffset() {
        assertFalse(weeklyPriceRefreshAllowed(OffsetDateTime.parse("2026-10-11T06:16:59+02:00")))
        assertTrue(weeklyPriceRefreshAllowed(OffsetDateTime.parse("2026-10-11T06:17:00+02:00")))
        assertFalse(weeklyPriceRefreshAllowed(OffsetDateTime.parse("2026-10-12T02:00:00+02:00")))
    }
}
