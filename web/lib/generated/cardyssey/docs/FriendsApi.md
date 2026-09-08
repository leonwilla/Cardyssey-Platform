# FriendsApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**acceptFriendRequest**](FriendsApi.md#acceptfriendrequest) | **POST** /api/v1/friends/requests/{id}/accept | Freundschaftsanfrage annehmen |
| [**deleteFriend**](FriendsApi.md#deletefriend) | **DELETE** /api/v1/friends/{friendCode} | Freund entfernen |
| [**deleteFriendRequest**](FriendsApi.md#deletefriendrequest) | **DELETE** /api/v1/friends/requests/{id} | Freundschaftsanfrage löschen |
| [**getFriendCollection**](FriendsApi.md#getfriendcollection) | **GET** /api/v1/friends/{friendCode}/collection | Sammlung eines Freundes |
| [**getFriendProfile**](FriendsApi.md#getfriendprofile) | **GET** /api/v1/friends/{friendCode}/profile | Freundesprofil laden |
| [**getFriendRequests**](FriendsApi.md#getfriendrequests) | **GET** /api/v1/friends/requests | Freundschaftsanfragen laden |
| [**getFriendSets**](FriendsApi.md#getfriendsets) | **GET** /api/v1/friends/{friendCode}/sets | Set-Fortschritt eines Freundes |
| [**getFriendShowcase**](FriendsApi.md#getfriendshowcase) | **GET** /api/v1/friends/{friendCode}/showcase | Showcase eines Freundes |
| [**getFriendWishlist**](FriendsApi.md#getfriendwishlist) | **GET** /api/v1/friends/{friendCode}/wishlist | Wishlist eines Freundes |
| [**getFriends**](FriendsApi.md#getfriends) | **GET** /api/v1/friends | Freundesliste laden |
| [**searchFriends**](FriendsApi.md#searchfriends) | **GET** /api/v1/friends/search | Sammler suchen |
| [**sendFriendRequest**](FriendsApi.md#sendfriendrequest) | **POST** /api/v1/friends/requests | Freundschaftsanfrage senden |



## acceptFriendRequest

> FriendUserResponse acceptFriendRequest(id)

Freundschaftsanfrage annehmen

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { AcceptFriendRequestRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    id: id_example,
  } satisfies AcceptFriendRequestRequest;

  try {
    const data = await api.acceptFriendRequest(body);
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

[**FriendUserResponse**](FriendUserResponse.md)

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


## deleteFriend

> deleteFriend(friendCode)

Freund entfernen

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { DeleteFriendRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    friendCode: friendCode_example,
  } satisfies DeleteFriendRequest;

  try {
    const data = await api.deleteFriend(body);
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
| **friendCode** | `string` |  | [Defaults to `undefined`] |

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


## deleteFriendRequest

> deleteFriendRequest(id)

Freundschaftsanfrage löschen

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { DeleteFriendRequestRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    id: id_example,
  } satisfies DeleteFriendRequestRequest;

  try {
    const data = await api.deleteFriendRequest(body);
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


## getFriendCollection

> FriendCollectionResponse getFriendCollection(friendCode)

Sammlung eines Freundes

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { GetFriendCollectionRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    friendCode: friendCode_example,
  } satisfies GetFriendCollectionRequest;

  try {
    const data = await api.getFriendCollection(body);
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
| **friendCode** | `string` |  | [Defaults to `undefined`] |

### Return type

[**FriendCollectionResponse**](FriendCollectionResponse.md)

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


## getFriendProfile

> FriendProfileResponse getFriendProfile(friendCode)

Freundesprofil laden

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { GetFriendProfileRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    friendCode: friendCode_example,
  } satisfies GetFriendProfileRequest;

  try {
    const data = await api.getFriendProfile(body);
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
| **friendCode** | `string` |  | [Defaults to `undefined`] |

### Return type

[**FriendProfileResponse**](FriendProfileResponse.md)

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


## getFriendRequests

> FriendRequestsResponse getFriendRequests()

Freundschaftsanfragen laden

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { GetFriendRequestsRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  try {
    const data = await api.getFriendRequests();
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

[**FriendRequestsResponse**](FriendRequestsResponse.md)

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


## getFriendSets

> Array&lt;FriendSetProgressResponse&gt; getFriendSets(friendCode)

Set-Fortschritt eines Freundes

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { GetFriendSetsRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    friendCode: friendCode_example,
  } satisfies GetFriendSetsRequest;

  try {
    const data = await api.getFriendSets(body);
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
| **friendCode** | `string` |  | [Defaults to `undefined`] |

### Return type

[**Array&lt;FriendSetProgressResponse&gt;**](FriendSetProgressResponse.md)

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


## getFriendShowcase

> Array&lt;ShowcaseItemResponse&gt; getFriendShowcase(friendCode)

Showcase eines Freundes

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { GetFriendShowcaseRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    friendCode: friendCode_example,
  } satisfies GetFriendShowcaseRequest;

  try {
    const data = await api.getFriendShowcase(body);
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
| **friendCode** | `string` |  | [Defaults to `undefined`] |

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


## getFriendWishlist

> Array&lt;WishlistResponse&gt; getFriendWishlist(friendCode)

Wishlist eines Freundes

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { GetFriendWishlistRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    friendCode: friendCode_example,
  } satisfies GetFriendWishlistRequest;

  try {
    const data = await api.getFriendWishlist(body);
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
| **friendCode** | `string` |  | [Defaults to `undefined`] |

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


## getFriends

> Array&lt;FriendUserResponse&gt; getFriends()

Freundesliste laden

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { GetFriendsRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  try {
    const data = await api.getFriends();
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

[**Array&lt;FriendUserResponse&gt;**](FriendUserResponse.md)

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


## searchFriends

> Array&lt;FriendUserResponse&gt; searchFriends(q)

Sammler suchen

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { SearchFriendsRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // string
    q: q_example,
  } satisfies SearchFriendsRequest;

  try {
    const data = await api.searchFriends(body);
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
| **q** | `string` |  | [Defaults to `undefined`] |

### Return type

[**Array&lt;FriendUserResponse&gt;**](FriendUserResponse.md)

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


## sendFriendRequest

> FriendRequestResponse sendFriendRequest(sendFriendRequest)

Freundschaftsanfrage senden

### Example

```ts
import {
  Configuration,
  FriendsApi,
} from 'cardyssey-contract';
import type { SendFriendRequestRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new FriendsApi(config);

  const body = {
    // SendFriendRequest
    sendFriendRequest: ...,
  } satisfies SendFriendRequestRequest;

  try {
    const data = await api.sendFriendRequest(body);
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
| **sendFriendRequest** | [SendFriendRequest](SendFriendRequest.md) |  | |

### Return type

[**FriendRequestResponse**](FriendRequestResponse.md)

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

