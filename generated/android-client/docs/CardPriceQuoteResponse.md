
# CardPriceQuoteResponse

## Properties
| Name | Type | Description | Notes |
| ------------ | ------------- | ------------- | ------------- |
| **cardId** | **kotlin.String** |  |  |
| **languageCode** | **kotlin.String** |  |  |
| **condition** | [**inline**](#Condition) |  |  |
| **market** | [**inline**](#Market) |  |  |
| **conditionFactor** | **kotlin.Double** |  |  |
| **exactLanguageMatch** | **kotlin.Boolean** |  |  |
| **exactVariantMatch** | **kotlin.Boolean** |  |  |
| **variantId** | **kotlin.String** |  |  [optional] |
| **variantType** | **kotlin.String** |  |  [optional] |
| **source** | [**inline**](#Source) |  |  [optional] |
| **baseEur** | **kotlin.Double** |  |  [optional] |
| **eur** | **kotlin.Double** |  |  [optional] |
| **sampleCount** | **kotlin.Int** |  |  [optional] |
| **updatedAtMs** | **kotlin.Long** |  |  [optional] |


<a id="Condition"></a>
## Enum: condition
| Name | Value |
| ---- | ----- |
| condition | MINT, NEAR_MINT, EXCELLENT, GOOD, PLAYED |


<a id="Market"></a>
## Enum: market
| Name | Value |
| ---- | ----- |
| market | TCG, EBAY |


<a id="Source"></a>
## Enum: source
| Name | Value |
| ---- | ----- |
| source | TCGDEX, JUSTTCG, SOLDCOMPS |



