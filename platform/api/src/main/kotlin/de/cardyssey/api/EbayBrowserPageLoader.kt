package de.cardyssey.api

import org.openqa.selenium.chrome.ChromeOptions
import org.openqa.selenium.remote.RemoteWebDriver
import java.net.URI
import java.time.Duration

data class EbayBrowserPage(
    val url: String,
    val html: String
)

/**
 * Sichtbarer Test-Browser auf dem Tiny.
 *
 * Challenges werden niemals automatisch umgangen. Der Browser bleibt auf der
 * eBay-Seite stehen, damit der Betreiber sie über die lokale noVNC-Oberfläche
 * selbst bestätigen kann. Anschließend wird dieselbe persistente Sitzung für
 * weitere, streng serielle Preisabfragen wiederverwendet.
 */
class EbayBrowserPageLoader(
    private val remoteUrl: String
) {
    private var driver: RemoteWebDriver? = null

    @Synchronized
    fun load(
        url: String
    ): EbayBrowserPage {
        val active =
            driver ?: createDriver()
                .also {
                    driver = it
                }

        return try {
            active.get(url)
            Thread.sleep(PAGE_SETTLE_MS)

            EbayBrowserPage(
                url = active.currentUrl,
                html = active.pageSource
            )
        } catch (error: Exception) {
            runCatching {
                active.quit()
            }
            driver = null
            throw error
        }
    }

    private fun createDriver():
        RemoteWebDriver {
        val options =
            ChromeOptions().apply {
                addArguments(
                    "--lang=de-DE",
                    "--window-size=1440,1200",
                    "--user-data-dir=/home/seluser/.config/chromium/cardyssey"
                )
            }

        return RemoteWebDriver(
            URI.create(remoteUrl).toURL(),
            options
        ).apply {
            manage()
                .timeouts()
                .pageLoadTimeout(
                    Duration.ofSeconds(60)
                )
        }
    }

    companion object {
        private const val PAGE_SETTLE_MS =
            3_000L
    }
}
