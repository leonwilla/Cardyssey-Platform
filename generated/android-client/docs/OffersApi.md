# OffersApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**acceptOffer**](OffersApi.md#acceptOffer) | **POST** /api/v1/offers/{id}/accept | Angebot annehmen |
| [**createOffer**](OffersApi.md#createOffer) | **POST** /api/v1/offers | Angebot senden |
| [**getIncomingOffers**](OffersApi.md#getIncomingOffers) | **GET** /api/v1/offers/incoming | Eingehende Angebote laden |
| [**getOutgoingOffers**](OffersApi.md#getOutgoingOffers) | **GET** /api/v1/offers/outgoing | Ausgehende Angebote laden |
| [**rejectOffer**](OffersApi.md#rejectOffer) | **POST** /api/v1/offers/{id}/reject | Angebot ablehnen |
| [**withdrawOffer**](OffersApi.md#withdrawOffer) | **DELETE** /api/v1/offers/{id} | Angebot zurückziehen |


<a id="acceptOffer"></a>
# **acceptOffer**
> MarketplaceOfferResponse acceptOffer(id)

Angebot annehmen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = OffersApi()
val id : kotlin.String = id_example // kotlin.String | 
try {
    val result : MarketplaceOfferResponse = apiInstance.acceptOffer(id)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling OffersApi#acceptOffer")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling OffersApi#acceptOffer")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **id** | **kotlin.String**|  | |

### Return type

[**MarketplaceOfferResponse**](MarketplaceOfferResponse.md)

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

<a id="createOffer"></a>
# **createOffer**
> MarketplaceOfferResponse createOffer(createMarketplaceOfferRequest)

Angebot senden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = OffersApi()
val createMarketplaceOfferRequest : CreateMarketplaceOfferRequest =  // CreateMarketplaceOfferRequest | 
try {
    val result : MarketplaceOfferResponse = apiInstance.createOffer(createMarketplaceOfferRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling OffersApi#createOffer")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling OffersApi#createOffer")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **createMarketplaceOfferRequest** | [**CreateMarketplaceOfferRequest**](CreateMarketplaceOfferRequest.md)|  | |

### Return type

[**MarketplaceOfferResponse**](MarketplaceOfferResponse.md)

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

 - **Content-Type**: application/json
 - **Accept**: application/json

<a id="getIncomingOffers"></a>
# **getIncomingOffers**
> kotlin.collections.List&lt;MarketplaceOfferResponse&gt; getIncomingOffers()

Eingehende Angebote laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = OffersApi()
try {
    val result : kotlin.collections.List<MarketplaceOfferResponse> = apiInstance.getIncomingOffers()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling OffersApi#getIncomingOffers")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling OffersApi#getIncomingOffers")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**kotlin.collections.List&lt;MarketplaceOfferResponse&gt;**](MarketplaceOfferResponse.md)

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

<a id="getOutgoingOffers"></a>
# **getOutgoingOffers**
> kotlin.collections.List&lt;MarketplaceOfferResponse&gt; getOutgoingOffers()

Ausgehende Angebote laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = OffersApi()
try {
    val result : kotlin.collections.List<MarketplaceOfferResponse> = apiInstance.getOutgoingOffers()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling OffersApi#getOutgoingOffers")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling OffersApi#getOutgoingOffers")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**kotlin.collections.List&lt;MarketplaceOfferResponse&gt;**](MarketplaceOfferResponse.md)

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

<a id="rejectOffer"></a>
# **rejectOffer**
> MarketplaceOfferResponse rejectOffer(id)

Angebot ablehnen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = OffersApi()
val id : kotlin.String = id_example // kotlin.String | 
try {
    val result : MarketplaceOfferResponse = apiInstance.rejectOffer(id)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling OffersApi#rejectOffer")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling OffersApi#rejectOffer")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **id** | **kotlin.String**|  | |

### Return type

[**MarketplaceOfferResponse**](MarketplaceOfferResponse.md)

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

<a id="withdrawOffer"></a>
# **withdrawOffer**
> withdrawOffer(id)

Angebot zurückziehen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = OffersApi()
val id : kotlin.String = id_example // kotlin.String | 
try {
    apiInstance.withdrawOffer(id)
} catch (e: ClientException) {
    println("4xx response calling OffersApi#withdrawOffer")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling OffersApi#withdrawOffer")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **id** | **kotlin.String**|  | |

### Return type

null (empty response body)

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

