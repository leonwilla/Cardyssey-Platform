package de.cardyssey.api

import kotlinx.serialization.Serializable

@Serializable
data class CardPriceQuoteResponse(
    val cardId: String,
    val languageCode: String,
    val variantId: String?,
    val variantType: String?,
    val condition: String,
    val market: String,
    val source: String?,
    val baseEur: Double?,
    val conditionFactor: Double,
    val eur: Double?,
    val exactLanguageMatch: Boolean,
    val exactVariantMatch: Boolean
)

enum class PricingCondition(
    val factor: Double
) {
    MINT(1.00),
    NEAR_MINT(0.92),
    EXCELLENT(0.80),
    GOOD(0.65),
    PLAYED(0.45);

    companion object {
        fun parse(
            raw: String?
        ): PricingCondition? {
            if (raw.isNullOrBlank()) {
                return NEAR_MINT
            }

            return entries.firstOrNull {
                it.name.equals(
                    raw.trim(),
                    ignoreCase = true
                )
            }
        }
    }
}

private data class CentralProviderQuote(
    val source: String,
    val baseEur: Double
)

private interface CentralPricingProvider {
    suspend fun quote(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): CentralProviderQuote?
}

/**
 * Erster zentraler Provider.
 *
 * Weitere Quellen wie JustTCG oder SoldComps werden künftig hier
 * serverseitig als zusätzliche Provider ergänzt. Web und Android
 * müssen dafür nicht geändert werden.
 */
private class TcgDexCentralPricingProvider :
    CentralPricingProvider {

    override suspend fun quote(
        card: CatalogCardDetails,
        variant: CatalogVariant
    ): CentralProviderQuote? {
        val baseEur =
            variant.tcgDexEur
                ?.takeIf {
                    it.isFinite() &&
                        it > 0.0
                }
                ?: return null

        return CentralProviderQuote(
            source = "TCGDEX",
            baseEur = baseEur
        )
    }
}

class CardPricingService(
    private val catalog: CardCatalogService,
    private val providers:
        List<CentralPricingProvider> =
        listOf(
            TcgDexCentralPricingProvider()
        )
) {
    suspend fun quote(
        cardId: String,
        language: String,
        variantId: String?,
        legacyVariant: String?,
        condition: PricingCondition
    ): CardPriceQuoteResponse? {
        val details =
            catalog.details(
                cardId = cardId,
                language = language
            ) ?: return null

        val normalizedLegacyVariant =
            legacyVariant
                ?.trim()
                ?.uppercase()
                ?.takeIf(String::isNotBlank)

        val selected =
            when {
                !variantId.isNullOrBlank() ->
                    details.variants
                        .firstOrNull {
                            it.id == variantId.trim()
                        }

                normalizedLegacyVariant != null -> {
                    val candidates =
                        details.variants.filter {
                            it.legacyVariant ==
                                normalizedLegacyVariant
                        }

                    /*
                     * Eine Legacy-Variante darf nur dann
                     * bepreist werden, wenn genau eine
                     * physische Detailvariante dazu passt.
                     * Besser kein Preis als ein falscher.
                     */
                    candidates.singleOrNull()
                }

                details.variants.size == 1 ->
                    details.variants.first()

                else ->
                    null
            }

        val providerQuote =
            selected?.let { variant ->
                providers.firstNotNullOfOrNull {
                    provider ->

                    provider.quote(
                        card = details,
                        variant = variant
                    )
                }
            }

        val baseEur =
            providerQuote?.baseEur

        return CardPriceQuoteResponse(
            cardId = details.id,
            languageCode = details.languageCode,
            variantId = selected?.id,
            variantType = selected?.type,
            condition = condition.name,
            market = "TCG",
            source = providerQuote?.source,
            baseEur = baseEur,
            conditionFactor = condition.factor,
            eur =
                baseEur?.times(
                    condition.factor
                ),
            exactLanguageMatch =
                details.languageCode == language,
            exactVariantMatch =
                selected != null
        )
    }
}
