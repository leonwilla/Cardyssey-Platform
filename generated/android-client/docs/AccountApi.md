# AccountApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**deleteMyAvatar**](AccountApi.md#deleteMyAvatar) | **DELETE** /api/v1/me/avatar | Profilbild löschen |
| [**getMe**](AccountApi.md#getMe) | **GET** /api/v1/me | Eigenes Profil laden |
| [**updateMe**](AccountApi.md#updateMe) | **PUT** /api/v1/me | Eigenes Profil ändern |
| [**updateMyAvatar**](AccountApi.md#updateMyAvatar) | **PUT** /api/v1/me/avatar | Profilbild hochladen |


<a id="deleteMyAvatar"></a>
# **deleteMyAvatar**
> UserResponse deleteMyAvatar()

Profilbild löschen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = AccountApi()
try {
    val result : UserResponse = apiInstance.deleteMyAvatar()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling AccountApi#deleteMyAvatar")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling AccountApi#deleteMyAvatar")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**UserResponse**](UserResponse.md)

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

<a id="getMe"></a>
# **getMe**
> UserResponse getMe()

Eigenes Profil laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = AccountApi()
try {
    val result : UserResponse = apiInstance.getMe()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling AccountApi#getMe")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling AccountApi#getMe")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**UserResponse**](UserResponse.md)

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

<a id="updateMe"></a>
# **updateMe**
> UserResponse updateMe(updateMeRequest)

Eigenes Profil ändern

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = AccountApi()
val updateMeRequest : UpdateMeRequest =  // UpdateMeRequest | 
try {
    val result : UserResponse = apiInstance.updateMe(updateMeRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling AccountApi#updateMe")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling AccountApi#updateMe")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **updateMeRequest** | [**UpdateMeRequest**](UpdateMeRequest.md)|  | |

### Return type

[**UserResponse**](UserResponse.md)

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

<a id="updateMyAvatar"></a>
# **updateMyAvatar**
> UserResponse updateMyAvatar(body)

Profilbild hochladen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = AccountApi()
val body : java.io.File = BINARY_DATA_HERE // java.io.File | 
try {
    val result : UserResponse = apiInstance.updateMyAvatar(body)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling AccountApi#updateMyAvatar")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling AccountApi#updateMyAvatar")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **body** | **java.io.File**|  | |

### Return type

[**UserResponse**](UserResponse.md)

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

 - **Content-Type**: application/octet-stream
 - **Accept**: application/json

