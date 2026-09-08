# CollectionApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createCollectionItem**](CollectionApi.md#createcollectionitem) | **POST** /api/v1/collection | Sammlungseintrag anlegen |
| [**deleteCollectionItem**](CollectionApi.md#deletecollectionitem) | **DELETE** /api/v1/collection/{key} | Sammlungseintrag löschen |
| [**getCollection**](CollectionApi.md#getcollection) | **GET** /api/v1/collection | Sammlung laden |
| [**importCollection**](CollectionApi.md#importcollection) | **POST** /api/v1/collection/import | Sammlung importieren |
| [**updateCollectionItem**](CollectionApi.md#updatecollectionitem) | **PUT** /api/v1/collection/{key} | Sammlungseintrag aktualisieren |



## createCollectionItem

> CollectionWriteResponse createCollectionItem(collectionItemDto)

Sammlungseintrag anlegen

### Example

```ts
import {
  Configuration,
  CollectionApi,
} from 'cardyssey-contract';
import type { CreateCollectionItemRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CollectionApi(config);

  const body = {
    // CollectionItemDto
    collectionItemDto: ...,
  } satisfies CreateCollectionItemRequest;

  try {
    const data = await api.createCollectionItem(body);
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
| **collectionItemDto** | [CollectionItemDto](CollectionItemDto.md) |  | |

### Return type

[**CollectionWriteResponse**](CollectionWriteResponse.md)

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


## deleteCollectionItem

> deleteCollectionItem(key)

Sammlungseintrag löschen

### Example

```ts
import {
  Configuration,
  CollectionApi,
} from 'cardyssey-contract';
import type { DeleteCollectionItemRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CollectionApi(config);

  const body = {
    // string
    key: key_example,
  } satisfies DeleteCollectionItemRequest;

  try {
    const data = await api.deleteCollectionItem(body);
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
| **key** | `string` |  | [Defaults to `undefined`] |

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


## getCollection

> Array&lt;CollectionItemDto&gt; getCollection()

Sammlung laden

### Example

```ts
import {
  Configuration,
  CollectionApi,
} from 'cardyssey-contract';
import type { GetCollectionRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CollectionApi(config);

  try {
    const data = await api.getCollection();
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

[**Array&lt;CollectionItemDto&gt;**](CollectionItemDto.md)

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


## importCollection

> CollectionImportResponse importCollection(collectionItemDto)

Sammlung importieren

### Example

```ts
import {
  Configuration,
  CollectionApi,
} from 'cardyssey-contract';
import type { ImportCollectionRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CollectionApi(config);

  const body = {
    // Array<CollectionItemDto>
    collectionItemDto: ...,
  } satisfies ImportCollectionRequest;

  try {
    const data = await api.importCollection(body);
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
| **collectionItemDto** | `Array<CollectionItemDto>` |  | |

### Return type

[**CollectionImportResponse**](CollectionImportResponse.md)

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


## updateCollectionItem

> CollectionWriteResponse updateCollectionItem(key, collectionItemDto)

Sammlungseintrag aktualisieren

### Example

```ts
import {
  Configuration,
  CollectionApi,
} from 'cardyssey-contract';
import type { UpdateCollectionItemRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CollectionApi(config);

  const body = {
    // string
    key: key_example,
    // CollectionItemDto
    collectionItemDto: ...,
  } satisfies UpdateCollectionItemRequest;

  try {
    const data = await api.updateCollectionItem(body);
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
| **key** | `string` |  | [Defaults to `undefined`] |
| **collectionItemDto** | [CollectionItemDto](CollectionItemDto.md) |  | |

### Return type

[**CollectionWriteResponse**](CollectionWriteResponse.md)

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

