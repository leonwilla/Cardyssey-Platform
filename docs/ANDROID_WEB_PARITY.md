# Android / Web parity – implementation and test contract

Reviewed in GitHub on 2026-10-27. Code inspection, not a device test.

## Verified foundations
- Android is native Kotlin/Jetpack Compose with CameraX and ML Kit, as documented in its README.
- Android MainActivity syncs appearance setting from the Cardyssey API after login.
- Android Theme.kt currently contains four dark palettes: OBSIDIAN_GOLD, MIDNIGHT_CYAN, ROYAL_VIOLET, EMERALD_MINT.
- Web AppearanceSettingsPanel stores the same dark theme setting through /api/appearance.
- The experimental cream/orange browser preview is local-only and must not be silently synced into existing Android enum.
- Web has collection, scanner, set catalog, and shop routes. Shop is now in small-screen bottom navigation.

## End-to-end parity acceptance tests
1. Same login and auth permissions on both platforms.
2. Set list and catalog counts for all six supported languages.
3. Matching printed card number, set ID, card ID, picture, edition and foil variant.
4. Collection quantity, condition, and wishlist updates seen on both platforms.
5. Android CameraX/OCR and browser scanner produce equivalent confirmed card identities.
6. Same price source, age, unknown-price state and 30-day median.
7. Shop listing is not buyable until an admin supplies price, stock and publishes it.
8. Existing dark themes sync; experimental light web preview remains opt-in.
9. Test small-screen navigation, modal contrast, typography and accessibility.
10. Test order reductions, cancellations, refunds and out-of-stock handling.

## Outstanding implementation and validation
- An Android light palette needs an explicit new backend theme enum, DTO serializer and version-compatible migration, plus UI review. Do not change this blindly.
- Live feature equality, artwork licensing, WooCommerce connection, and device/build tests are not yet confirmed.
- Keep public registration and production publication blocked until explicit approval.