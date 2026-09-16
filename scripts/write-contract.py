from pathlib import Path
import json

OUT = Path("contracts/cardyssey.openapi.json")
PUBLIC_OUT = Path("web/public/contracts/cardyssey.openapi.json")

def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}

def arr(name):
    return {
        "type": "array",
        "items": ref(name)
    }

def string(nullable=False, default=None, enum=None):
    result = {"type": "string"}

    if nullable:
        result["nullable"] = True

    if default is not None:
        result["default"] = default

    if enum is not None:
        result["enum"] = enum

    return result

def integer(nullable=False, default=None, minimum=None, maximum=None, fmt="int32"):
    result = {
        "type": "integer",
        "format": fmt
    }

    if nullable:
        result["nullable"] = True

    if default is not None:
        result["default"] = default

    if minimum is not None:
        result["minimum"] = minimum

    if maximum is not None:
        result["maximum"] = maximum

    return result

def number(nullable=False):
    result = {
        "type": "number",
        "format": "double"
    }

    if nullable:
        result["nullable"] = True

    return result

def boolean(default=None):
    result = {
        "type": "boolean"
    }

    if default is not None:
        result["default"] = default

    return result

def obj(properties, required=None):
    result = {
        "type": "object",
        "properties": properties
    }

    if required:
        result["required"] = required

    return result

def map_of(value_schema):
    return {
        "type": "object",
        "additionalProperties": value_schema
    }

def body(name):
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": ref(name)
            }
        }
    }

def array_body(name):
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": arr(name)
            }
        }
    }


def binary_body():
    return {
        "required": True,
        "content": {
            "application/octet-stream": {
                "schema": {
                    "type": "string",
                    "format": "binary"
                }
            }
        }
    }

def response(schema=None, description="OK"):
    result = {
        "description": description
    }

    if schema is not None:
        result["content"] = {
            "application/json": {
                "schema": schema
            }
        }

    return result

def error_responses():
    return {
        "400": response(ref("ErrorResponse"), "Ungültige Anfrage"),
        "401": response(ref("ErrorResponse"), "Nicht authentifiziert"),
        "403": response(ref("ErrorResponse"), "Nicht erlaubt"),
        "404": response(ref("ErrorResponse"), "Nicht gefunden"),
        "409": response(ref("ErrorResponse"), "Konflikt")
    }

def operation(
    tag,
    operation_id,
    summary,
    success_schema=None,
    success_status="200",
    request_body=None,
    parameters=None,
    authenticated=True,
    no_content=False
):
    responses = error_responses()

    if no_content:
        responses[success_status] = response(
            None,
            "Erfolgreich"
        )
    else:
        responses[success_status] = response(
            success_schema,
            "Erfolgreich"
        )

    result = {
        "tags": [tag],
        "operationId": operation_id,
        "summary": summary,
        "responses": responses
    }

    if request_body is not None:
        result["requestBody"] = request_body

    if parameters:
        result["parameters"] = parameters

    if not authenticated:
        result["security"] = []

    return result

def path_param(name):
    return {
        "name": name,
        "in": "path",
        "required": True,
        "schema": string()
    }

def query_param(
    name,
    default=None,
    required=False,
    schema=None
):
    result = {
        "name": name,
        "in": "query",
        "required": required,
        "schema": schema or string()
    }

    if default is not None:
        result["schema"]["default"] = default

    return result


visibility = [
    "PRIVATE",
    "FRIENDS",
    "PUBLIC"
]

languages = [
    "de",
    "en",
    "fr",
    "it",
    "es",
    "pt",
    "ja",
    "ko",
    "zh-tw",
    "zh-cn"
]

