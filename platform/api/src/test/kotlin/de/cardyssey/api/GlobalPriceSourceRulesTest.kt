package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertEquals

class GlobalPriceSourceRulesTest {
    @Test fun commonAndUncommonAreBulkAcrossLocales() {
        for (rarity in listOf("Häufig", "Ungewöhnlich", "COMMON", "Uncommon", "C", "U", "rare_c", "rare_u", "rare_c_c", "rare_u_c", "One Diamond", "Two Diamond", "Une Diamant", "Deux Diamant")) {
            assertEquals("BULK", GlobalPriceSourceRules.priceClass(rarity))
            for (language in GlobalPriceSourceRules.supportedLanguages)
                assertEquals("TCG", GlobalPriceSourceRules.preferredMarket(language, rarity))
        }
    }

    @Test fun specialCardsUseEbayOnlyWhenMarketIsSupported() {
        assertEquals("EBAY", GlobalPriceSourceRules.preferredMarket("de", "Selten"))
        assertEquals("EBAY", GlobalPriceSourceRules.preferredMarket("en", "Rare"))
        for (language in listOf("ja", "ko", "zh-cn", "zh-tw"))
            assertEquals("LOCAL_MARKET", GlobalPriceSourceRules.preferredMarket(language, "Rare"))
    }

    @Test fun unknownRarityIsNeverGuessedAsBulk() {
        for (rarity in listOf(null, "", "  ", "None", "Keine", "Unbekannt")) {
            assertEquals("RARITY_UNVERIFIED", GlobalPriceSourceRules.priceClass(rarity))
            assertEquals("LOCAL_MARKET", GlobalPriceSourceRules.preferredMarket("de", rarity))
        }
    }
}
