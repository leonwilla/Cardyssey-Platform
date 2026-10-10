#!/usr/bin/env python3
"""Marketplace inventory quantity is distinct from physical bundle size.

Primary contract: https://www.cardtrader.com/en-US/docs/api/full/reference
Multi-unit stock is accepted only when an explicit bundle_size proves unit=1.
"""
def is_single_card_stock(product):
    quantity=product.get("quantity")
    if type(quantity) is not int or quantity<=0:
        return False
    size=product.get("bundle_size")
    if size is None:
        # Legacy marketplace payload: retain the existing conservative stock=1 case.
        if quantity!=1:
            return False
    elif type(size) is not int or size!=1:
        return False
    if "bundled_quantity" in product:
        bundled=product["bundled_quantity"]
        if type(bundled) is not int or bundled!=quantity:
            return False
    return True