schemas = {

    "ErrorResponse":
        obj(
            {
                "error": string()
            },
            ["error"]
        ),

    "HealthResponse":
        obj(
            {
                "status": string(),
                "database": string(),
                "service": string(),
                "version": string(),
                "justTcgConfigured": boolean(),
                "ebayPricingMode":
                    string(enum=["CARDYSSEY_DIRECT_ONLY"]),
                "ebayDirectEnabled": boolean(),
                "ebayDirectSessionConfigured": boolean(),
                "ebayPriceCacheTtlHours":
                    integer(minimum=1)
            },
            [
                "status",
                "database",
                "service",
                "version",
                "justTcgConfigured",
                "ebayPricingMode",
                "ebayDirectEnabled",
                "ebayDirectSessionConfigured",
                "ebayPriceCacheTtlHours"
            ]
        ),

    "RegisterRequest":
        obj(
            {
                "email": string(),
                "password": string(),
                "displayName":
                    string(nullable=True)
            },
            [
                "email",
                "password"
            ]
        ),

    "LoginRequest":
        obj(
            {
                "email": string(),
                "password": string()
            },
            [
                "email",
                "password"
            ]
        ),

    "RefreshRequest":
        obj(
            {
                "refreshToken": string()
            },
            ["refreshToken"]
        ),

    "LogoutRequest":
        obj(
            {
                "refreshToken": string()
            },
            ["refreshToken"]
        ),

    "UpdateMeRequest":
        obj(
            {
                "displayName":
                    string(nullable=True)
            },
            ["displayName"]
        ),

    "UserResponse":
        obj(
            {
                "id": string(),
                "email": string(),
                "displayName":
                    string(nullable=True),

                "avatarUrl":
                    string(nullable=True),

                "friendCode":
                    string()
            },
            [
                "id",
                "email",
                "displayName",
                "avatarUrl"
            ]
        ),

    "AuthResponse":
        obj(
            {
                "accessToken":
                    string(),

                "accessTokenExpiresInSeconds":
                    integer(fmt="int64"),

                "refreshToken":
                    string(),

                "refreshTokenExpiresInSeconds":
                    integer(fmt="int64"),

                "user":
                    ref("UserResponse")
            },
            [
                "accessToken",
                "accessTokenExpiresInSeconds",
                "refreshToken",
                "refreshTokenExpiresInSeconds",
                "user"
            ]
        ),

    "VariantSpecDto":
        obj(
            {
                "id":
                    string(),

                "type":
                    string(),

                "foil":
                    string(nullable=True),

                "size":
                    string(nullable=True),

                "subtype":
                    string(nullable=True),

                "stamps":
                    {
                        "type": "array",
                        "items": string(),
                        "default": []
                    }
            },
            [
                "id",
                "type"
            ]
        ),

    "CollectionItemDto":
        obj(
            {
                "id":
                    string(nullable=True),

                "key":
                    string(),

                "cardId":
                    string(),

                "languageCode":
                    string(),

                "name":
                    string(),

                "setId":
                    string(nullable=True),

                "setName":
                    string(nullable=True),

                "localId":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True),

                "imageLanguage":
                    string(nullable=True),

                "variant":
                    string(),

                "variantSpec": {
                    **ref("VariantSpecDto"),
                    "nullable": True
                },

                "condition":
                    string(),

                "quantity":
                    integer(minimum=1),

                "unitEur":
                    number(nullable=True),

                "unitUsd":
                    number(nullable=True),

                "marketUnitEur":
                    map_of(number()),

                "marketUpdatedAtMs":
                    map_of(
                        integer(fmt="int64")
                    ),

                "marketSampleCount":
                    map_of(
                        integer()
                    )
            },
            [
                "key",
                "cardId",
                "languageCode",
                "name",
                "variant",
                "condition",
                "quantity"
            ]
        ),

    "CollectionImportResponse":
        obj(
            {
                "imported":
                    integer(),

                "total":
                    integer()
            },
            [
                "imported",
                "total"
            ]
        ),

    "CollectionWriteResponse":
        obj(
            {
                "status":
                    string(),

                "key":
                    string()
            },
            [
                "status",
                "key"
            ]
        ),

    "FriendUserResponse":
        obj(
            {
                "friendCode":
                    string(),

                "displayName":
                    string(nullable=True)
            },
            [
                "friendCode",
                "displayName"
            ]
        ),

    "FriendRequestResponse":
        obj(
            {
                "id":
                    string(),

                "user":
                    ref(
                        "FriendUserResponse"
                    ),

                "createdAt":
                    string()
            },
            [
                "id",
                "user",
                "createdAt"
            ]
        ),

    "FriendRequestsResponse":
        obj(
            {
                "incoming":
                    arr(
                        "FriendRequestResponse"
                    ),

                "outgoing":
                    arr(
                        "FriendRequestResponse"
                    )
            },
            [
                "incoming",
                "outgoing"
            ]
        ),

    "SendFriendRequest":
        obj(
            {
                "friendCode":
                    string()
            },
            ["friendCode"]
        ),

    "FriendSetProgressResponse":
        obj(
            {
                "setId":
                    string(),

                "setName":
                    string(nullable=True),

                "ownedCards":
                    integer(),

                "totalCards":
                    integer(nullable=True)
            },
            [
                "setId",
                "setName",
                "ownedCards",
                "totalCards"
            ]
        ),

    "FriendCollectionCardResponse":
        obj(
            {
                "cardId":
                    string(),

                "name":
                    string(),

                "setId":
                    string(nullable=True),

                "setName":
                    string(nullable=True),

                "localId":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True),

                "variant":
                    string(),

                "quantity":
                    integer(nullable=True)
            },
            [
                "cardId",
                "name",
                "setId",
                "setName",
                "localId",
                "imageBase",
                "variant",
                "quantity"
            ]
        ),

    "FriendCollectionResponse":
        obj(
            {
                "totalValueEur":
                    number(nullable=True),

                "cards":
                    arr(
                        "FriendCollectionCardResponse"
                    )
            },
            [
                "totalValueEur",
                "cards"
            ]
        ),

    "FriendProfileResponse":
        obj(
            {
                "friendCode":
                    string(),

                "displayName":
                    string(nullable=True),

                "avatarUrl":
                    string(nullable=True),

                "isFriend":
                    boolean(),

                "canSeeShowcase":
                    boolean(),

                "canSeeCollection":
                    boolean(),

                "canSeeCollectionValue":
                    boolean(),

                "canSeeQuantity":
                    boolean(),

                "canSeeSets":
                    boolean(),

                "canSeeWishlist":
                    boolean()
            },
            [
                "friendCode",
                "displayName",
                "avatarUrl",
                "isFriend",
                "canSeeShowcase",
                "canSeeCollection",
                "canSeeCollectionValue",
                "canSeeQuantity",
                "canSeeSets",
                "canSeeWishlist"
            ]
        ),

    "PrivacySettings":
        obj(
            {
                "profileVisibility":
                    string(
                        default="PUBLIC",
                        enum=visibility
                    ),

                "showcaseVisibility":
                    string(
                        default="PUBLIC",
                        enum=visibility
                    ),

                "collectionVisibility":
                    string(
                        default="FRIENDS",
                        enum=visibility
                    ),

                "collectionValueVisibility":
                    string(
                        default="PRIVATE",
                        enum=visibility
                    ),

                "quantityVisibility":
                    string(
                        default="PRIVATE",
                        enum=visibility
                    ),

                "setsVisibility":
                    string(
                        default="PUBLIC",
                        enum=visibility
                    ),

                "wishlistVisibility":
                    string(
                        default="FRIENDS",
                        enum=visibility
                    ),

                "showcaseSize":
                    integer(
                        default=5,
                        minimum=5,
                        maximum=10
                    )
            }
        ),

    "ShowcaseItemResponse":
        obj(
            {
                "collectionItemId":
                    string(),

                "position":
                    integer(),

                "cardId":
                    string(),

                "name":
                    string(),

                "setName":
                    string(nullable=True),

                "localId":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True),

                "variant":
                    string()
            },
            [
                "collectionItemId",
                "position",
                "cardId",
                "name",
                "setName",
                "localId",
                "imageBase",
                "variant"
            ]
        ),

    "UpdateShowcaseRequest":
        obj(
            {
                "collectionItemIds":
                    {
                        "type":
                            "array",
                        "items":
                            string()
                    }
            },
            [
                "collectionItemIds"
            ]
        ),

    "WishlistResponse":
        obj(
            {
                "id":
                    string(),

                "cardId":
                    string(),

                "languageCode":
                    string(),

                "name":
                    string(),

                "setId":
                    string(nullable=True),

                "setName":
                    string(nullable=True),

                "localId":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True),

                "variantId":
                    string(nullable=True),

                "variantType":
                    string(nullable=True),

                "variantSubtype":
                    string(nullable=True),

                "foil":
                    string(nullable=True),

                "size":
                    string(nullable=True),

                "stamps":
                    {
                        "type":
                            "array",
                        "items":
                            string()
                    }
            },
            [
                "id",
                "cardId",
                "languageCode",
                "name",
                "setId",
                "setName",
                "localId",
                "imageBase",
                "variantId",
                "variantType",
                "variantSubtype",
                "foil",
                "size",
                "stamps"
            ]
        ),

    "CreateWishlistRequest":
        obj(
            {
                "cardId":
                    string(),

                "languageCode":
                    string(default="de"),

                "name":
                    string(),

                "setId":
                    string(nullable=True),

                "setName":
                    string(nullable=True),

                "localId":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True),

                "variantId":
                    string(nullable=True),

                "variantType":
                    string(nullable=True),

                "variantSubtype":
                    string(nullable=True),

                "foil":
                    string(nullable=True),

                "size":
                    string(nullable=True),

                "stamps":
                    {
                        "type":
                            "array",
                        "items":
                            string(),
                        "default":
                            []
                    }
            },
            [
                "cardId",
                "name"
            ]
        ),

    "SaleListingResponse":
        obj(
            {
                "id":
                    string(),

                "collectionItemId":
                    string(),

                "cardId":
                    string(),

                "name":
                    string(),

                "setName":
                    string(nullable=True),

                "localId":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True),

                "variant":
                    string(),

                "condition":
                    string(),

                "ownedQuantity":
                    integer(),

                "quantity":
                    integer(),

                "priceEur":
                    number(nullable=True),

                "negotiable":
                    boolean(),

                "status":
                    string()
            },
            [
                "id",
                "collectionItemId",
                "cardId",
                "name",
                "setName",
                "localId",
                "imageBase",
                "variant",
                "condition",
                "ownedQuantity",
                "quantity",
                "priceEur",
                "negotiable",
                "status"
            ]
        ),

    "CreateSaleListingRequest":
        obj(
            {
                "collectionItemId":
                    string(),

                "quantity":
                    integer(
                        default=1,
                        minimum=1
                    ),

                "priceEur":
                    number(nullable=True),

                "negotiable":
                    boolean(default=True)
            },
            [
                "collectionItemId"
            ]
        ),

    "UpdateSaleListingRequest":
        obj(
            {
                "collectionItemId":
                    string(),

                "quantity":
                    integer(minimum=1),

                "priceEur":
                    number(nullable=True),

                "negotiable":
                    boolean(),

                "status":
                    string()
            },
            [
                "collectionItemId",
                "quantity",
                "negotiable",
                "status"
            ]
        ),

    "MarketplaceListingResponse":
        obj(
            {
                "id":
                    string(),

                "sellerFriendCode":
                    string(),

                "sellerDisplayName":
                    string(nullable=True),

                "cardId":
                    string(),

                "languageCode":
                    string(),

                "name":
                    string(),

                "setName":
                    string(nullable=True),

                "localId":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True),

                "variant":
                    string(),

                "condition":
                    string(),

                "quantity":
                    integer(),

                "priceEur":
                    number(nullable=True),

                "negotiable":
                    boolean()
            },
            [
                "id",
                "sellerFriendCode",
                "sellerDisplayName",
                "cardId",
                "languageCode",
                "name",
                "setName",
                "localId",
                "imageBase",
                "variant",
                "condition",
                "quantity",
                "priceEur",
                "negotiable"
            ]
        ),

    "CreateMarketplaceOfferRequest":
        obj(
            {
                "listingId":
                    string(),

                "quantity":
                    integer(
                        default=1,
                        minimum=1
                    ),

                "priceEur":
                    number(),

                "message":
                    string(nullable=True)
            },
            [
                "listingId",
                "priceEur"
            ]
        ),

    "MarketplaceOfferResponse":
        obj(
            {
                "id":
                    string(),

                "listingId":
                    string(),

                "buyerFriendCode":
                    string(),

                "buyerDisplayName":
                    string(nullable=True),

                "sellerFriendCode":
                    string(),

                "sellerDisplayName":
                    string(nullable=True),

                "cardId":
                    string(),

                "languageCode":
                    string(),

                "name":
                    string(),

                "setName":
                    string(nullable=True),

                "localId":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True),

                "variant":
                    string(),

                "condition":
                    string(),

                "quantity":
                    integer(minimum=1),

                "offerPriceEur":
                    number(),

                "listingPriceEur":
                    number(nullable=True),

                "message":
                    string(nullable=True),

                "status":
                    string(
                        enum=[
                            "PENDING",
                            "ACCEPTED",
                            "REJECTED",
                            "WITHDRAWN"
                        ]
                    ),

                "createdAt":
                    string(),

                "updatedAt":
                    string()
            },
            [
                "id",
                "listingId",
                "buyerFriendCode",
                "buyerDisplayName",
                "sellerFriendCode",
                "sellerDisplayName",
                "cardId",
                "languageCode",
                "name",
                "setName",
                "localId",
                "imageBase",
                "variant",
                "condition",
                "quantity",
                "offerPriceEur",
                "listingPriceEur",
                "message",
                "status",
                "createdAt",
                "updatedAt"
            ]
        ),

    "CatalogCardSearchResult":
        obj(
            {
                "id":
                    string(),

                "localId":
                    string(),

                "name":
                    string(),

                "setId":
                    string(),

                "setName":
                    string(nullable=True),

                "imageBase":
                    string(nullable=True)
            },
            [
                "id",
                "localId",
                "name",
                "setId",
                "setName",
                "imageBase"
            ]
        ),

    "CatalogVariant":
        obj(
            {
                "id":
                    string(),

                "type":
                    string(),

                "subtype":
                    string(nullable=True),

                "foil":
                    string(nullable=True),

                "size":
                    string(nullable=True),

                "stamps":
                    {
                        "type":
                            "array",
                        "items":
                            string()
                    },

                "legacyVariant":
                    string(),

                "tcgDexEur":
                    number(nullable=True)
            },
            [
                "id",
                "type",
                "subtype",
                "foil",
                "size",
                "stamps",
                "legacyVariant",
                "tcgDexEur"
            ]
        ),

    "CatalogCardDetails":
        obj(
            {
                "id":
                    string(),

                "localId":
                    string(),

                "name":
                    string(),

                "languageCode":
                    string(),

                "imageBase":
                    string(nullable=True),

                "imageLanguage":
                    string(nullable=True),

                "setId":
                    string(),

                "setName":
                    string(),

                "officialCount":
                    integer(),

                "rarity":
                    string(nullable=True),

                "variants":
                    arr(
                        "CatalogVariant"
                    )
            },
            [
                "id",
                "localId",
                "name",
                "languageCode",
                "imageBase",
                "imageLanguage",
                "setId",
                "setName",
                "officialCount",
                "rarity",
                "variants"
            ]
        ),

    "CatalogSetSummary":
        obj(
            {
                "id":
                    string(),

                "name":
                    string(),

                "logo":
                    string(nullable=True),

                "symbol":
                    string(nullable=True),

                "officialCount":
                    integer(),

                "totalCount":
                    integer()
            },
            [
                "id",
                "name",
                "logo",
                "symbol",
                "officialCount",
                "totalCount"
            ]
        ),

    "CatalogSetCard":
        obj(
            {
                "id":
                    string(),

                "localId":
                    string(),

                "name":
                    string(),

                "imageBase":
                    string(nullable=True)
            },
            [
                "id",
                "localId",
                "name",
                "imageBase"
            ]
        ),

    "CatalogSetDetails":
        obj(
            {
                "id":
                    string(),

                "name":
                    string(),

                "logo":
                    string(nullable=True),

                "symbol":
                    string(nullable=True),

                "officialCount":
                    integer(),

                "totalCount":
                    integer(),

                "cards":
                    arr(
                        "CatalogSetCard"
                    )
            },
            [
                "id",
                "name",
                "logo",
                "symbol",
                "officialCount",
                "totalCount",
                "cards"
            ]
        ),

    "CardRecognitionRequest":
        obj(
            {
                "text":
                    string(),

                "language":
                    string(
                        default="de",
                        enum=languages
                    )
            },
            ["text"]
        ),

    "CardRecognitionResponse":
        obj(
            {
                "detectedNumber":
                    string(nullable=True),

                "detectedQuery":
                    string(nullable=True),

                "candidates":
                    arr(
                        "CatalogCardSearchResult"
                    )
            },
            [
                "detectedNumber",
                "detectedQuery",
                "candidates"
            ]
        )
}


