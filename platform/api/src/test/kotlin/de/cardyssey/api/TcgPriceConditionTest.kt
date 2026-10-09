package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class TcgPriceConditionTest {
    @Test fun singleOfferRangeEqualsConditionAdjustedCardValue() {
        val statistics = TcgPriceStatistics(5.2109, 5.2109, 12.0)
        for (condition in PricingCondition.entries) {
            val result = statistics.forCondition(condition)
            assertEquals(roundedUnitEur(5.2109, condition.factor), result.lowEur)
            assertEquals(result.lowEur, result.highEur)
            assertEquals(12.0, result.trend30dPercent)
        }
        assertEquals(4.79, statistics.forCondition(PricingCondition.NEAR_MINT).lowEur)
        assertEquals(5.2109, statistics.lowEur)
    }

    @Test fun historicalRangeUsesTheSameConditionAndCentRounding() {
        val result = TcgPriceStatistics(1.005, 10.005, -20.0).forCondition(PricingCondition.GOOD)
        assertEquals(0.65, result.lowEur)
        assertEquals(6.50, result.highEur)
        assertEquals(-20.0, result.trend30dPercent)
    }

    @Test fun missingHistoryRemainsMissing() {
        val result = TcgPriceStatistics(null, null, null).forCondition(PricingCondition.PLAYED)
        assertNull(result.lowEur)
        assertNull(result.highEur)
        assertNull(result.trend30dPercent)
    }
}
