package de.cardyssey.api

/**
 * Ersatz-Logos für Sets, für die TCGdex in keiner Sprache ein Logo liefert
 * (z. B. neue Sets wie „Delta-Herrschaft“ oder Untersets wie Trainer-Galerien).
 *
 * Die Bilder liegen auf der eigenen Webseite unter `web/public/set-logos/<id>.png`,
 * damit App und Web nicht von fremden Bildservern abhängen.
 */
internal object SetLogoFallbacks {
    private val ids = setOf(
        "2011bw", "2012bw", "2014xy", "2015xy", "2016xy", "2017sm", "2018sm", "2019sm",
        "2021swsh", "2022swsh", "30th", "30th-c", "cel25cc", "exu", "me06", "mee", "mep",
        "rc", "sm3.5", "sm7.5", "sma", "sv05", "sve", "svp", "swsh10tg", "swsh11tg",
        "swsh12.5gg", "swsh12tg", "swsh4.5sv", "swsh9tg"
    )

    private val baseUrl: String =
        (System.getenv("PUBLIC_WEB_URL")?.takeIf(String::isNotBlank) ?: "https://cardyssey.de").trimEnd('/')

    fun logoFor(setId: String): String? =
        setId.trim().lowercase().takeIf { it in ids }?.let { "$baseUrl/set-logos/$it.png" }

    /** Vorhandenes Logo behalten, sonst Ersatz-Logo verwenden. */
    fun logoOr(setId: String, logo: String?): String? =
        logo?.takeIf(String::isNotBlank) ?: logoFor(setId)
}
