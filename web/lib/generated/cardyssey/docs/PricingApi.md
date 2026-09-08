# PricingApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getCardPriceQuote**](PricingApi.md#getcardpricequote) | **GET** /api/v1/pricing/cards/{id} | Zentralen Marktpreis für eine exakte Kartenvariante laden |



## getCardPriceQuote

> CardPriceQuoteResponse getCardPriceQuote(id, language, variantId, variant, condition, market)

Zentralen Marktpreis für eine exakte Kartenvariante laden

### Example

```ts
import {
  Configuration,
  PricingApi,
} from 'cardyssey-contract';
import type { GetCardPriceQuoteRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new PricingApi(config);

  const body = {
    // string
    id: id_example,
    // string (optional)
    language: language_example,
    // string (optional)
    variantId: variantId_example,
    // 'NORMAL' | 'REVERSE' | 'HOLO' | 'FIRST_EDITION' (optional)
    variant: variant_example,
    // 'MINT' | 'NEAR_MINT' | 'EXCELLENT' | 'GOOD' | 'PLAYED' (optional)
    condition: condition_example,
    // 'TCG' | 'EBAY' (optional)
    market: market_example,
  } satisfies GetCardPriceQuoteRequest;

  try {
    const data = await api.getCardPriceQuote(body);
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
| **language** | `string` |  | [Optional] [Defaults to `&#39;de&#39;`] |
| **variantId** | `string` |  | [Optional] [Defaults to `undefined`] |
| **variant** | `NORMAL`, `REVERSE`, `HOLO`, `FIRST_EDITION` |  | [Optional] [Defaults to `undefined`] [Enum: NORMAL, REVERSE, HOLO, FIRST_EDITION] |
| **condition** | `MINT`, `NEAR_MINT`, `EXCELLENT`, `GOOD`, `PLAYED` |  | [Optional] [Defaults to `&#39;NEAR_MINT&#39;`] [Enum: MINT, NEAR_MINT, EXCELLENT, GOOD, PLAYED] |
| **market** | `TCG`, `EBAY` |  | [Optional] [Defaults to `&#39;TCG&#39;`] [Enum: TCG, EBAY] |

### Return type

[**CardPriceQuoteResponse**](CardPriceQuoteResponse.md)

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

