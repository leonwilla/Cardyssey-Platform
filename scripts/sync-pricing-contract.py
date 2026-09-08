#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "contracts" / "cardyssey.openapi.json"

with SPEC.open("r", encoding="utf-8") as handle:
    spec = json.load(handle)

pricing_tag = {"name": "Pricing"}
if pricing_tag not in spec.setdefault("tags", []):
    spec["tags"].append(pricing_tag)

error_response = lambda description: {
    "description": description,
    "content": {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/ErrorResponse"
            }
        }
    }
}

spec.setdefault("paths", {})[
    "/api/v1/pricing/cards/{id}"
] = {
    "get": {
        "tags": ["Pricing"],
        "operationId": "getCardPriceQuote",
        "summary": "Zentralen Marktpreis für eine exakte Kartenvariante laden",
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            },
            {
                "name": "language",
                "in": "query",
                "required": False,
                "schema": {
                    "type": "string",
                    "default": "de"
                }
            },
            {
                "name": "variantId",
                "in": "query",
                "required": False,
                "description": "Bevorzugte exakte Varianten-ID aus dem zentralen Katalog.",
                "schema": {"type": "string"}
            },
            {
                "name": "variant",
                "in": "query",
                "required": False,
                "description": "Legacy-Variante. Wird nur verwendet, wenn sie genau eine physische Variante ergibt.",
                "schema": {
                    "type": "string",
                    "enum": [
                        "NORMAL",
                        "REVERSE",
                        "HOLO",
                        "FIRST_EDITION"
                    ]
                }
            },
            {
                "name": "condition",
                "in": "query",
                "required": False,
                "schema": {
                    "type": "string",
                    "default": "NEAR_MINT",
                    "enum": [
                        "MINT",
                        "NEAR_MINT",
                        "EXCELLENT",
                        "GOOD",
                        "PLAYED"
                    ]
                }
            }
        ],
        "responses": {
            "200": {
                "description": "Erfolgreich",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/CardPriceQuoteResponse"
                        }
                    }
                }
            },
            "400": error_response("Ungültige Anfrage"),
            "401": error_response("Nicht authentifiziert"),
            "403": error_response("Nicht erlaubt"),
            "404": error_response("Karte nicht gefunden")
        }
    }
}

spec.setdefault("components", {}).setdefault("schemas", {})[
    "CardPriceQuoteResponse"
] = {
    "type": "object",
    "required": [
        "cardId",
        "languageCode",
        "condition",
        "market",
        "conditionFactor",
        "exactLanguageMatch",
        "exactVariantMatch"
    ],
    "properties": {
        "cardId": {"type": "string"},
        "languageCode": {"type": "string"},
        "variantId": {
            "type": "string",
            "nullable": True
        },
        "variantType": {
            "type": "string",
            "nullable": True
        },
        "condition": {
            "type": "string",
            "enum": [
                "MINT",
                "NEAR_MINT",
                "EXCELLENT",
                "GOOD",
                "PLAYED"
            ]
        },
        "market": {
            "type": "string",
            "enum": ["TCG"]
        },
        "source": {
            "type": "string",
            "nullable": True,
            "enum": ["TCGDEX"]
        },
        "baseEur": {
            "type": "number",
            "format": "double",
            "nullable": True
        },
        "conditionFactor": {
            "type": "number",
            "format": "double"
        },
        "eur": {
            "type": "number",
            "format": "double",
            "nullable": True
        },
        "exactLanguageMatch": {"type": "boolean"},
        "exactVariantMatch": {"type": "boolean"}
    }
}

with SPEC.open("w", encoding="utf-8") as handle:
    json.dump(
        spec,
        handle,
        ensure_ascii=False,
        indent=2
    )
    handle.write("\n")