paths = {

    "/api/v1/health": {
        "get":
            operation(
                "System",
                "getHealth",
                "API-Status",
                ref("HealthResponse"),
                authenticated=False
            )
    },

    "/api/v1/auth/register": {
        "post":
            operation(
                "Auth",
                "register",
                "Account registrieren",
                ref("AuthResponse"),
                success_status="201",
                request_body=
                    body("RegisterRequest"),
                authenticated=False
            )
    },

    "/api/v1/auth/login": {
        "post":
            operation(
                "Auth",
                "login",
                "Anmelden",
                ref("AuthResponse"),
                request_body=
                    body("LoginRequest"),
                authenticated=False
            )
    },

    "/api/v1/auth/refresh": {
        "post":
            operation(
                "Auth",
                "refresh",
                "Tokens erneuern",
                ref("AuthResponse"),
                request_body=
                    body("RefreshRequest"),
                authenticated=False
            )
    },

    "/api/v1/auth/logout": {
        "post":
            operation(
                "Auth",
                "logout",
                "Refresh-Token widerrufen",
                success_status="204",
                request_body=
                    body("LogoutRequest"),
                authenticated=False,
                no_content=True
            )
    },

    "/api/v1/me": {
        "get":
            operation(
                "Account",
                "getMe",
                "Eigenes Profil laden",
                ref("UserResponse")
            ),

        "put":
            operation(
                "Account",
                "updateMe",
                "Eigenes Profil ändern",
                ref("UserResponse"),
                request_body=
                    body("UpdateMeRequest")
            )
    },

    "/api/v1/me/avatar": {
        "put":
            operation(
                "Account",
                "updateMyAvatar",
                "Profilbild hochladen",
                ref("UserResponse"),
                request_body=
                    binary_body()
            ),

        "delete":
            operation(
                "Account",
                "deleteMyAvatar",
                "Profilbild löschen",
                ref("UserResponse")
            )
    },

    "/api/v1/collection": {
        "get":
            operation(
                "Collection",
                "getCollection",
                "Sammlung laden",
                arr("CollectionItemDto")
            ),

        "post":
            operation(
                "Collection",
                "createCollectionItem",
                "Sammlungseintrag anlegen",
                ref(
                    "CollectionWriteResponse"
                ),
                success_status="201",
                request_body=
                    body(
                        "CollectionItemDto"
                    )
            )
    },

    "/api/v1/collection/{key}": {
        "put":
            operation(
                "Collection",
                "updateCollectionItem",
                "Sammlungseintrag aktualisieren",
                ref(
                    "CollectionWriteResponse"
                ),
                request_body=
                    body(
                        "CollectionItemDto"
                    ),
                parameters=[
                    path_param("key")
                ]
            ),

        "delete":
            operation(
                "Collection",
                "deleteCollectionItem",
                "Sammlungseintrag löschen",
                success_status="204",
                parameters=[
                    path_param("key")
                ],
                no_content=True
            )
    },

    "/api/v1/collection/import": {
        "post":
            operation(
                "Collection",
                "importCollection",
                "Sammlung importieren",
                ref(
                    "CollectionImportResponse"
                ),
                request_body=
                    array_body(
                        "CollectionItemDto"
                    )
            )
    },

    "/api/v1/friends": {
        "get":
            operation(
                "Friends",
                "getFriends",
                "Freundesliste laden",
                arr(
                    "FriendUserResponse"
                )
            )
    },

    "/api/v1/friends/search": {
        "get":
            operation(
                "Friends",
                "searchFriends",
                "Sammler suchen",
                arr(
                    "FriendUserResponse"
                ),
                parameters=[
                    query_param(
                        "q",
                        required=True
                    )
                ]
            )
    },

    "/api/v1/friends/requests": {
        "get":
            operation(
                "Friends",
                "getFriendRequests",
                "Freundschaftsanfragen laden",
                ref(
                    "FriendRequestsResponse"
                )
            ),

        "post":
            operation(
                "Friends",
                "sendFriendRequest",
                "Freundschaftsanfrage senden",
                ref(
                    "FriendRequestResponse"
                ),
                success_status="201",
                request_body=
                    body(
                        "SendFriendRequest"
                    )
            )
    },

    "/api/v1/friends/requests/{id}/accept": {
        "post":
            operation(
                "Friends",
                "acceptFriendRequest",
                "Freundschaftsanfrage annehmen",
                ref(
                    "FriendUserResponse"
                ),
                parameters=[
                    path_param("id")
                ]
            )
    },

    "/api/v1/friends/requests/{id}": {
        "delete":
            operation(
                "Friends",
                "deleteFriendRequest",
                "Freundschaftsanfrage löschen",
                success_status="204",
                parameters=[
                    path_param("id")
                ],
                no_content=True
            )
    },

    "/api/v1/friends/{friendCode}": {
        "delete":
            operation(
                "Friends",
                "deleteFriend",
                "Freund entfernen",
                success_status="204",
                parameters=[
                    path_param(
                        "friendCode"
                    )
                ],
                no_content=True
            )
    },

    "/api/v1/friends/{friendCode}/profile": {
        "get":
            operation(
                "Friends",
                "getFriendProfile",
                "Freundesprofil laden",
                ref(
                    "FriendProfileResponse"
                ),
                parameters=[
                    path_param(
                        "friendCode"
                    )
                ]
            )
    },

    "/api/v1/friends/{friendCode}/showcase": {
        "get":
            operation(
                "Friends",
                "getFriendShowcase",
                "Showcase eines Freundes",
                arr(
                    "ShowcaseItemResponse"
                ),
                parameters=[
                    path_param(
                        "friendCode"
                    )
                ]
            )
    },

    "/api/v1/friends/{friendCode}/collection": {
        "get":
            operation(
                "Friends",
                "getFriendCollection",
                "Sammlung eines Freundes",
                ref(
                    "FriendCollectionResponse"
                ),
                parameters=[
                    path_param(
                        "friendCode"
                    )
                ]
            )
    },

    "/api/v1/friends/{friendCode}/sets": {
        "get":
            operation(
                "Friends",
                "getFriendSets",
                "Set-Fortschritt eines Freundes",
                arr(
                    "FriendSetProgressResponse"
                ),
                parameters=[
                    path_param(
                        "friendCode"
                    )
                ]
            )
    },

    "/api/v1/friends/{friendCode}/wishlist": {
        "get":
            operation(
                "Friends",
                "getFriendWishlist",
                "Wishlist eines Freundes",
                arr(
                    "WishlistResponse"
                ),
                parameters=[
                    path_param(
                        "friendCode"
                    )
                ]
            )
    },

    "/api/v1/me/privacy": {
        "get":
            operation(
                "Privacy",
                "getPrivacy",
                "Privatsphäre laden",
                ref(
                    "PrivacySettings"
                )
            ),

        "put":
            operation(
                "Privacy",
                "updatePrivacy",
                "Privatsphäre speichern",
                ref(
                    "PrivacySettings"
                ),
                request_body=
                    body(
                        "PrivacySettings"
                    )
            )
    },

    "/api/v1/me/showcase": {
        "get":
            operation(
                "Showcase",
                "getShowcase",
                "Eigenes Showcase laden",
                arr(
                    "ShowcaseItemResponse"
                )
            ),

        "put":
            operation(
                "Showcase",
                "updateShowcase",
                "Eigenes Showcase speichern",
                arr(
                    "ShowcaseItemResponse"
                ),
                request_body=
                    body(
                        "UpdateShowcaseRequest"
                    )
            )
    },

    "/api/v1/wishlist": {
        "get":
            operation(
                "Wishlist",
                "getWishlist",
                "Wishlist laden",
                arr(
                    "WishlistResponse"
                )
            ),

        "post":
            operation(
                "Wishlist",
                "createWishlistItem",
                "Wishlist-Eintrag anlegen",
                ref(
                    "WishlistResponse"
                ),
                success_status="201",
                request_body=
                    body(
                        "CreateWishlistRequest"
                    )
            )
    },

    "/api/v1/wishlist/{id}": {
        "delete":
            operation(
                "Wishlist",
                "deleteWishlistItem",
                "Wishlist-Eintrag löschen",
                success_status="204",
                parameters=[
                    path_param("id")
                ],
                no_content=True
            )
    },

    "/api/v1/selling": {
        "get":
            operation(
                "Selling",
                "getSaleListings",
                "Eigene Verkaufsangebote",
                arr(
                    "SaleListingResponse"
                )
            ),

        "post":
            operation(
                "Selling",
                "createSaleListing",
                "Verkaufsangebot anlegen",
                success_status="201",
                request_body=
                    body(
                        "CreateSaleListingRequest"
                    ),
                no_content=True
            )
    },

    "/api/v1/selling/{id}": {
        "put":
            operation(
                "Selling",
                "updateSaleListing",
                "Verkaufsangebot ändern",
                success_status="204",
                request_body=
                    body(
                        "UpdateSaleListingRequest"
                    ),
                parameters=[
                    path_param("id")
                ],
                no_content=True
            ),

        "delete":
            operation(
                "Selling",
                "deleteSaleListing",
                "Verkaufsangebot löschen",
                success_status="204",
                parameters=[
                    path_param("id")
                ],
                no_content=True
            )
    },

    "/api/v1/marketplace": {
        "get":
            operation(
                "Marketplace",
                "getMarketplace",
                "Marktplatz laden",
                arr(
                    "MarketplaceListingResponse"
                )
            )
    },

    "/api/v1/offers/incoming": {
        "get":
            operation(
                "Offers",
                "getIncomingOffers",
                "Eingehende Angebote laden",
                arr(
                    "MarketplaceOfferResponse"
                )
            )
    },

    "/api/v1/offers/outgoing": {
        "get":
            operation(
                "Offers",
                "getOutgoingOffers",
                "Ausgehende Angebote laden",
                arr(
                    "MarketplaceOfferResponse"
                )
            )
    },

    "/api/v1/offers": {
        "post":
            operation(
                "Offers",
                "createOffer",
                "Angebot senden",
                ref(
                    "MarketplaceOfferResponse"
                ),
                success_status="201",
                request_body=
                    body(
                        "CreateMarketplaceOfferRequest"
                    )
            )
    },

    "/api/v1/offers/{id}/accept": {
        "post":
            operation(
                "Offers",
                "acceptOffer",
                "Angebot annehmen",
                ref(
                    "MarketplaceOfferResponse"
                ),
                parameters=[
                    path_param("id")
                ]
            )
    },

    "/api/v1/offers/{id}/reject": {
        "post":
            operation(
                "Offers",
                "rejectOffer",
                "Angebot ablehnen",
                ref(
                    "MarketplaceOfferResponse"
                ),
                parameters=[
                    path_param("id")
                ]
            )
    },

    "/api/v1/offers/{id}": {
        "delete":
            operation(
                "Offers",
                "withdrawOffer",
                "Angebot zurückziehen",
                success_status="204",
                parameters=[
                    path_param("id")
                ],
                no_content=True
            )
    },

    "/api/v1/cards/search": {
        "get":
            operation(
                "Catalog",
                "searchCards",
                "Karten suchen",
                arr(
                    "CatalogCardSearchResult"
                ),
                parameters=[
                    query_param("q"),
                    query_param("number"),
                    query_param(
                        "language",
                        default="de",
                        schema=string(
                            enum=languages
                        )
                    ),
                    query_param(
                        "limit",
                        default=20,
                        schema=integer(
                            minimum=1,
                            maximum=50
                        )
                    )
                ]
            )
    },

    "/api/v1/cards/{id}": {
        "get":
            operation(
                "Catalog",
                "getCard",
                "Kartendetails laden",
                ref(
                    "CatalogCardDetails"
                ),
                parameters=[
                    path_param("id"),
                    query_param(
                        "language",
                        default="de",
                        schema=string(
                            enum=languages
                        )
                    )
                ]
            )
    },

    "/api/v1/cards/recognize": {
        "post":
            operation(
                "Catalog",
                "recognizeCard",
                "OCR-Text analysieren",
                ref(
                    "CardRecognitionResponse"
                ),
                request_body=
                    body(
                        "CardRecognitionRequest"
                    )
            )
    },

    "/api/v1/sets": {
        "get":
            operation(
                "Catalog",
                "getSets",
                "Sets laden",
                arr(
                    "CatalogSetSummary"
                ),
                parameters=[
                    query_param(
                        "language",
                        default="de",
                        schema=string(
                            enum=languages
                        )
                    )
                ]
            )
    },

    "/api/v1/sets/{id}": {
        "get":
            operation(
                "Catalog",
                "getSet",
                "Setdetails laden",
                ref(
                    "CatalogSetDetails"
                ),
                parameters=[
                    path_param("id"),
                    query_param(
                        "language",
                        default="de",
                        schema=string(
                            enum=languages
                        )
                    )
                ]
            )
    }
}


