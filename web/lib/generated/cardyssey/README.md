# cardyssey-contract@0.2.0

A TypeScript SDK client for the 127.0.0.1 API.

## Usage

First, install the SDK from npm.

```bash
npm install cardyssey-contract --save
```

Next, try it out.


```ts
import {
  Configuration,
  AccountApi,
} from 'cardyssey-contract';
import type { DeleteMyAvatarRequest } from 'cardyssey-contract';

async function example() {
  console.log("🚀 Testing cardyssey-contract SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: bearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new AccountApi(config);

  try {
    const data = await api.deleteMyAvatar();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```


## Documentation

### API Endpoints

All URIs are relative to *http://127.0.0.1:8081*

| Class | Method | HTTP request | Description
| ----- | ------ | ------------ | -------------
*AccountApi* | [**deleteMyAvatar**](docs/AccountApi.md#deletemyavatar) | **DELETE** /api/v1/me/avatar | Profilbild löschen
*AccountApi* | [**getMe**](docs/AccountApi.md#getme) | **GET** /api/v1/me | Eigenes Profil laden
*AccountApi* | [**updateMe**](docs/AccountApi.md#updatemeoperation) | **PUT** /api/v1/me | Eigenes Profil ändern
*AccountApi* | [**updateMyAvatar**](docs/AccountApi.md#updatemyavatar) | **PUT** /api/v1/me/avatar | Profilbild hochladen
*AdminApi* | [**getAdminAccess**](docs/AdminApi.md#getadminaccess) | **GET** /api/v1/admin/access | Eigene Admin-/Founder-Berechtigung laden
*AdminApi* | [**getAdminOverview**](docs/AdminApi.md#getadminoverview) | **GET** /api/v1/admin/overview | Control-Center-Übersicht laden
*AdminApi* | [**getAdminUser**](docs/AdminApi.md#getadminuser) | **GET** /api/v1/admin/users/{id} | Read-only Nutzerdetails laden
*AdminApi* | [**getAdminUsers**](docs/AdminApi.md#getadminusers) | **GET** /api/v1/admin/users | Nutzer für das Control Center laden
*AdminApi* | [**getFounderSystem**](docs/AdminApi.md#getfoundersystem) | **GET** /api/v1/admin/system | Founder-Systemstatus laden
*AuthApi* | [**login**](docs/AuthApi.md#loginoperation) | **POST** /api/v1/auth/login | Anmelden
*AuthApi* | [**logout**](docs/AuthApi.md#logoutoperation) | **POST** /api/v1/auth/logout | Refresh-Token widerrufen
*AuthApi* | [**refresh**](docs/AuthApi.md#refreshoperation) | **POST** /api/v1/auth/refresh | Tokens erneuern
*AuthApi* | [**register**](docs/AuthApi.md#registeroperation) | **POST** /api/v1/auth/register | Account registrieren
*CatalogApi* | [**getCard**](docs/CatalogApi.md#getcard) | **GET** /api/v1/cards/{id} | Kartendetails laden
*CatalogApi* | [**getSet**](docs/CatalogApi.md#getset) | **GET** /api/v1/sets/{id} | Setdetails laden
*CatalogApi* | [**getSets**](docs/CatalogApi.md#getsets) | **GET** /api/v1/sets | Sets laden
*CatalogApi* | [**recognizeCard**](docs/CatalogApi.md#recognizecard) | **POST** /api/v1/cards/recognize | OCR-Text analysieren
*CatalogApi* | [**searchCards**](docs/CatalogApi.md#searchcards) | **GET** /api/v1/cards/search | Karten suchen
*CollectionApi* | [**createCollectionItem**](docs/CollectionApi.md#createcollectionitem) | **POST** /api/v1/collection | Sammlungseintrag anlegen
*CollectionApi* | [**deleteCollectionItem**](docs/CollectionApi.md#deletecollectionitem) | **DELETE** /api/v1/collection/{key} | Sammlungseintrag löschen
*CollectionApi* | [**getCollection**](docs/CollectionApi.md#getcollection) | **GET** /api/v1/collection | Sammlung laden
*CollectionApi* | [**importCollection**](docs/CollectionApi.md#importcollection) | **POST** /api/v1/collection/import | Sammlung importieren
*CollectionApi* | [**updateCollectionItem**](docs/CollectionApi.md#updatecollectionitem) | **PUT** /api/v1/collection/{key} | Sammlungseintrag aktualisieren
*FriendsApi* | [**acceptFriendRequest**](docs/FriendsApi.md#acceptfriendrequest) | **POST** /api/v1/friends/requests/{id}/accept | Freundschaftsanfrage annehmen
*FriendsApi* | [**deleteFriend**](docs/FriendsApi.md#deletefriend) | **DELETE** /api/v1/friends/{friendCode} | Freund entfernen
*FriendsApi* | [**deleteFriendRequest**](docs/FriendsApi.md#deletefriendrequest) | **DELETE** /api/v1/friends/requests/{id} | Freundschaftsanfrage löschen
*FriendsApi* | [**getFriendCollection**](docs/FriendsApi.md#getfriendcollection) | **GET** /api/v1/friends/{friendCode}/collection | Sammlung eines Freundes
*FriendsApi* | [**getFriendProfile**](docs/FriendsApi.md#getfriendprofile) | **GET** /api/v1/friends/{friendCode}/profile | Freundesprofil laden
*FriendsApi* | [**getFriendRequests**](docs/FriendsApi.md#getfriendrequests) | **GET** /api/v1/friends/requests | Freundschaftsanfragen laden
*FriendsApi* | [**getFriendSets**](docs/FriendsApi.md#getfriendsets) | **GET** /api/v1/friends/{friendCode}/sets | Set-Fortschritt eines Freundes
*FriendsApi* | [**getFriendShowcase**](docs/FriendsApi.md#getfriendshowcase) | **GET** /api/v1/friends/{friendCode}/showcase | Showcase eines Freundes
*FriendsApi* | [**getFriendWishlist**](docs/FriendsApi.md#getfriendwishlist) | **GET** /api/v1/friends/{friendCode}/wishlist | Wishlist eines Freundes
*FriendsApi* | [**getFriends**](docs/FriendsApi.md#getfriends) | **GET** /api/v1/friends | Freundesliste laden
*FriendsApi* | [**searchFriends**](docs/FriendsApi.md#searchfriends) | **GET** /api/v1/friends/search | Sammler suchen
*FriendsApi* | [**sendFriendRequest**](docs/FriendsApi.md#sendfriendrequest) | **POST** /api/v1/friends/requests | Freundschaftsanfrage senden
*MarketplaceApi* | [**getMarketplace**](docs/MarketplaceApi.md#getmarketplace) | **GET** /api/v1/marketplace | Marktplatz laden
*OffersApi* | [**acceptOffer**](docs/OffersApi.md#acceptoffer) | **POST** /api/v1/offers/{id}/accept | Angebot annehmen
*OffersApi* | [**createOffer**](docs/OffersApi.md#createoffer) | **POST** /api/v1/offers | Angebot senden
*OffersApi* | [**getIncomingOffers**](docs/OffersApi.md#getincomingoffers) | **GET** /api/v1/offers/incoming | Eingehende Angebote laden
*OffersApi* | [**getOutgoingOffers**](docs/OffersApi.md#getoutgoingoffers) | **GET** /api/v1/offers/outgoing | Ausgehende Angebote laden
*OffersApi* | [**rejectOffer**](docs/OffersApi.md#rejectoffer) | **POST** /api/v1/offers/{id}/reject | Angebot ablehnen
*OffersApi* | [**withdrawOffer**](docs/OffersApi.md#withdrawoffer) | **DELETE** /api/v1/offers/{id} | Angebot zurückziehen
*PricingApi* | [**getCardPriceQuote**](docs/PricingApi.md#getcardpricequote) | **GET** /api/v1/pricing/cards/{id} | Zentralen Marktpreis für eine exakte Kartenvariante laden
*PrivacyApi* | [**getPrivacy**](docs/PrivacyApi.md#getprivacy) | **GET** /api/v1/me/privacy | Privatsphäre laden
*PrivacyApi* | [**updatePrivacy**](docs/PrivacyApi.md#updateprivacy) | **PUT** /api/v1/me/privacy | Privatsphäre speichern
*SellingApi* | [**createSaleListing**](docs/SellingApi.md#createsalelistingoperation) | **POST** /api/v1/selling | Verkaufsangebot anlegen
*SellingApi* | [**deleteSaleListing**](docs/SellingApi.md#deletesalelisting) | **DELETE** /api/v1/selling/{id} | Verkaufsangebot löschen
*SellingApi* | [**getSaleListings**](docs/SellingApi.md#getsalelistings) | **GET** /api/v1/selling | Eigene Verkaufsangebote
*SellingApi* | [**updateSaleListing**](docs/SellingApi.md#updatesalelistingoperation) | **PUT** /api/v1/selling/{id} | Verkaufsangebot ändern
*ShowcaseApi* | [**getShowcase**](docs/ShowcaseApi.md#getshowcase) | **GET** /api/v1/me/showcase | Eigenes Showcase laden
*ShowcaseApi* | [**updateShowcase**](docs/ShowcaseApi.md#updateshowcaseoperation) | **PUT** /api/v1/me/showcase | Eigenes Showcase speichern
*SystemApi* | [**getHealth**](docs/SystemApi.md#gethealth) | **GET** /api/v1/health | API-Status
*WishlistApi* | [**createWishlistItem**](docs/WishlistApi.md#createwishlistitem) | **POST** /api/v1/wishlist | Wishlist-Eintrag anlegen
*WishlistApi* | [**deleteWishlistItem**](docs/WishlistApi.md#deletewishlistitem) | **DELETE** /api/v1/wishlist/{id} | Wishlist-Eintrag löschen
*WishlistApi* | [**getWishlist**](docs/WishlistApi.md#getwishlist) | **GET** /api/v1/wishlist | Wishlist laden


### Models

- [AdminAccessResponse](docs/AdminAccessResponse.md)
- [AdminCollectionItemResponse](docs/AdminCollectionItemResponse.md)
- [AdminListingResponse](docs/AdminListingResponse.md)
- [AdminOverviewResponse](docs/AdminOverviewResponse.md)
- [AdminUserDetailResponse](docs/AdminUserDetailResponse.md)
- [AdminUserSummaryResponse](docs/AdminUserSummaryResponse.md)
- [AdminWishlistItemResponse](docs/AdminWishlistItemResponse.md)
- [AuthResponse](docs/AuthResponse.md)
- [CardPriceQuoteResponse](docs/CardPriceQuoteResponse.md)
- [CardRecognitionRequest](docs/CardRecognitionRequest.md)
- [CardRecognitionResponse](docs/CardRecognitionResponse.md)
- [CatalogCardDetails](docs/CatalogCardDetails.md)
- [CatalogCardSearchResult](docs/CatalogCardSearchResult.md)
- [CatalogSetCard](docs/CatalogSetCard.md)
- [CatalogSetDetails](docs/CatalogSetDetails.md)
- [CatalogSetSummary](docs/CatalogSetSummary.md)
- [CatalogVariant](docs/CatalogVariant.md)
- [CollectionImportResponse](docs/CollectionImportResponse.md)
- [CollectionItemDto](docs/CollectionItemDto.md)
- [CollectionWriteResponse](docs/CollectionWriteResponse.md)
- [CreateMarketplaceOfferRequest](docs/CreateMarketplaceOfferRequest.md)
- [CreateSaleListingRequest](docs/CreateSaleListingRequest.md)
- [CreateWishlistRequest](docs/CreateWishlistRequest.md)
- [EbayRecentSaleResponse](docs/EbayRecentSaleResponse.md)
- [ErrorResponse](docs/ErrorResponse.md)
- [FounderSystemResponse](docs/FounderSystemResponse.md)
- [FriendCollectionCardResponse](docs/FriendCollectionCardResponse.md)
- [FriendCollectionResponse](docs/FriendCollectionResponse.md)
- [FriendProfileResponse](docs/FriendProfileResponse.md)
- [FriendRequestResponse](docs/FriendRequestResponse.md)
- [FriendRequestsResponse](docs/FriendRequestsResponse.md)
- [FriendSetProgressResponse](docs/FriendSetProgressResponse.md)
- [FriendUserResponse](docs/FriendUserResponse.md)
- [HealthResponse](docs/HealthResponse.md)
- [LoginRequest](docs/LoginRequest.md)
- [LogoutRequest](docs/LogoutRequest.md)
- [MarketplaceListingResponse](docs/MarketplaceListingResponse.md)
- [MarketplaceOfferResponse](docs/MarketplaceOfferResponse.md)
- [PrivacySettings](docs/PrivacySettings.md)
- [RefreshRequest](docs/RefreshRequest.md)
- [RegisterRequest](docs/RegisterRequest.md)
- [SaleListingResponse](docs/SaleListingResponse.md)
- [SendFriendRequest](docs/SendFriendRequest.md)
- [ShowcaseItemResponse](docs/ShowcaseItemResponse.md)
- [UpdateMeRequest](docs/UpdateMeRequest.md)
- [UpdateSaleListingRequest](docs/UpdateSaleListingRequest.md)
- [UpdateShowcaseRequest](docs/UpdateShowcaseRequest.md)
- [UserResponse](docs/UserResponse.md)
- [VariantSpecDto](docs/VariantSpecDto.md)
- [WishlistResponse](docs/WishlistResponse.md)

### Authorization


Authentication schemes defined for the API:
<a id="bearerAuth"></a>
#### bearerAuth


- **Type**: HTTP Bearer Token authentication (JWT)

## About

This TypeScript SDK client supports the [Fetch API](https://fetch.spec.whatwg.org/)
and is automatically generated by the
[OpenAPI Generator](https://openapi-generator.tech) project:

- API version: `0.2.4`
- Package version: `0.2.0`
- Generator version: `7.24.0`
- Build package: `org.openapitools.codegen.languages.TypeScriptFetchClientCodegen`

The generated npm module supports the following:

- Environments
  * Node.js
  * Webpack
  * Browserify
- Language levels
  * ES5 - you must have a Promises/A+ library installed
  * ES6
- Module systems
  * CommonJS
  * ES6 module system


## Development

### Building

To build the TypeScript source code, you need to have Node.js and npm installed.
After cloning the repository, navigate to the project directory and run:

```bash
npm install
npm run build
```

### Publishing

Once you've built the package, you can publish it to npm:

```bash
npm publish
```

## License

[]()
