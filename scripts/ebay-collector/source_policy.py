"""Cardyssey acquisition policy: bulk uses German TCG/Cardmarket references.

Only Normal/Common and Uncommon prints are bulk. Rare/holo/illustration,
ex/ultra, promos, and special prints remain eligible for eBay acquisition.
No PriceCharting fallback is ever implied by this routing policy.
"""
import re
BULK_RARITIES=frozenset({'häufig','ungewöhnlich','common','uncommon'})

def is_bulk_rarity(rarity):
    return isinstance(rarity,str) and rarity.strip().casefold() in BULK_RARITIES

def ebay_required(card):
    return not is_bulk_rarity(card.get('rarity'))

def load_bulk_ids(db):
    raw=db("SELECT card_id FROM catalog_cards_mirror WHERE language_code='de' AND lower(trim(rarity)) IN ('häufig','ungewöhnlich','common','uncommon')")
    return set(raw.splitlines())
