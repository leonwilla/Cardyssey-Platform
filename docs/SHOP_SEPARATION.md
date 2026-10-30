# Cardyssey: Gewerblicher Webshop vs Nutzer-Marktplatz

Status: implementation in repository, host cutover pending.

## Distinct inventory owners

- `shop.cardyssey.de` (target): commercial storefront, business-only offers and company inventory. Current internal preview route: `/business-shop`.
- `cardyssey.de/shop`: community marketplace redirect to `/marketplace`; user listings are loaded from existing `/api/marketplace` and created through existing `/selling` route.
- `cardyssey.de/admin/shop-catalog`: business-owner card import/editor; saved offers use `/api/admin/shop/native` and native PostgreSQL `cardyssey_shop` tables. The editor now displays server-persisted business offers.
- Neither store sells until payments/orders and inventory reservations are implemented.
- Do not merge or transfer individual users' private collection records into business stock.

## Why share the catalog

One reference catalog for card identities, image bases, sets, variants and languages. This is *not* shared inventory. Business stock and user listings are separate storage and permissions.

## Current release constraints

- The new company storefront still runs within the private Cardyssey Next.js web application; subdomain routing and separate shop header/layout are not yet configured at the reverse proxy. Do not stop WordPress/MySQL until the host and its own access policy are verified.
- Current business offer write route uses gated Next.js → local PostgreSQL. Long term migrate it to Kotlin/Ktor, with a dedicated least-privilege DB role and transaction safety.
- The API currently supports card offers, not arbitrary sealed products, accessories, bundles or owned-photo upload. Those need dedicated workflows before claiming a complete commercial catalogue.
- Saved business offers are listed on the admin page; browser-selected unsynced drafts remain separate.
- Existing app marketplace is already present; no new user-sales database is created here.
- Do not conflate image display permission in app with commercial redistribution rights in storefront.

## Rollout

1. On Tiny, `cd ~/cardshop && git pull --ff-only origin main && (cd web && npm run build) && sudo systemctl restart cardyssey-web.service`.
2. In private browser verify `/shop` redirects to `/marketplace`, `/business-shop` shows business-only catalog, admin saved offers list includes previously created Owei. If needed create a business draft, reload and verify it appears in saved list.
3. Confirm company offers appear on business-shop only after explicitly publishing with stock and price. Do **not** list user offers there.
4. Reverse-proxy `shop.cardyssey.de` to an independently configured business storefront hostname/route with explicit Host routing and security. Test login, cookies, tenant isolation and redirects before turning off WP.
5. Preserve WordPress/MySQL volumes; archive and verify backups before retirement.
