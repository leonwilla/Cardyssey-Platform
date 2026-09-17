package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class EbaySoldStatusClassifierTest {
    @Test
    fun soldListingMayAlsoContainGenericEndedText() {
        val german =
            "Verkauft 15. Sep 2026. Das Angebot ist beendet."

        assertTrue(
            ebayTextHasExplicitSoldStatus(
                german
            )
        )
        assertFalse(
            ebayTextIsExplicitlyEndedWithoutSale(
                german
            )
        )
    }

    @Test
    fun foreignSoldListingMayAlsoContainGenericEndedText() {
        val english =
            "SOLD Sep 15 2026. This listing has ended."

        assertTrue(
            ebayTextHasExplicitSoldStatus(
                english
            )
        )
        assertFalse(
            ebayTextIsExplicitlyEndedWithoutSale(
                english
            )
        )
    }

    @Test
    fun sellerEndedGermanListingIsNotASale() {
        val text =
            "Dieses Angebot wurde vom Verkäufer am 31. Aug um 01:22 beendet, " +
                "da der Artikel nicht mehr verfügbar ist."

        assertFalse(
            ebayTextHasExplicitSoldStatus(
                text
            )
        )
        assertTrue(
            ebayTextIsExplicitlyEndedWithoutSale(
                text
            )
        )
    }

    @Test
    fun sellerEndedEnglishListingIsNotASale() {
        val text =
            "This listing was ended by the seller because the item is no longer available."

        assertFalse(
            ebayTextHasExplicitSoldStatus(
                text
            )
        )
        assertTrue(
            ebayTextIsExplicitlyEndedWithoutSale(
                text
            )
        )
    }
}
