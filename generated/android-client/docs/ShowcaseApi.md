# ShowcaseApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**getShowcase**](ShowcaseApi.md#getShowcase) | **GET** /api/v1/me/showcase | Eigenes Showcase laden |
| [**updateShowcase**](ShowcaseApi.md#updateShowcase) | **PUT** /api/v1/me/showcase | Eigenes Showcase speichern |


<a id="getShowcase"></a>
# **getShowcase**
> kotlin.collections.List&lt;ShowcaseItemResponse&gt; getShowcase()

Eigenes Showcase laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = ShowcaseApi()
try {
    val result : kotlin.collections.List<ShowcaseItemResponse> = apiInstance.getShowcase()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling ShowcaseApi#getShowcase")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling ShowcaseApi#getShowcase")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**kotlin.collections.List&lt;ShowcaseItemResponse&gt;**](ShowcaseItemResponse.md)

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

<a id="updateShowcase"></a>
# **updateShowcase**
> kotlin.collections.List&lt;ShowcaseItemResponse&gt; updateShowcase(updateShowcaseRequest)

Eigenes Showcase speichern

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = ShowcaseApi()
val updateShowcaseRequest : UpdateShowcaseRequest =  // UpdateShowcaseRequest | 
try {
    val result : kotlin.collections.List<ShowcaseItemResponse> = apiInstance.updateShowcase(updateShowcaseRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling ShowcaseApi#updateShowcase")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling ShowcaseApi#updateShowcase")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **updateShowcaseRequest** | [**UpdateShowcaseRequest**](UpdateShowcaseRequest.md)|  | |

### Return type

[**kotlin.collections.List&lt;ShowcaseItemResponse&gt;**](ShowcaseItemResponse.md)

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

