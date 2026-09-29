package de.cardyssey.api

import java.math.BigDecimal
import java.math.RoundingMode

/** Round the displayed unit first, so quantity times unit equals the position value. */
internal fun roundedUnitEur(base: Double, factor: Double = 1.0): Double =
    BigDecimal.valueOf(base).multiply(BigDecimal.valueOf(factor))
        .setScale(2, RoundingMode.HALF_UP).toDouble()
