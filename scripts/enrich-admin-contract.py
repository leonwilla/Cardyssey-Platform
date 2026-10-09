from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contracts/cardyssey.openapi.json"
PUBLIC_OUT = ROOT / "web/public/contracts/cardyssey.openapi.json"


def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def nullable(schema):
    return {**schema, "nullable": True}


def obj(properties, required=None):
    result = {
        "type": "object",
        "properties": properties,
    }
    if required:
        result["required"] = required
    return result


def array(schema):
    return {
        "type": "array",
        "items": schema,
    }


def response(schema, description="Erfolgreich"):
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": schema,
            }
        },
    }


def admin_operation(operation_id, summary, schema, parameters=None):
    operation = {
        "tags": ["Admin"],
        "operationId": operation_id,
        "summary": summary,
        "responses": {
            "200": response(schema),
            "400": response(ref("ErrorResponse"), "Ungültige Anfrage"),
            "401": response(ref("ErrorResponse"), "Nicht authentifiziert"),
            "403": response(ref("ErrorResponse"), "Nicht erlaubt"),
            "404": response(ref("ErrorResponse"), "Nicht gefunden"),
        },
    }
    if parameters:
        operation["parameters"] = parameters
    return operation


spec = json.loads(OUT.read_text())
schemas = spec.setdefault("components", {}).setdefault("schemas", {})
paths = spec.setdefault("paths", {})

# Cardyssey's eBay pricing response additionally exposes the cleaned sold-price
# range. Keeping this enrichment here makes client generation safe even when an
# older checked-in base contract was produced before these optional fields.
pricing_quote = schemas.get("CardPriceQuoteResponse")
if pricing_quote is not None:
    pricing_properties = pricing_quote.setdefault("properties", {})
    pricing_properties["rangeLowEur"] = nullable({
        "type": "number",
        "format": "double",
    })
    pricing_properties["rangeHighEur"] = nullable({
        "type": "number",
        "format": "double",
    })

role = {
    "type": "string",
    "enum": ["USER", "ADMIN", "FOUNDER"],
}

schemas.update({
    "AdminAccessResponse": obj(
        {
            "role": role,
            "canAdmin": {"type": "boolean"},
            "canFounder": {"type": "boolean"},
        },
        ["role", "canAdmin", "canFounder"],
    ),
    "AdminOverviewResponse": obj(
        {
            "registeredUsers": {"type": "integer", "format": "int64"},
            "activeUsers": {"type": "integer", "format": "int64"},
            "collectionItems": {"type": "integer", "format": "int64"},
            "collectionCards": {"type": "integer", "format": "int64"},
            "wishlistItems": {"type": "integer", "format": "int64"},
            "activeListings": {"type": "integer", "format": "int64"},
            "pendingOffers": {"type": "integer", "format": "int64"},
        },
        [
            "registeredUsers", "activeUsers", "collectionItems",
            "collectionCards", "wishlistItems", "activeListings",
            "pendingOffers",
        ],
    ),
    "AdminUserSummaryResponse": obj(
        {
            "id": {"type": "string"},
            "email": {"type": "string"},
            "displayName": nullable({"type": "string"}),
            "friendCode": {"type": "string"},
            "role": role,
            "disabled": {"type": "boolean"},
            "createdAt": {"type": "string"},
            "collectionItems": {"type": "integer", "format": "int64"},
            "collectionCards": {"type": "integer", "format": "int64"},
            "wishlistItems": {"type": "integer", "format": "int64"},
            "activeListings": {"type": "integer", "format": "int64"},
            "pendingOffers": {"type": "integer", "format": "int64"},
        },
        [
            "id", "email", "displayName", "friendCode", "role",
            "disabled", "createdAt", "collectionItems", "collectionCards",
            "wishlistItems", "activeListings", "pendingOffers",
        ],
    ),
    "AdminCollectionItemResponse": obj(
        {
            "id": {"type": "string"},
            "cardId": {"type": "string"},
            "languageCode": {"type": "string"},
            "name": {"type": "string"},
            "setName": nullable({"type": "string"}),
            "localId": nullable({"type": "string"}),
            "variant": {"type": "string"},
            "condition": {"type": "string"},
            "quantity": {"type": "integer", "format": "int32"},
            "valuedUnitEur": nullable({"type": "number", "format": "double"}),
            "positionValueEur": nullable({"type": "number", "format": "double"}),
        },
        [
            "id", "cardId", "languageCode", "name", "setName", "localId",
            "variant", "condition", "quantity", "valuedUnitEur",
            "positionValueEur",
        ],
    ),
    "AdminWishlistItemResponse": obj(
        {
            "id": {"type": "string"},
            "cardId": {"type": "string"},
            "languageCode": {"type": "string"},
            "name": {"type": "string"},
            "setName": nullable({"type": "string"}),
            "localId": nullable({"type": "string"}),
            "variantId": nullable({"type": "string"}),
            "createdAt": {"type": "string"},
        },
        [
            "id", "cardId", "languageCode", "name", "setName", "localId",
            "variantId", "createdAt",
        ],
    ),
    "AdminListingResponse": obj(
        {
            "id": {"type": "string"},
            "collectionItemId": {"type": "string"},
            "cardId": {"type": "string"},
            "name": {"type": "string"},
            "quantity": {"type": "integer", "format": "int32"},
            "priceEur": nullable({"type": "number", "format": "double"}),
            "negotiable": {"type": "boolean"},
            "status": {"type": "string"},
            "createdAt": {"type": "string"},
        },
        [
            "id", "collectionItemId", "cardId", "name", "quantity",
            "priceEur", "negotiable", "status", "createdAt",
        ],
    ),
    "AdminUserDetailResponse": obj(
        {
            "user": ref("AdminUserSummaryResponse"),
            "collection": array(ref("AdminCollectionItemResponse")),
            "wishlist": array(ref("AdminWishlistItemResponse")),
            "listings": array(ref("AdminListingResponse")),
        },
        ["user", "collection", "wishlist", "listings"],
    ),
    "FounderSystemResponse": obj(
        {
            "database": {"type": "string"},
            "service": {"type": "string"},
            "version": {"type": "string"},
            "justTcgConfigured": {"type": "boolean"},
            "soldCompsConfigured": {"type": "boolean"},
            "registeredUsers": {"type": "integer", "format": "int64"},
            "collectionItems": {"type": "integer", "format": "int64"},
        },
        [
            "database", "service", "version", "justTcgConfigured",
            "soldCompsConfigured", "registeredUsers", "collectionItems",
        ],
    ),
})

