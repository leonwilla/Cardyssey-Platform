# CatalogApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getCard**](CatalogApi.md#getcard) | **GET** /api/v1/cards/{id} | Kartendetails laden |
| [**getSet**](CatalogApi.md#getset) | **GET** /api/v1/sets/{id} | Setdetails laden |
| [**getSets**](CatalogApi.md#getsets) | **GET** /api/v1/sets | Sets laden |
| [**recognizeCard**](CatalogApi.md#recognizecard) | **POST** /api/v1/cards/recognize | OCR-Text analysieren |
| [**searchCards**](CatalogApi.md#searchcards) | **GET** /api/v1/cards/search | Karten suchen |



## getCard

> CatalogCardDetails getCard(id, language)

Kartendetails laden

### Example

```ts
import {
  Configuration,
  CatalogApi,
} from 'cardyssey-contract';
import type { GetCardRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CatalogApi(config);

  const body = {
    // string
    id: id_example,
    // 'de' | 'en' | 'fr' | 'it' | 'es' | 'pt' | 'ja' | 'ko' | 'zh-tw' | 'zh-cn' (optional)
    language: language_example,
  } satisfies GetCardRequest;

  try {
    const data = await api.getCard(body);
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
| **language** | `de`, `en`, `fr`, `it`, `es`, `pt`, `ja`, `ko`, `zh-tw`, `zh-cn` |  | [Optional] [Defaults to `&#39;de&#39;`] [Enum: de, en, fr, it, es, pt, ja, ko, zh-tw, zh-cn] |

### Return type

[**CatalogCardDetails**](CatalogCardDetails.md)

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


## getSet

> CatalogSetDetails getSet(id, language)

Setdetails laden

### Example

```ts
import {
  Configuration,
  CatalogApi,
} from 'cardyssey-contract';
import type { GetSetRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CatalogApi(config);

  const body = {
    // string
    id: id_example,
    // 'de' | 'en' | 'fr' | 'it' | 'es' | 'pt' | 'ja' | 'ko' | 'zh-tw' | 'zh-cn' (optional)
    language: language_example,
  } satisfies GetSetRequest;

  try {
    const data = await api.getSet(body);
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
| **language** | `de`, `en`, `fr`, `it`, `es`, `pt`, `ja`, `ko`, `zh-tw`, `zh-cn` |  | [Optional] [Defaults to `&#39;de&#39;`] [Enum: de, en, fr, it, es, pt, ja, ko, zh-tw, zh-cn] |

### Return type

[**CatalogSetDetails**](CatalogSetDetails.md)

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


## getSets

> Array&lt;CatalogSetSummary&gt; getSets(language)

Sets laden

### Example

```ts
import {
  Configuration,
  CatalogApi,
} from 'cardyssey-contract';
import type { GetSetsRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CatalogApi(config);

  const body = {
    // 'de' | 'en' | 'fr' | 'it' | 'es' | 'pt' | 'ja' | 'ko' | 'zh-tw' | 'zh-cn' (optional)
    language: language_example,
  } satisfies GetSetsRequest;

  try {
    const data = await api.getSets(body);
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
| **language** | `de`, `en`, `fr`, `it`, `es`, `pt`, `ja`, `ko`, `zh-tw`, `zh-cn` |  | [Optional] [Defaults to `&#39;de&#39;`] [Enum: de, en, fr, it, es, pt, ja, ko, zh-tw, zh-cn] |

### Return type

[**Array&lt;CatalogSetSummary&gt;**](CatalogSetSummary.md)

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


## recognizeCard

> CardRecognitionResponse recognizeCard(cardRecognitionRequest)

OCR-Text analysieren

### Example

```ts
import {
  Configuration,
  CatalogApi,
} from 'cardyssey-contract';
import type { RecognizeCardRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CatalogApi(config);

  const body = {
    // CardRecognitionRequest
    cardRecognitionRequest: ...,
  } satisfies RecognizeCardRequest;

  try {
    const data = await api.recognizeCard(body);
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
| **cardRecognitionRequest** | [CardRecognitionRequest](CardRecognitionRequest.md) |  | |

### Return type

[**CardRecognitionResponse**](CardRecognitionResponse.md)

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


## searchCards

> Array&lt;CatalogCardSearchResult&gt; searchCards(q, number, language, limit)

Karten suchen

### Example

```ts
import {
  Configuration,
  CatalogApi,
} from 'cardyssey-contract';
import type { SearchCardsRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new CatalogApi(config);

  const body = {
    // string (optional)
    q: q_example,
    // string (optional)
    number: number_example,
    // 'de' | 'en' | 'fr' | 'it' | 'es' | 'pt' | 'ja' | 'ko' | 'zh-tw' | 'zh-cn' (optional)
    language: language_example,
    // number (optional)
    limit: 56,
  } satisfies SearchCardsRequest;

  try {
    const data = await api.searchCards(body);
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
| **q** | `string` |  | [Optional] [Defaults to `undefined`] |
| **number** | `string` |  | [Optional] [Defaults to `undefined`] |
| **language** | `de`, `en`, `fr`, `it`, `es`, `pt`, `ja`, `ko`, `zh-tw`, `zh-cn` |  | [Optional] [Defaults to `&#39;de&#39;`] [Enum: de, en, fr, it, es, pt, ja, ko, zh-tw, zh-cn] |
| **limit** | `number` |  | [Optional] [Defaults to `20`] |

### Return type

[**Array&lt;CatalogCardSearchResult&gt;**](CatalogCardSearchResult.md)

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

