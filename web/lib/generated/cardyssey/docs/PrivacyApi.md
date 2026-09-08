# PrivacyApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getPrivacy**](PrivacyApi.md#getprivacy) | **GET** /api/v1/me/privacy | Privatsphäre laden |
| [**updatePrivacy**](PrivacyApi.md#updateprivacy) | **PUT** /api/v1/me/privacy | Privatsphäre speichern |



## getPrivacy

> PrivacySettings getPrivacy()

Privatsphäre laden

### Example

```ts
import {
  Configuration,
  PrivacyApi,
} from 'cardyssey-contract';
import type { GetPrivacyRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new PrivacyApi(config);

  try {
    const data = await api.getPrivacy();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**PrivacySettings**](PrivacySettings.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **400** | Ungültige Anfrage |  -  |
| **401** | Nicht authentifiziert |  -  |
| **403** | Nicht erlaubt |  -  |
| **404** | Nicht gefunden |  -  |
| **409** | Konflikt |  -  |
| **200** | Erfolgreich |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## updatePrivacy

> PrivacySettings updatePrivacy(privacySettings)

Privatsphäre speichern

### Example

```ts
import {
  Configuration,
  PrivacyApi,
} from 'cardyssey-contract';
import type { UpdatePrivacyRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new PrivacyApi(config);

  const body = {
    // PrivacySettings
    privacySettings: ...,
  } satisfies UpdatePrivacyRequest;

  try {
    const data = await api.updatePrivacy(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **privacySettings** | [PrivacySettings](PrivacySettings.md) |  | |

### Return type

[**PrivacySettings**](PrivacySettings.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **400** | Ungültige Anfrage |  -  |
| **401** | Nicht authentifiziert |  -  |
| **403** | Nicht erlaubt |  -  |
| **404** | Nicht gefunden |  -  |
| **409** | Konflikt |  -  |
| **200** | Erfolgreich |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

