"""Fail-closed print identity checks for pricing provider candidates.

Provider product catalogues are not language-specific price quotations.
A name match only proposes an identity; language/edition and physical printing
must be confirmed before a candidate can become an automatic price.
"""
import re


def normalize_number(value):
    value=str(value or "").strip().split("/",1)[0]
    match=re.fullmatch(r"([A-Za-z]*)(0*[0-9]+)([A-Za-z]*)",value)
    if not match:
        return value.casefold()
    if match.group(1) or match.group(3):
        return value.casefold()  # Promo prefix/suffix may make zero-padding significant
    return str(int(match.group(2)))


def print_reasons(variant, candidate_name, *, language_verified=False, edition_verified=False,
                  number_verified=False, set_verified=False):
    reasons=[]
    if not set_verified:reasons.append("SET_UNVERIFIED")
    if not number_verified:reasons.append("CARD_NUMBER_UNVERIFIED")
    if not language_verified:reasons.append("LANGUAGE_UNVERIFIED")
    if not edition_verified:reasons.append("EDITION_UNVERIFIED")
    name=str(candidate_name or "").casefold()
    stamps=[str(x).casefold() for x in (variant.get("stamps") or [])]
    foil=str(variant.get("foil") or "").casefold()
    subtype=str(variant.get("subtype") or "").casefold()
    size=str(variant.get("size") or "standard").casefold()
    if size not in ("", "standard") and size not in name:
        reasons.append("SIZE_UNVERIFIED")
    for marker in stamps:
        if marker and marker.replace("-"," ") not in name.replace("-"," "):
            reasons.append("STAMP_UNVERIFIED")
            break
    if foil and foil.replace("-"," ") not in name.replace("-"," "):
        reasons.append("FOIL_UNVERIFIED")
    if subtype and subtype not in name:
        reasons.append("SUBTYPE_UNVERIFIED")
    return reasons


def candidate_status(candidate_count, reasons):
    if not candidate_count:return "NO_PROVIDER_PRODUCT_MATCH"
    if candidate_count!=1:return "AMBIGUOUS_PRODUCT_IDENTITY"
    return "READY_FOR_REVIEW" if reasons else "IDENTITY_VERIFIED"


def split_by_verified_expansion(products, expected_expansion):
    """Return verified-set candidates and name-only search hints separately.

    An unverified expansion must never become an identity candidate.
    """
    if expected_expansion is None:
        return [], list(products)
    verified=[p for p in products if p.get("idExpansion")==expected_expansion]
    return verified,[p for p in products if p.get("idExpansion")!=expected_expansion]
