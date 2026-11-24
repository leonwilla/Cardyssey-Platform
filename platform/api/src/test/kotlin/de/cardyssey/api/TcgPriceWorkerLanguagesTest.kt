package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class TcgPriceWorkerLanguagesTest {
    @Test
    fun workerSkipsGermanAndEnglish() {
        assertEquals(
            listOf("ko", "ja", "zh-tw", "zh-cn"),
            workerPriceLanguages(listOf("de", "en", "ko", "ja", "zh-tw", "zh-cn"))
        )
    }

    @Test
    fun tcgdexIsRetiredAsPriceSource() {
        assertTrue(isRetiredPriceSource("TCGDEX"))
        assertTrue(isRetiredPriceSource("TCGDEX_SHARED_HOLO"))
        assertFalse(isRetiredPriceSource("CARDMARKET_GUIDE"))
        assertFalse(isRetiredPriceSource(null))
    }
}
