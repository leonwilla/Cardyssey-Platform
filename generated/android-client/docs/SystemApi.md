# SystemApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**getHealth**](SystemApi.md#getHealth) | **GET** /api/v1/health | API-Status |


<a id="getHealth"></a>
# **getHealth**
> HealthResponse getHealth()

API-Status

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = SystemApi()
try {
    val result : HealthResponse = apiInstance.getHealth()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling SystemApi#getHealth")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling SystemApi#getHealth")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**HealthResponse**](HealthResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

