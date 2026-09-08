# WishlistApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**createWishlistItem**](WishlistApi.md#createWishlistItem) | **POST** /api/v1/wishlist | Wishlist-Eintrag anlegen |
| [**deleteWishlistItem**](WishlistApi.md#deleteWishlistItem) | **DELETE** /api/v1/wishlist/{id} | Wishlist-Eintrag löschen |
| [**getWishlist**](WishlistApi.md#getWishlist) | **GET** /api/v1/wishlist | Wishlist laden |


<a id="createWishlistItem"></a>
# **createWishlistItem**
> WishlistResponse createWishlistItem(createWishlistRequest)

Wishlist-Eintrag anlegen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = WishlistApi()
val createWishlistRequest : CreateWishlistRequest =  // CreateWishlistRequest | 
try {
    val result : WishlistResponse = apiInstance.createWishlistItem(createWishlistRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling WishlistApi#createWishlistItem")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling WishlistApi#createWishlistItem")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **createWishlistRequest** | [**CreateWishlistRequest**](CreateWishlistRequest.md)|  | |

### Return type

[**WishlistResponse**](WishlistResponse.md)

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

<a id="deleteWishlistItem"></a>
# **deleteWishlistItem**
> deleteWishlistItem(id)

Wishlist-Eintrag löschen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = WishlistApi()
val id : kotlin.String = id_example // kotlin.String | 
try {
    apiInstance.deleteWishlistItem(id)
} catch (e: ClientException) {
    println("4xx response calling WishlistApi#deleteWishlistItem")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling WishlistApi#deleteWishlistItem")
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

<a id="getWishlist"></a>
# **getWishlist**
> kotlin.collections.List&lt;WishlistResponse&gt; getWishlist()

Wishlist laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = WishlistApi()
try {
    val result : kotlin.collections.List<WishlistResponse> = apiInstance.getWishlist()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling WishlistApi#getWishlist")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling WishlistApi#getWishlist")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**kotlin.collections.List&lt;WishlistResponse&gt;**](WishlistResponse.md)

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