document = {
    "openapi":
        "3.0.3",

    "info": {
        "title":
            "Cardyssey API",

        "version":
            "0.2.4",

        "description":
            "Zentraler API-Vertrag für Cardyssey Web, Android und Backend."
    },

    "servers": [
        {
            "url":
                "http://127.0.0.1:8081"
        }
    ],

    "security": [
        {
            "bearerAuth": []
        }
    ],

    "tags": [
        {"name": "System"},
        {"name": "Auth"},
        {"name": "Account"},
        {"name": "Collection"},
        {"name": "Friends"},
        {"name": "Privacy"},
        {"name": "Showcase"},
        {"name": "Wishlist"},
        {"name": "Selling"},
        {"name": "Marketplace"},
        {"name": "Offers"},
        {"name": "Catalog"}
    ],

    "paths":
        paths,

    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type":
                    "http",
                "scheme":
                    "bearer",
                "bearerFormat":
                    "JWT"
            }
        },

        "schemas":
            schemas
    }
}


# CENTRAL_PRICING_CONTRACT_V1
# Keep server-valued collection fields and the central Pricing API in the
# authoritative generator source so regeneration cannot silently drop them.
collection_properties = document["components"]["schemas"]["CollectionItemDto"]["properties"]
collection_properties["valuedUnitEur"] = map_of(number())
collection_properties["positionValueEur"] = map_of(number())

