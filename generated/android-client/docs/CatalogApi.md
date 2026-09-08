# CatalogApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**getCard**](CatalogApi.md#getCard) | **GET** /api/v1/cards/{id} | Kartendetails laden |
| [**getSet**](CatalogApi.md#getSet) | **GET** /api/v1/sets/{id} | Setdetails laden |
| [**getSets**](CatalogApi.md#getSets) | **GET** /api/v1/sets | Sets laden |
| [**recognizeCard**](CatalogApi.md#recognizeCard) | **POST** /api/v1/cards/recognize | OCR-Text analysieren |
| [**searchCards**](CatalogApi.md#searchCards) | **GET** /api/v1/cards/search | Karten suchen |


<a id="getCard"></a>
# **getCard**
> CatalogCardDetails getCard(id, language)

Kartendetails laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CatalogApi()
val id : kotlin.String = id_example // kotlin.String | 
val language : kotlin.String = language_example // kotlin.String | 
try {
    val result : CatalogCardDetails = apiInstance.getCard(id, language)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CatalogApi#getCard")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CatalogApi#getCard")
    e.printStackTrace()
}
```

### Parameters
| **id** | **kotlin.String**|  | |
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **language** | **kotlin.String**|  | [optional] [default to Language.de] [enum: de, en, fr, it, es, pt, ja, ko, zh-tw, zh-cn] |

### Return type

[**CatalogCardDetails**](CatalogCardDetails.md)

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

<a id="getSet"></a>
# **getSet**
> CatalogSetDetails getSet(id, language)

Setdetails laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CatalogApi()
val id : kotlin.String = id_example // kotlin.String | 
val language : kotlin.String = language_example // kotlin.String | 
try {
    val result : CatalogSetDetails = apiInstance.getSet(id, language)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CatalogApi#getSet")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CatalogApi#getSet")
    e.printStackTrace()
}
```

### Parameters
| **id** | **kotlin.String**|  | |
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **language** | **kotlin.String**|  | [optional] [default to Language.de] [enum: de, en, fr, it, es, pt, ja, ko, zh-tw, zh-cn] |

### Return type

[**CatalogSetDetails**](CatalogSetDetails.md)

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

<a id="getSets"></a>
# **getSets**
> kotlin.collections.List&lt;CatalogSetSummary&gt; getSets(language)

Sets laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CatalogApi()
val language : kotlin.String = language_example // kotlin.String | 
try {
    val result : kotlin.collections.List<CatalogSetSummary> = apiInstance.getSets(language)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CatalogApi#getSets")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CatalogApi#getSets")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **language** | **kotlin.String**|  | [optional] [default to Language.de] [enum: de, en, fr, it, es, pt, ja, ko, zh-tw, zh-cn] |

### Return type

[**kotlin.collections.List&lt;CatalogSetSummary&gt;**](CatalogSetSummary.md)

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

<a id="recognizeCard"></a>
# **recognizeCard**
> CardRecognitionResponse recognizeCard(cardRecognitionRequest)

OCR-Text analysieren

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CatalogApi()
val cardRecognitionRequest : CardRecognitionRequest =  // CardRecognitionRequest | 
try {
    val result : CardRecognitionResponse = apiInstance.recognizeCard(cardRecognitionRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CatalogApi#recognizeCard")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CatalogApi#recognizeCard")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **cardRecognitionRequest** | [**CardRecognitionRequest**](CardRecognitionRequest.md)|  | |

### Return type

[**CardRecognitionResponse**](CardRecognitionResponse.md)

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

<a id="searchCards"></a>
# **searchCards**
> kotlin.collections.List&lt;CatalogCardSearchResult&gt; searchCards(q, number, language, limit)

Karten suchen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CatalogApi()
val q : kotlin.String = q_example // kotlin.String | 
val number : kotlin.String = number_example // kotlin.String | 
val language : kotlin.String = language_example // kotlin.String | 
val limit : kotlin.Int = 56 // kotlin.Int | 
try {
    val result : kotlin.collections.List<CatalogCardSearchResult> = apiInstance.searchCards(q, number, language, limit)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CatalogApi#searchCards")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CatalogApi#searchCards")
    e.printStackTrace()
}
```

### Parameters
| **q** | **kotlin.String**|  | [optional] |
| **number** | **kotlin.String**|  | [optional] |
| **language** | **kotlin.String**|  | [optional] [default to Language.de] [enum: de, en, fr, it, es, pt, ja, ko, zh-tw, zh-cn] |
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **limit** | **kotlin.Int**|  | [optional] [default to 20] |

### Return type

[**kotlin.collections.List&lt;CatalogCardSearchResult&gt;**](CatalogCardSearchResult.md)

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

