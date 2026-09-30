# 30th Celebration product promos

Verified 2026-09-29 against the official Pokémon product showcase and promo legality list:

- https://www.pokemon.com/us/news/pokemon-tcg-30th-celebration-product-showcase
- https://www.pokemon.com/uk/play-pokemon/about/pokemon-tcg-promo-card-legality-status
- https://www.pokemon.com/de/pokemon-sammelkartenspiel/Produktgalerie/top-trainer-box-30-jahre

| Physical ID | German name | Product |
| --- | --- | --- |
| MEP 094 | Alola-Kokowei | Tech Sticker |
| MEP 095 | Lucario | Tech Sticker |
| MEP 096 | Lavados | Poster |
| MEP 097 | Arktos | Poster |
| MEP 098 | Zapdos | Poster |
| MEP 099 | Quajutsu-ex | Pokémon-ex Collection |
| MEP 100 | Feelinara-ex | Pokémon-ex Collection |
| MEP 101 | Nidorina | Elite Trainer Box |

`30th-promos` is a Cardyssey product grouping, not an official replacement set code. Canonical IDs stay `mep-NNN`; main-set and Classic Collection numbering and collection entries do not change. MEP 030 is not in this grouping. Unreleased product promos without verified numbers are not guessed. Oversize and Pokémon Center stamped prints are not additional card numbers.

German scans: public German card images from https://pokezentrum.de/blog/alle-pokemon-mega-promokarten-in-der-uebersicht/ (exact URLs in AnniversaryPromos.kt); English 100/101 from Pokémon's official card assets. English 094–099 remain explicit image gaps. A German image is never declared English. No prices are invented.

The Supplemental Catalog Sync deploys the API and runs AnniversaryCatalogRepairKt inside cardyssey-api. It downloads, decodes, hashes and stores verified scans in the existing /data/catalog volume and records them in PostgreSQL. Successful images are skipped on reruns; failures are reported individually and fail the step after retries. Existing physical print variants and prices are preserved.

Manual check after deployment/APK: Sets → 30 Jahre → Jubiläums-Promos; eight cards in MEP order; German Nidorina image; adding a card increments the same MEP collection entry; language filtering preserves separate German/English holdings. The subgroup also appears in the Promo-Sets filter.
