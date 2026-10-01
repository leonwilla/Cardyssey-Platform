package de.cardyssey.api

/** Product grouping, not a new physical set: all collection identities remain MEP. */
object AnniversaryPromos {
    const val SET_ID = "30th-promos"
    fun title(language: String) = if (language == "de") "30 Jahre – Promos" else "30th Celebration – Promos"

    // Pokémon's product showcase and official promo legality list, checked 2026-09-29.
    // Only released, numbered product promos. Jumbo/stamped editions are not separate card IDs.
    private val names = listOf(
        Triple("094", "Alola-Kokowei", "Alolan Exeggutor"),
        Triple("095", "Lucario", "Lucario"),
        Triple("096", "Lavados", "Moltres"),
        Triple("097", "Arktos", "Articuno"),
        Triple("098", "Zapdos", "Zapdos"),
        Triple("099", "Quajutsu-ex", "Greninja ex"),
        Triple("100", "Feelinara-ex", "Sylveon ex"),
        Triple("101", "Nidorina", "Nidorina")
    )

    fun cards(language: String): List<CatalogCardDetails> {
        if (language !in setOf("de", "en")) return emptyList()
        return names.map { (number, german, english) ->
            val image = when {
                language == "de" ->
                    "https://pokezentrum.de/wp-content/uploads/$german-MEP-$number-30-Jahre-Promo-Pokemon-Karte-Deutsch-430x600.jpg"

                number in setOf("100", "101") ->
                    "https://www.pokemon.com/static-assets/content-assets/cms2/img/cards/web/MEP/MEP_EN_$number.png"

                /*
                 * TCGdex still has no image field for these newly released
                 * English promos. Limitless exposes the actual English MEP
                 * print scans under stable card-number URLs; the Tiny mirrors
                 * them locally on the first repair/sync run.
                 */
                language == "en" &&
                    number in setOf(
                        "094",
                        "095",
                        "096",
                        "097",
                        "098",
                        "099"
                    ) ->
                    "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/tpci/MEP/MEP_${number}_R_EN.png"

                else ->
                    null
            }
            CatalogCardDetails(
                id = "mep-$number", localId = number,
                name = if (language == "de") german.replace("-ex", " ex") else english,
                languageCode = language, imageBase = image,
                imageLanguage = if (image != null) language else null,
                setId = "mep", setName = "MEP Black Star Promos", rarity = "Promo",
                variants = listOf(CatalogVariant(id = "legacy:holo", type = "Holo", legacyVariant = "HOLO"))
            )
        }
    }

    fun summary(language: String): CatalogSetSummary? = cards(language).takeIf { it.isNotEmpty() }?.let {
        CatalogSetSummary(SET_ID, title(language), totalCount = it.size)
    }
}
