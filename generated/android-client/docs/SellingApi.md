# SellingApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**createSaleListing**](SellingApi.md#createSaleListing) | **POST** /api/v1/selling | Verkaufsangebot anlegen |
| [**deleteSaleListing**](SellingApi.md#deleteSaleListing) | **DELETE** /api/v1/selling/{id} | Verkaufsangebot löschen |
| [**getSaleListings**](SellingApi.md#getSaleListings) | **GET** /api/v1/selling | Eigene Verkaufsangebote |
| [**updateSaleListing**](SellingApi.md#updateSaleListing) | **PUT** /api/v1/selling/{id} | Verkaufsangebot ändern |


<a id="createSaleListing"></a>
# **createSaleListing**
> createSaleListing(createSaleListingRequest)

Verkaufsangebot anlegen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = SellingApi()
val createSaleListingRequest : CreateSaleListingRequest =  // CreateSaleListingRequest | 
try {
    apiInstance.createSaleListing(createSaleListingRequest)
} catch (e: ClientException) {
    println("4xx response calling SellingApi#createSaleListing")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling SellingApi#createSaleListing")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **createSaleListingRequest** | [**CreateSaleListingRequest**](CreateSaleListingRequest.md)|  | |

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

 - **Content-Type**: application/json
 - **Accept**: application/json

<a id="deleteSaleListing"></a>
# **deleteSaleListing**
> deleteSaleListing(id)

Verkaufsangebot löschen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = SellingApi()
val id : kotlin.String = id_example // kotlin.String | 
try {
    apiInstance.deleteSaleListing(id)
} catch (e: ClientException) {
    println("4xx response calling SellingApi#deleteSaleListing")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling SellingApi#deleteSaleListing")
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

<a id="getSaleListings"></a>
# **getSaleListings**
> kotlin.collections.List&lt;SaleListingResponse&gt; getSaleListings()

Eigene Verkaufsangebote

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = SellingApi()
try {
    val result : kotlin.collections.List<SaleListingResponse> = apiInstance.getSaleListings()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling SellingApi#getSaleListings")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling SellingApi#getSaleListings")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**kotlin.collections.List&lt;SaleListingResponse&gt;**](SaleListingResponse.md)

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

<a id="updateSaleListing"></a>
# **updateSaleListing**
> updateSaleListing(id, updateSaleListingRequest)

Verkaufsangebot ändern

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = SellingApi()
val id : kotlin.String = id_example // kotlin.String | 
val updateSaleListingRequest : UpdateSaleListingRequest =  // UpdateSaleListingRequest | 
try {
    apiInstance.updateSaleListing(id, updateSaleListingRequest)
} catch (e: ClientException) {
    println("4xx response calling SellingApi#updateSaleListing")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling SellingApi#updateSaleListing")
    e.printStackTrace()
}
```

### Parameters
| **id** | **kotlin.String**|  | |
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **updateSaleListingRequest** | [**UpdateSaleListingRequest**](UpdateSaleListingRequest.md)|  | |

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

 - **Content-Type**: application/json
 - **Accept**: application/json

