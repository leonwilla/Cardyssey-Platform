# CapSolver trial readiness for PriceCharting

Current stage: **preflight only; no challenge task has been submitted and no charges incurred.**

- `scripts/capsolver_preflight.py`: makes an authenticated **getBalance** request only if an API key is safely configured. It never echoes key values or proxy addresses and never invokes `createTask`.
- On 2026-11-05, the Tiny could resolve/reach the CapSolver API host. A direct GET of the POST-only API route returned HTTP 404 (not a balance check).
- The remote tool blocked transmission of the key pasted in chat. It was **not** stored on the Tiny; do not attempt to circumvent that block. Generate a replacement key and use an approved secure secret entry mechanism or authenticated local terminal to install it.
- Recommended local file `/home/tv/.config/cardyssey/capsolver.key` permissions 0600, directory 0700, excluded from source code and Git. Or set process environment `CAPSOLVER_API_KEY` from an approved secret store.
- A static/sticky proxy is required by CapSolver for `AntiCloudflareTask`. `CAPSOLVER_PROXY` is not configured on the Tiny. Without one, challenge task creation must not start.
- A balance response is not proof that PriceCharting will allow access. Its public website currently serves a Cloudflare challenge on the Tiny; website data usage permissions must be checked before production ingestion.
- Never send PriceCharting login credentials or existing browser cookies to CapSolver or untrusted subdomains. No indefinite retries or automatic spending.

To check readiness after secure setup:

```bash
python3 /home/tv/cardshop/scripts/capsolver_preflight.py
```

Expected fields: `status=API_ACCEPTED`, `balanceUsd`, and `staticProxyConfigured=true`. These are prerequisites only; not a promise of access to PriceCharting. **No paid operation is enabled by this script.**
