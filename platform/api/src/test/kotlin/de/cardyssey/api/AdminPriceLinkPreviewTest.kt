package de.cardyssey.api

import kotlin.test.Test
import kotlin.test.assertNull

class AdminPriceLinkPreviewTest {
    private val preview = AdminPriceLinkPreview()

    @Test fun blocksNonHttpsAndPrivateNetwork() {
        assertNull(preview.preview("http://www.cardmarket.com/Pokemon"))
        assertNull(preview.preview("https://127.0.0.1/internal"))
        assertNull(preview.preview("https://localhost/secrets"))
        assertNull(preview.preview("https://www.cardmarket.com.evil.example/"))
        assertNull(preview.preview("https://user:password@www.tcgplayer.com/"))
    }

    @Test fun blocksUnsupportedProviders() {
        assertNull(preview.preview("https://example.com/card"))
        assertNull(preview.preview("file:///etc/passwd"))
        assertNull(preview.preview("https://169.254.169.254/latest/meta-data"))
    }
}
