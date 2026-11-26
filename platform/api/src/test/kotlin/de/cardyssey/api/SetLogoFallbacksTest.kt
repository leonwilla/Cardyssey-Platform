package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class SetLogoFallbacksTest {
    @Test
    fun `fehlendes Logo bekommt Ersatz von der eigenen Seite`() {
        val logo = SetLogoFallbacks.logoOr("me06", null)
        assertTrue(logo!!.endsWith("/set-logos/me06.png"))
        assertTrue(SetLogoFallbacks.logoOr("30th-c", " ")!!.endsWith("/set-logos/30th-c.png"))
    }

    @Test
    fun `vorhandenes Logo bleibt und unbekannte Sets bleiben leer`() {
        assertEquals("https://assets.tcgdex.net/de/me/me05/logo", SetLogoFallbacks.logoOr("me05", "https://assets.tcgdex.net/de/me/me05/logo"))
        assertNull(SetLogoFallbacks.logoOr("unbekannt", null))
    }
}
