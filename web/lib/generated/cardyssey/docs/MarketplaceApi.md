# MarketplaceApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getMarketplace**](MarketplaceApi.md#getmarketplace) | **GET** /api/v1/marketplace | Marktplatz laden |



## getMarketplace

> Array&lt;MarketplaceListingResponse&gt; getMarketplace()

Marktplatz laden

### Example

```ts
import {
  Configuration,
  MarketplaceApi,
} from 'cardyssey-contract';
import type { GetMarketplaceRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new MarketplaceApi(config);

  try {
    const data = await api.getMarketplace();
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

[**Array&lt;MarketplaceListingResponse&gt;**](MarketplaceListingResponse.md)

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