pricing_conditions = ["MINT", "NEAR_MINT", "EXCELLENT", "GOOD", "PLAYED"]
pricing_markets = ["TCG", "EBAY"]
pricing_sources = ["TCGDEX", "JUSTTCG", "CARDYSSEY_EBAY"]

document["components"]["schemas"]["EbayRecentSaleResponse"] = obj(
    {
        "itemId": string(nullable=True),
        "title": string(),
        "soldPriceEur": number(),
        "rawCondition": string(nullable=True),
        "endedAt": string(nullable=True),
        "url": string(nullable=True)
    },
    [
        "title",
        "soldPriceEur"
    ]
)

document["components"]["schemas"]["CardPriceQuoteResponse"] = obj(
    {
        "cardId": string(),
        "languageCode": string(),
        "variantId": string(nullable=True),
        "variantType": string(nullable=True),
        "condition": string(enum=pricing_conditions),
        "market": string(enum=pricing_markets),
        "source": string(nullable=True, enum=pricing_sources),
        "baseEur": number(nullable=True),
        "conditionFactor": number(),
        "eur": number(nullable=True),
        "exactLanguageMatch": boolean(),
        "exactVariantMatch": boolean(),
        "sampleCount": integer(nullable=True, minimum=0),
        "rangeLowEur": number(nullable=True),
        "rangeHighEur": number(nullable=True),
        "updatedAtMs": integer(nullable=True, minimum=0, fmt="int64"),
        "recentSales":
            arr("EbayRecentSaleResponse")
    },
    [
        "cardId",
        "languageCode",
        "condition",
        "market",
        "conditionFactor",
        "exactLanguageMatch",
        "exactVariantMatch",
        "recentSales"
    ]
)

