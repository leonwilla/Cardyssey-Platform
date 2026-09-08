# AuthApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**login**](AuthApi.md#login) | **POST** /api/v1/auth/login | Anmelden |
| [**logout**](AuthApi.md#logout) | **POST** /api/v1/auth/logout | Refresh-Token widerrufen |
| [**refresh**](AuthApi.md#refresh) | **POST** /api/v1/auth/refresh | Tokens erneuern |
| [**register**](AuthApi.md#register) | **POST** /api/v1/auth/register | Account registrieren |


<a id="login"></a>
# **login**
> AuthResponse login(loginRequest)

Anmelden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = AuthApi()
val loginRequest : LoginRequest =  // LoginRequest | 
try {
    val result : AuthResponse = apiInstance.login(loginRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling AuthApi#login")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling AuthApi#login")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **loginRequest** | [**LoginRequest**](LoginRequest.md)|  | |

### Return type

[**AuthResponse**](AuthResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

<a id="logout"></a>
# **logout**
> logout(logoutRequest)

Refresh-Token widerrufen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = AuthApi()
val logoutRequest : LogoutRequest =  // LogoutRequest | 
try {
    apiInstance.logout(logoutRequest)
} catch (e: ClientException) {
    println("4xx response calling AuthApi#logout")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling AuthApi#logout")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **logoutRequest** | [**LogoutRequest**](LogoutRequest.md)|  | |

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

<a id="refresh"></a>
# **refresh**
> AuthResponse refresh(refreshRequest)

Tokens erneuern

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = AuthApi()
val refreshRequest : RefreshRequest =  // RefreshRequest | 
try {
    val result : AuthResponse = apiInstance.refresh(refreshRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling AuthApi#refresh")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling AuthApi#refresh")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **refreshRequest** | [**RefreshRequest**](RefreshRequest.md)|  | |

### Return type

[**AuthResponse**](AuthResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

<a id="register"></a>
# **register**
> AuthResponse register(registerRequest)

Account registrieren

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = AuthApi()
val registerRequest : RegisterRequest =  // RegisterRequest | 
try {
    val result : AuthResponse = apiInstance.register(registerRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling AuthApi#register")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling AuthApi#register")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **registerRequest** | [**RegisterRequest**](RegisterRequest.md)|  | |

### Return type

[**AuthResponse**](AuthResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

