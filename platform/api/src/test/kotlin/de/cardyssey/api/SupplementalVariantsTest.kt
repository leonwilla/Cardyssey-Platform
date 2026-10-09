package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class SupplementalVariantsTest {
    private fun card(variants: List<CatalogVariant> = emptyList()) = CatalogCardDetails(
        id="official_ja_test", localId="052", name="Official name", languageCode="ja",
        setId="SV11B", setName="Test", variants=variants
    )

    @Test fun recoveredDefinitionsReachOfficialDetailsWithoutChangingIdentity() {
        val original=card()
        val recovered=recoveredSupplementalVariants(original, """[{"id":"normal","type":"normal","legacyVariant":"NORMAL","extra":"ignored"},{"id":"reverse","type":"reverse","legacyVariant":"REVERSE"}]""")
        assertEquals(listOf("normal", "reverse"),recovered.map { it.id })
        assertEquals("official_ja_test",original.copy(variants=recovered).id)
    }

    @Test fun existingProviderVariantsTakePrecedence() {
        val existing=listOf(CatalogVariant("primary","normal",legacyVariant="NORMAL"))
        assertEquals(existing,recoveredSupplementalVariants(card(existing),"[]"))
    }

    @Test fun malformedIncompleteAndDuplicateDefinitionsFailClosed() {
        for (value in listOf(null,"bad json","[]","[{\"type\":\"normal\"}]",
            "[{\"id\":\"bad\",\"type\":\"unknown\",\"legacyVariant\":\"NORMAL\"}]",
            "[{\"id\":\"same\",\"type\":\"normal\",\"legacyVariant\":\"NORMAL\"},{\"id\":\"same\",\"type\":\"normal\",\"legacyVariant\":\"NORMAL\"}]")) {
            assertTrue(recoveredSupplementalVariants(card(),value).isEmpty())
        }
    }
}