paths.update({
    "/api/v1/admin/access": {
        "get": admin_operation(
            "getAdminAccess",
            "Eigene Admin-/Founder-Berechtigung laden",
            ref("AdminAccessResponse"),
        )
    },
    "/api/v1/admin/overview": {
        "get": admin_operation(
            "getAdminOverview",
            "Control-Center-Übersicht laden",
            ref("AdminOverviewResponse"),
        )
    },
    "/api/v1/admin/users": {
        "get": admin_operation(
            "getAdminUsers",
            "Nutzer für das Control Center laden",
            array(ref("AdminUserSummaryResponse")),
            parameters=[{
                "name": "q",
                "in": "query",
                "required": False,
                "schema": {"type": "string"},
            }],
        )
    },
    "/api/v1/admin/users/{id}": {
        "get": admin_operation(
            "getAdminUser",
            "Read-only Nutzerdetails laden",
            ref("AdminUserDetailResponse"),
            parameters=[{
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }],
        )
    },
    "/api/v1/admin/system": {
        "get": admin_operation(
            "getFounderSystem",
            "Founder-Systemstatus laden",
            ref("FounderSystemResponse"),
        )
    },
})

# Full physical catalogue coverage, including deferred and missing-variant entries.
coverage_group = {
    "setId": {"type": "string"}, "setName": {"type": "string"}, "languageCode": {"type": "string"},
    **{key: {"type": "integer", "format": "int64"} for key in
       ("affectedCards", "missingPrices", "deferredPrices", "providerErrors", "missingCache", "missingVariantCards")},
}
schemas["AdminPriceCoverageGroup"] = obj(coverage_group, list(coverage_group))
schemas["AdminPriceCoverageResponse"] = obj({"groups": array(ref("AdminPriceCoverageGroup"))}, ["groups"])
coverage_card = {
    **{key: {"type": "string"} for key in ("cardId", "cardName", "cardNumber", "reason")},
    **{key: nullable({"type": "string"}) for key in ("variantId", "variant", "failureDetail", "nextAttemptAt")},
}
schemas["AdminPriceCoverageCard"] = obj(coverage_card, ["cardId", "cardName", "cardNumber", "reason"])
schemas["AdminPriceCoverageCardsResponse"] = obj({
    "total": {"type": "integer", "format": "int64"},
    "offset": {"type": "integer", "minimum": 0},
    "items": array(ref("AdminPriceCoverageCard")),
}, ["total", "offset", "items"])
coverage_language = {"name": "language", "in": "query", "schema": {"type": "string", "enum": ["de", "en", "ja", "ko", "zh-cn", "zh-tw"]}}
paths["/api/v1/admin/price-coverage"] = {"get": admin_operation(
    "getAdminPriceCoverage", "Fehlende Preise nach Set und Sprache", ref("AdminPriceCoverageResponse"),
    parameters=[coverage_language],
)}
paths["/api/v1/admin/price-coverage/cards"] = {"get": admin_operation(
    "getAdminPriceCoverageCards", "Fehlende Preise eines Sets (100 Einträge pro Seite)", ref("AdminPriceCoverageCardsResponse"),
    parameters=[{**coverage_language, "required": True},
                {"name": "setId", "in": "query", "required": True, "schema": {"type": "string", "maxLength": 160}},
                {"name": "offset", "in": "query", "schema": {"type": "integer", "minimum": 0, "default": 0}}],
)}

text = json.dumps(
    spec,
    indent=2,
    ensure_ascii=False,
) + "\n"

OUT.write_text(text)
PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
PUBLIC_OUT.write_text(text)

print("Admin/Founder contract extension written")
