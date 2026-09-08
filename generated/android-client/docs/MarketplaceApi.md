# MarketplaceApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**getMarketplace**](MarketplaceApi.md#getMarketplace) | **GET** /api/v1/marketplace | Marktplatz laden |


<a id="getMarketplace"></a>
# **getMarketplace**
> kotlin.collections.List&lt;MarketplaceListingResponse&gt; getMarketplace()

Marktplatz laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = MarketplaceApi()
try {
    val result : kotlin.collections.List<MarketplaceListingResponse> = apiInstance.getMarketplace()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling MarketplaceApi#getMarketplace")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling MarketplaceApi#getMarketplace")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**kotlin.collections.List&lt;MarketplaceListingResponse&gt;**](MarketplaceListingResponse.md)

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

