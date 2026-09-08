# SellingApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createSaleListing**](SellingApi.md#createsalelistingoperation) | **POST** /api/v1/selling | Verkaufsangebot anlegen |
| [**deleteSaleListing**](SellingApi.md#deletesalelisting) | **DELETE** /api/v1/selling/{id} | Verkaufsangebot löschen |
| [**getSaleListings**](SellingApi.md#getsalelistings) | **GET** /api/v1/selling | Eigene Verkaufsangebote |
| [**updateSaleListing**](SellingApi.md#updatesalelistingoperation) | **PUT** /api/v1/selling/{id} | Verkaufsangebot ändern |



## createSaleListing

> createSaleListing(createSaleListingRequest)

Verkaufsangebot anlegen

### Example

```ts
import {
  Configuration,
  SellingApi,
} from 'cardyssey-contract';
import type { CreateSaleListingOperationRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new SellingApi(config);

  const body = {
    // CreateSaleListingRequest
    createSaleListingRequest: ...,
  } satisfies CreateSaleListingOperationRequest;

  try {
    const data = await api.createSaleListing(body);
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
| **createSaleListingRequest** | [CreateSaleListingRequest](CreateSaleListingRequest.md) |  | |

### Return type

`void` (Empty response body)

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
| **201** | Erfolgreich |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## deleteSaleListing

> deleteSaleListing(id)

Verkaufsangebot löschen

### Example

```ts
import {
  Configuration,
  SellingApi,
} from 'cardyssey-contract';
import type { DeleteSaleListingRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new SellingApi(config);

  const body = {
    // string
    id: id_example,
  } satisfies DeleteSaleListingRequest;

  try {
    const data = await api.deleteSaleListing(body);
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
| **id** | `string` |  | [Defaults to `undefined`] |

### Return type

`void` (Empty response body)

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
| **204** | Erfolgreich |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getSaleListings

> Array&lt;SaleListingResponse&gt; getSaleListings()

Eigene Verkaufsangebote

### Example

```ts
import {
  Configuration,
  SellingApi,
} from 'cardyssey-contract';
import type { GetSaleListingsRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new SellingApi(config);

  try {
    const data = await api.getSaleListings();
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

[**Array&lt;SaleListingResponse&gt;**](SaleListingResponse.md)

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


## updateSaleListing

> updateSaleListing(id, updateSaleListingRequest)

Verkaufsangebot ändern

### Example

```ts
import {
  Configuration,
  SellingApi,
} from 'cardyssey-contract';
import type { UpdateSaleListingOperationRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new SellingApi(config);

  const body = {
    // string
    id: id_example,
    // UpdateSaleListingRequest
    updateSaleListingRequest: ...,
  } satisfies UpdateSaleListingOperationRequest;

  try {
    const data = await api.updateSaleListing(body);
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
| **id** | `string` |  | [Defaults to `undefined`] |
| **updateSaleListingRequest** | [UpdateSaleListingRequest](UpdateSaleListingRequest.md) |  | |

### Return type

`void` (Empty response body)

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
| **204** | Erfolgreich |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

