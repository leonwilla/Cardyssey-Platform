# PricingApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**getCardPriceQuote**](PricingApi.md#getCardPriceQuote) | **GET** /api/v1/pricing/cards/{id} | Zentralen Marktpreis für eine exakte Kartenvariante laden |


<a id="getCardPriceQuote"></a>
# **getCardPriceQuote**
> CardPriceQuoteResponse getCardPriceQuote(id, language, variantId, variant, condition, market)

Zentralen Marktpreis für eine exakte Kartenvariante laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = PricingApi()
val id : kotlin.String = id_example // kotlin.String | 
val language : kotlin.String = language_example // kotlin.String | 
val variantId : kotlin.String = variantId_example // kotlin.String | 
val variant : kotlin.String = variant_example // kotlin.String | 
val condition : kotlin.String = condition_example // kotlin.String | 
val market : kotlin.String = market_example // kotlin.String | 
try {
    val result : CardPriceQuoteResponse = apiInstance.getCardPriceQuote(id, language, variantId, variant, condition, market)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling PricingApi#getCardPriceQuote")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling PricingApi#getCardPriceQuote")
    e.printStackTrace()
}
```

### Parameters
| **id** | **kotlin.String**|  | |
| **language** | **kotlin.String**|  | [optional] [default to &quot;de&quot;] |
| **variantId** | **kotlin.String**|  | [optional] |
| **variant** | **kotlin.String**|  | [optional] [enum: NORMAL, REVERSE, HOLO, FIRST_EDITION] |
| **condition** | **kotlin.String**|  | [optional] [default to Condition.NEAR_MINT] [enum: MINT, NEAR_MINT, EXCELLENT, GOOD, PLAYED] |
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **market** | **kotlin.String**|  | [optional] [default to Market.TCG] [enum: TCG, EBAY] |

### Return type

[**CardPriceQuoteResponse**](CardPriceQuoteResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