if not any(tag.get("name") == "Pricing" for tag in document["tags"]):
    document["tags"].append({"name": "Pricing"})

document["paths"]["/api/v1/pricing/cards/{id}"] = {
    "get": operation(
        "Pricing",
        "getCardPriceQuote",
        "Zentralen Marktpreis für eine exakte Kartenvariante laden",
        ref("CardPriceQuoteResponse"),
        parameters=[
            path_param("id"),
            query_param("language", default="de"),
            query_param("variantId"),
            query_param(
                "variant",
                schema=string(enum=["NORMAL", "REVERSE", "HOLO", "FIRST_EDITION"])
            ),
            query_param(
                "condition",
                default="NEAR_MINT",
                schema=string(enum=pricing_conditions)
            ),
            query_param(
                "market",
                default="TCG",
                schema=string(enum=pricing_markets)
            )
        ]
    )
}

OUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

payload = (
    json.dumps(
        document,
        indent=2,
        ensure_ascii=False
    )
    + "\n"
)

OUT.write_text(payload)

PUBLIC_OUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

PUBLIC_OUT.write_text(payload)

print(
    f"OpenAPI geschrieben: {OUT}"
)

print(
    f"OpenAPI öffentlich: {PUBLIC_OUT}"
)

print(
    f"Paths: {len(paths)}"
)

print(
    f"Schemas: {len(schemas)}"
)
