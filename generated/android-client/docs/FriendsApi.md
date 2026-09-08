# FriendsApi

All URIs are relative to *http://127.0.0.1:8081*

| Method | HTTP request | Description |
| ------------- | ------------- | ------------- |
| [**acceptFriendRequest**](FriendsApi.md#acceptFriendRequest) | **POST** /api/v1/friends/requests/{id}/accept | Freundschaftsanfrage annehmen |
| [**deleteFriend**](FriendsApi.md#deleteFriend) | **DELETE** /api/v1/friends/{friendCode} | Freund entfernen |
| [**deleteFriendRequest**](FriendsApi.md#deleteFriendRequest) | **DELETE** /api/v1/friends/requests/{id} | Freundschaftsanfrage löschen |
| [**getFriendCollection**](FriendsApi.md#getFriendCollection) | **GET** /api/v1/friends/{friendCode}/collection | Sammlung eines Freundes |
| [**getFriendProfile**](FriendsApi.md#getFriendProfile) | **GET** /api/v1/friends/{friendCode}/profile | Freundesprofil laden |
| [**getFriendRequests**](FriendsApi.md#getFriendRequests) | **GET** /api/v1/friends/requests | Freundschaftsanfragen laden |
| [**getFriendSets**](FriendsApi.md#getFriendSets) | **GET** /api/v1/friends/{friendCode}/sets | Set-Fortschritt eines Freundes |
| [**getFriendShowcase**](FriendsApi.md#getFriendShowcase) | **GET** /api/v1/friends/{friendCode}/showcase | Showcase eines Freundes |
| [**getFriendWishlist**](FriendsApi.md#getFriendWishlist) | **GET** /api/v1/friends/{friendCode}/wishlist | Wishlist eines Freundes |
| [**getFriends**](FriendsApi.md#getFriends) | **GET** /api/v1/friends | Freundesliste laden |
| [**searchFriends**](FriendsApi.md#searchFriends) | **GET** /api/v1/friends/search | Sammler suchen |
| [**sendFriendRequest**](FriendsApi.md#sendFriendRequest) | **POST** /api/v1/friends/requests | Freundschaftsanfrage senden |


<a id="acceptFriendRequest"></a>
# **acceptFriendRequest**
> FriendUserResponse acceptFriendRequest(id)

Freundschaftsanfrage annehmen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val id : kotlin.String = id_example // kotlin.String | 
try {
    val result : FriendUserResponse = apiInstance.acceptFriendRequest(id)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#acceptFriendRequest")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#acceptFriendRequest")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **id** | **kotlin.String**|  | |

### Return type

[**FriendUserResponse**](FriendUserResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="deleteFriend"></a>
# **deleteFriend**
> deleteFriend(friendCode)

Freund entfernen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val friendCode : kotlin.String = friendCode_example // kotlin.String | 
try {
    apiInstance.deleteFriend(friendCode)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#deleteFriend")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#deleteFriend")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **friendCode** | **kotlin.String**|  | |

### Return type

null (empty response body)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="deleteFriendRequest"></a>
# **deleteFriendRequest**
> deleteFriendRequest(id)

Freundschaftsanfrage löschen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val id : kotlin.String = id_example // kotlin.String | 
try {
    apiInstance.deleteFriendRequest(id)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#deleteFriendRequest")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#deleteFriendRequest")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **id** | **kotlin.String**|  | |

### Return type

null (empty response body)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="getFriendCollection"></a>
# **getFriendCollection**
> FriendCollectionResponse getFriendCollection(friendCode)

Sammlung eines Freundes

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val friendCode : kotlin.String = friendCode_example // kotlin.String | 
try {
    val result : FriendCollectionResponse = apiInstance.getFriendCollection(friendCode)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#getFriendCollection")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#getFriendCollection")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **friendCode** | **kotlin.String**|  | |

### Return type

[**FriendCollectionResponse**](FriendCollectionResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="getFriendProfile"></a>
# **getFriendProfile**
> FriendProfileResponse getFriendProfile(friendCode)

Freundesprofil laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val friendCode : kotlin.String = friendCode_example // kotlin.String | 
try {
    val result : FriendProfileResponse = apiInstance.getFriendProfile(friendCode)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#getFriendProfile")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#getFriendProfile")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **friendCode** | **kotlin.String**|  | |

### Return type

[**FriendProfileResponse**](FriendProfileResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="getFriendRequests"></a>
# **getFriendRequests**
> FriendRequestsResponse getFriendRequests()

Freundschaftsanfragen laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
try {
    val result : FriendRequestsResponse = apiInstance.getFriendRequests()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#getFriendRequests")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#getFriendRequests")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**FriendRequestsResponse**](FriendRequestsResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="getFriendSets"></a>
# **getFriendSets**
> kotlin.collections.List&lt;FriendSetProgressResponse&gt; getFriendSets(friendCode)

Set-Fortschritt eines Freundes

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val friendCode : kotlin.String = friendCode_example // kotlin.String | 
try {
    val result : kotlin.collections.List<FriendSetProgressResponse> = apiInstance.getFriendSets(friendCode)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#getFriendSets")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#getFriendSets")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **friendCode** | **kotlin.String**|  | |

### Return type

[**kotlin.collections.List&lt;FriendSetProgressResponse&gt;**](FriendSetProgressResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="getFriendShowcase"></a>
# **getFriendShowcase**
> kotlin.collections.List&lt;ShowcaseItemResponse&gt; getFriendShowcase(friendCode)

Showcase eines Freundes

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val friendCode : kotlin.String = friendCode_example // kotlin.String | 
try {
    val result : kotlin.collections.List<ShowcaseItemResponse> = apiInstance.getFriendShowcase(friendCode)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#getFriendShowcase")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#getFriendShowcase")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **friendCode** | **kotlin.String**|  | |

### Return type

[**kotlin.collections.List&lt;ShowcaseItemResponse&gt;**](ShowcaseItemResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="getFriendWishlist"></a>
# **getFriendWishlist**
> kotlin.collections.List&lt;WishlistResponse&gt; getFriendWishlist(friendCode)

Wishlist eines Freundes

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val friendCode : kotlin.String = friendCode_example // kotlin.String | 
try {
    val result : kotlin.collections.List<WishlistResponse> = apiInstance.getFriendWishlist(friendCode)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#getFriendWishlist")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#getFriendWishlist")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **friendCode** | **kotlin.String**|  | |

### Return type

[**kotlin.collections.List&lt;WishlistResponse&gt;**](WishlistResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="getFriends"></a>
# **getFriends**
> kotlin.collections.List&lt;FriendUserResponse&gt; getFriends()

Freundesliste laden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
try {
    val result : kotlin.collections.List<FriendUserResponse> = apiInstance.getFriends()
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#getFriends")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#getFriends")
    e.printStackTrace()
}
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**kotlin.collections.List&lt;FriendUserResponse&gt;**](FriendUserResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="searchFriends"></a>
# **searchFriends**
> kotlin.collections.List&lt;FriendUserResponse&gt; searchFriends(q)

Sammler suchen

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val q : kotlin.String = q_example // kotlin.String | 
try {
    val result : kotlin.collections.List<FriendUserResponse> = apiInstance.searchFriends(q)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#searchFriends")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#searchFriends")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **q** | **kotlin.String**|  | |

### Return type

[**kotlin.collections.List&lt;FriendUserResponse&gt;**](FriendUserResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

<a id="sendFriendRequest"></a>
# **sendFriendRequest**
> FriendRequestResponse sendFriendRequest(sendFriendRequest)

Freundschaftsanfrage senden

### Example
```kotlin
// Import classes:
//import de.cardyssey.generated.infrastructure.*
//import de.cardyssey.generated.models.*

val apiInstance = FriendsApi()
val sendFriendRequest : SendFriendRequest =  // SendFriendRequest | 
try {
    val result : FriendRequestResponse = apiInstance.sendFriendRequest(sendFriendRequest)
    println(result)
} catch (e: ClientException) {
    println("4xx response calling FriendsApi#sendFriendRequest")
    e.printStackTrace()
} catch (e: ServerException) {
    println("5xx response calling FriendsApi#sendFriendRequest")
    e.printStackTrace()
}
```

### Parameters
| Name | Type | Description  | Notes |
| ------------- | ------------- | ------------- | ------------- |
| **sendFriendRequest** | [**SendFriendRequest**](SendFriendRequest.md)|  | |

### Return type

[**FriendRequestResponse**](FriendRequestResponse.md)

### Authorization


Configure bearerAuth statically:
```kotlin
ApiClient.accessToken = ""
```
Configure bearerAuth dynamically:
```kotlin
apiInstance.accessTokenProvider = { "" }
```

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

