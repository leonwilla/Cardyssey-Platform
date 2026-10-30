# Standalone company storefront: shop.cardyssey.de

Current code:
- `web/app/business-shop` has its own commercial header and layout. No AppShell or social navigation.
- `web/proxy.ts` routes incoming Host: shop.cardyssey.de to this storefront at / and restricts shop-host routes to GET /api/sets, GET /api/shop/offers, and required assets. No WordPress routes, no community listing/admin routes on the store host.
- Company inventory remains `cardyssey_shop.*`; community inventory remains `/marketplace`, `/selling` and the current API.
- Private beta only: existing Cardyssey login cookies scoped to .cardyssey.de are required; storefront does not implement independent signup.
- No cart, payment, order fulfillment or public launch.
- `shop.cardyssey.de` still needs its reverse proxy upstream changed from WordPress (localhost:8080) to Next.js (localhost:3000), preserving original Host and TLS. The actual proxy provider/config must be verified on the Tiny; do not assume Cloudflare vs Nginx.

Deployment:
```bash
cd ~/cardshop
sudo systemctl stop cardyssey-deploy.timer
git pull --ff-only origin main
(cd web && npm run build)
sudo systemctl restart cardyssey-web.service
sudo systemctl enable --now cardyssey-deploy.timer
```

Before DNS/proxy cutover, locally test the new host route:
```bash
curl -si -H 'Host: shop.cardyssey.de' http://127.0.0.1:3000/ | head -n 14
curl -si -H 'Host: shop.cardyssey.de' http://127.0.0.1:3000/marketplace | head -n 10
curl -si -H 'Host: shop.cardyssey.de' http://127.0.0.1:3000/wp-admin/ | head -n 10
```
Expected unauthenticated redirect on / to cardyssey.de/login, and 404 on /marketplace and /wp-admin. **Never** submit valid session cookies in terminal/logs.

After changing proxy route, test shop.cardyssey.de in normal browser (domain/policy, set search, card image, company price only, no social navigation). Validate 302 to Cardyssey login when unauthenticated, no cache of private pages, 404 on community/admin URLs. Then verify database listing with admin at cardyssey.de/admin/shop-catalog. Only retire WordPress when rollback is tested and explicit cutover evidence exists.

Do not use `docker compose down -v`, `docker volume prune`, or delete the MySQL volume.
