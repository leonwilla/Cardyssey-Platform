# WishlistApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createWishlistItem**](WishlistApi.md#createwishlistitem) | **POST** /api/v1/wishlist | Wishlist-Eintrag anlegen |
| [**deleteWishlistItem**](WishlistApi.md#deletewishlistitem) | **DELETE** /api/v1/wishlist/{id} | Wishlist-Eintrag löschen |
| [**getWishlist**](WishlistApi.md#getwishlist) | **GET** /api/v1/wishlist | Wishlist laden |



## createWishlistItem

> WishlistResponse createWishlistItem(createWishlistRequest)

Wishlist-Eintrag anlegen

### Example

```ts
import {
  Configuration,
  WishlistApi,
} from 'cardyssey-contract';
import type { CreateWishlistItemRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new WishlistApi(config);

  const body = {
    // CreateWishlistRequest
    createWishlistRequest: ...,
  } satisfies CreateWishlistItemRequest;

  try {
    const data = await api.createWishlistItem(body);
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
| **createWishlistRequest** | [CreateWishlistRequest](CreateWishlistRequest.md) |  | |

### Return type

[**WishlistResponse**](WishlistResponse.md)

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


## deleteWishlistItem

> deleteWishlistItem(id)

Wishlist-Eintrag löschen

### Example

```ts
import {
  Configuration,
  WishlistApi,
} from 'cardyssey-contract';
import type { DeleteWishlistItemRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new WishlistApi(config);

  const body = {
    // string
    id: id_example,
  } satisfies DeleteWishlistItemRequest;

  try {
    const data = await api.deleteWishlistItem(body);
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


## getWishlist

> Array&lt;WishlistResponse&gt; getWishlist()

Wishlist laden

### Example

```ts
import {
  Configuration,
  WishlistApi,
} from 'cardyssey-contract';
import type { GetWishlistRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new WishlistApi(config);

  try {
    const data = await api.getWishlist();
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

[**Array&lt;WishlistResponse&gt;**](WishlistResponse.md)

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

