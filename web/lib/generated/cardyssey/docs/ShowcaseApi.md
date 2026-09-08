# ShowcaseApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getShowcase**](ShowcaseApi.md#getshowcase) | **GET** /api/v1/me/showcase | Eigenes Showcase laden |
| [**updateShowcase**](ShowcaseApi.md#updateshowcaseoperation) | **PUT** /api/v1/me/showcase | Eigenes Showcase speichern |



## getShowcase

> Array&lt;ShowcaseItemResponse&gt; getShowcase()

Eigenes Showcase laden

### Example

```ts
import {
  Configuration,
  ShowcaseApi,
} from 'cardyssey-contract';
import type { GetShowcaseRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ShowcaseApi(config);

  try {
    const data = await api.getShowcase();
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

[**Array&lt;ShowcaseItemResponse&gt;**](ShowcaseItemResponse.md)

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


## updateShowcase

> Array&lt;ShowcaseItemResponse&gt; updateShowcase(updateShowcaseRequest)

Eigenes Showcase speichern

### Example

```ts
import {
  Configuration,
  ShowcaseApi,
} from 'cardyssey-contract';
import type { UpdateShowcaseOperationRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ShowcaseApi(config);

  const body = {
    // UpdateShowcaseRequest
    updateShowcaseRequest: ...,
  } satisfies UpdateShowcaseOperationRequest;

  try {
    const data = await api.updateShowcase(body);
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
| **updateShowcaseRequest** | [UpdateShowcaseRequest](UpdateShowcaseRequest.md) |  | |

### Return type

[**Array&lt;ShowcaseItemResponse&gt;**](ShowcaseItemResponse.md)

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

