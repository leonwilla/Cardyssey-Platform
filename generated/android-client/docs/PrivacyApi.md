# PrivacyApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**getPrivacy**](PrivacyApi.md#getPrivacy) | **GET** /api/v1/me/privacy | Privatsphäre laden |
| [**updatePrivacy**](PrivacyApi.md#updatePrivacy) | **PUT** /api/v1/me/privacy | Privatsphäre speichern |


<a id="getPrivacy"></a>
# **getPrivacy**
> PrivacySettings getPrivacy()

Privatsphäre laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = PrivacyApi()
try {
    val result : PrivacySettings = apiInstance.getPrivacy()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling PrivacyApi#getPrivacy")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling PrivacyApi#getPrivacy")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**PrivacySettings**](PrivacySettings.md)

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

<a id="updatePrivacy"></a>
# **updatePrivacy**
> PrivacySettings updatePrivacy(privacySettings)

Privatsphäre speichern

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = PrivacyApi()
val privacySettings : PrivacySettings =  // PrivacySettings | 
try {
    val result : PrivacySettings = apiInstance.updatePrivacy(privacySettings)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling PrivacyApi#updatePrivacy")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling PrivacyApi#updatePrivacy")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **privacySettings** | [**PrivacySettings**](PrivacySettings.md)|  | |

### Return type

[**PrivacySettings**](PrivacySettings.md)

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

