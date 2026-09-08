# CollectionApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**createCollectionItem**](CollectionApi.md#createCollectionItem) | **POST** /api/v1/collection | Sammlungseintrag anlegen |
| [**deleteCollectionItem**](CollectionApi.md#deleteCollectionItem) | **DELETE** /api/v1/collection/{key} | Sammlungseintrag löschen |
| [**getCollection**](CollectionApi.md#getCollection) | **GET** /api/v1/collection | Sammlung laden |
| [**importCollection**](CollectionApi.md#importCollection) | **POST** /api/v1/collection/import | Sammlung importieren |
| [**updateCollectionItem**](CollectionApi.md#updateCollectionItem) | **PUT** /api/v1/collection/{key} | Sammlungseintrag aktualisieren |


<a id="createCollectionItem"></a>
# **createCollectionItem**
> CollectionWriteResponse createCollectionItem(collectionItemDto)

Sammlungseintrag anlegen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CollectionApi()
val collectionItemDto : CollectionItemDto =  // CollectionItemDto | 
try {
    val result : CollectionWriteResponse = apiInstance.createCollectionItem(collectionItemDto)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CollectionApi#createCollectionItem")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CollectionApi#createCollectionItem")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **collectionItemDto** | [**CollectionItemDto**](CollectionItemDto.md)|  | |

### Return type

[**CollectionWriteResponse**](CollectionWriteResponse.md)

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

<a id="deleteCollectionItem"></a>
# **deleteCollectionItem**
> deleteCollectionItem(key)

Sammlungseintrag löschen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CollectionApi()
val key : kotlin.String = key_example // kotlin.String | 
try {
    apiInstance.deleteCollectionItem(key)
} catch (e: ClientException) {
    println("4xx response calling CollectionApi#deleteCollectionItem")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CollectionApi#deleteCollectionItem")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **key** | **kotlin.String**|  | |

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

<a id="getCollection"></a>
# **getCollection**
> kotlin.collections.List&lt;CollectionItemDto&gt; getCollection()

Sammlung laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CollectionApi()
try {
    val result : kotlin.collections.List<CollectionItemDto> = apiInstance.getCollection()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CollectionApi#getCollection")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CollectionApi#getCollection")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**kotlin.collections.List&lt;CollectionItemDto&gt;**](CollectionItemDto.md)

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

<a id="importCollection"></a>
# **importCollection**
> CollectionImportResponse importCollection(collectionItemDto)

Sammlung importieren

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CollectionApi()
val collectionItemDto : kotlin.collections.List<CollectionItemDto> =  // kotlin.collections.List<CollectionItemDto> | 
try {
    val result : CollectionImportResponse = apiInstance.importCollection(collectionItemDto)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CollectionApi#importCollection")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CollectionApi#importCollection")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **collectionItemDto** | [**kotlin.collections.List&lt;CollectionItemDto&gt;**](CollectionItemDto.md)|  | |

### Return type

[**CollectionImportResponse**](CollectionImportResponse.md)

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

<a id="updateCollectionItem"></a>
# **updateCollectionItem**
> CollectionWriteResponse updateCollectionItem(key, collectionItemDto)

Sammlungseintrag aktualisieren

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = CollectionApi()
val key : kotlin.String = key_example // kotlin.String | 
val collectionItemDto : CollectionItemDto =  // CollectionItemDto | 
try {
    val result : CollectionWriteResponse = apiInstance.updateCollectionItem(key, collectionItemDto)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling CollectionApi#updateCollectionItem")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling CollectionApi#updateCollectionItem")
    e.printStackTrace()
}
```

### Parameters
| **key** | **kotlin.String**|  | |
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **collectionItemDto** | [**CollectionItemDto**](CollectionItemDto.md)|  | |

### Return type

[**CollectionWriteResponse**](CollectionWriteResponse.md)

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

