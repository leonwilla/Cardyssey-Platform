"""Plausibilität exakter Browser-Preise gegen den offiziellen Preisführer.

Browser-Preise sind Median-*Angebots*preise der sichtbaren NM-Angebote einer Sprache.
Bei wenigen Angeboten reicht ein Fantasiepreis eines Verkäufers (z. B. 8.250 EUR bei
25 EUR Trend, 26.11.2026). Solche Werte werden nicht übernommen; dann gilt der
offizielle Preisführer.
"""

STD_MAX = 10.0          # ab dieser Abweichung ist auch ein breiter Angebotsmedian unglaubwürdig
STD_MAX_FEW = 4.0       # bei weniger als FEW_OFFERS Angeboten
FIRST_ED_MAX = 40.0     # 1. Auflage: Preisführer mischt 1. Auflage und Unlimited
FIRST_ED_MAX_FEW = 15.0
FIRST_ED_MIN_EUR = 50.0  # günstige 1.-Auflage-Karten nicht prüfen
FEW_OFFERS = 3


def browser_price_plausible(price, guide_eur, first_edition=False, offers=None):
    """-> (True, '') oder (False, Grund). Ohne Preisführer-Wert immer plausibel."""
    if not guide_eur or guide_eur <= 0 or not price or price <= 0:
        return True, ''
    ratio = price / guide_eur
    few = offers is not None and offers < FEW_OFFERS
    if first_edition:
        limit = FIRST_ED_MAX_FEW if few else FIRST_ED_MAX
        if price >= FIRST_ED_MIN_EUR and ratio > limit:
            return False, f'{ratio:.0f}x Preisführer (1. Auflage, {offers} Angebote)'
        return True, ''
    high = STD_MAX_FEW if few else STD_MAX
    if ratio > high or ratio < 1 / high:
        return False, f'{ratio:.2f}x Preisführer ({offers} Angebote)'
    return True, ''
