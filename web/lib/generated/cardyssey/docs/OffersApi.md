# OffersApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**acceptOffer**](OffersApi.md#acceptoffer) | **POST** /api/v1/offers/{id}/accept | Angebot annehmen |
| [**createOffer**](OffersApi.md#createoffer) | **POST** /api/v1/offers | Angebot senden |
| [**getIncomingOffers**](OffersApi.md#getincomingoffers) | **GET** /api/v1/offers/incoming | Eingehende Angebote laden |
| [**getOutgoingOffers**](OffersApi.md#getoutgoingoffers) | **GET** /api/v1/offers/outgoing | Ausgehende Angebote laden |
| [**rejectOffer**](OffersApi.md#rejectoffer) | **POST** /api/v1/offers/{id}/reject | Angebot ablehnen |
| [**withdrawOffer**](OffersApi.md#withdrawoffer) | **DELETE** /api/v1/offers/{id} | Angebot zurückziehen |



## acceptOffer

> MarketplaceOfferResponse acceptOffer(id)

Angebot annehmen

### Example

```ts
import {
  Configuration,
  OffersApi,
} from 'cardyssey-contract';
import type { AcceptOfferRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new OffersApi(config);

  const body = {
    // string
    id: id_example,
  } satisfies AcceptOfferRequest;

  try {
    const data = await api.acceptOffer(body);
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

[**MarketplaceOfferResponse**](MarketplaceOfferResponse.md)

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


## createOffer

> MarketplaceOfferResponse createOffer(createMarketplaceOfferRequest)

Angebot senden

### Example

```ts
import {
  Configuration,
  OffersApi,
} from 'cardyssey-contract';
import type { CreateOfferRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new OffersApi(config);

  const body = {
    // CreateMarketplaceOfferRequest
    createMarketplaceOfferRequest: ...,
  } satisfies CreateOfferRequest;

  try {
    const data = await api.createOffer(body);
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
| **createMarketplaceOfferRequest** | [CreateMarketplaceOfferRequest](CreateMarketplaceOfferRequest.md) |  | |

### Return type

[**MarketplaceOfferResponse**](MarketplaceOfferResponse.md)

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


## getIncomingOffers

> Array&lt;MarketplaceOfferResponse&gt; getIncomingOffers()

Eingehende Angebote laden

### Example

```ts
import {
  Configuration,
  OffersApi,
} from 'cardyssey-contract';
import type { GetIncomingOffersRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new OffersApi(config);

  try {
    const data = await api.getIncomingOffers();
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

[**Array&lt;MarketplaceOfferResponse&gt;**](MarketplaceOfferResponse.md)

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


## getOutgoingOffers

> Array&lt;MarketplaceOfferResponse&gt; getOutgoingOffers()

Ausgehende Angebote laden

### Example

```ts
import {
  Configuration,
  OffersApi,
} from 'cardyssey-contract';
import type { GetOutgoingOffersRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new OffersApi(config);

  try {
    const data = await api.getOutgoingOffers();
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

[**Array&lt;MarketplaceOfferResponse&gt;**](MarketplaceOfferResponse.md)

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


## rejectOffer

> MarketplaceOfferResponse rejectOffer(id)

Angebot ablehnen

### Example

```ts
import {
  Configuration,
  OffersApi,
} from 'cardyssey-contract';
import type { RejectOfferRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new OffersApi(config);

  const body = {
    // string
    id: id_example,
  } satisfies RejectOfferRequest;

  try {
    const data = await api.rejectOffer(body);
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

[**MarketplaceOfferResponse**](MarketplaceOfferResponse.md)

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


## withdrawOffer

> withdrawOffer(id)

Angebot zurückziehen

### Example

```ts
import {
  Configuration,
  OffersApi,
} from 'cardyssey-contract';
import type { WithdrawOfferRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new OffersApi(config);

  const body = {
    // string
    id: id_example,
  } satisfies WithdrawOfferRequest;

  try {
    const data = await api.withdrawOffer(body);
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

