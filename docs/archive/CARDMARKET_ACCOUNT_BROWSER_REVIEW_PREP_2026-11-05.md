# Cardmarket Browser Review — account login handoff (2026-11-05)

## Prepared

The Windows Desktop on Lenovo Tiny (`C:\Users\TV\Desktop`) has:

- `Cardmarket - Cardyssey Pruefung.lnk`: launches `scripts/Cardmarket-Login-Test.ps1` via PowerShell.
- `Cardyssey-Cardmarket-Pruefung\de_offene_cardmarket_varianten.csv`: 1,460 missing physical German print variants, verified product candidates and unresolved identity flags.
- `Cardyssey-Cardmarket-Pruefung\status.json`: review counts.

The PowerShell entrypoint opens the ordinary Cardmarket site in a dedicated **interactive Chrome profile** at `%LOCALAPPDATA%\Cardyssey\CardmarketReviewProfile`. If Chrome is missing, it uses Microsoft Edge. This is isolated from the default browser profile. No passwords, cookies, session tokens or API keys are copied into repository files or logs. The user must type credentials themselves into the Cardmarket page and complete any legitimate checks.

## Source worklist

`python3 scripts/refresh-cardmarket-price-cache.py --language de --dry-run --fallback-report /tmp/cardyssey-cardmarket-login-review.json`

`python3 scripts/prepare-cardmarket-browser-review.py --input /tmp/cardyssey-cardmarket-login-review.json --output-dir /home/tv/cardshop/reports/cardmarket-review`

Results from the 2026-11-05 pass: 1,460 unresolved German physical print variants, 978 with 1+ unverified Cardmarket product candidates. Review queue A=6 straightforward set-verified candidates, B=972 variants with additional ambiguity, D=482 with no provider candidates. Review priority is **not** price approval. Use exact language, set, number, subtype, foil, edition and seller condition as evidence.

Do not treat public Cardmarket trend as language-specific Near Mint. Cardmarket product price guide remains the production market reference. No automated bypass of Cloudflare, captcha, login restrictions or private article endpoints is added by this handoff. If the signed-in browser can lawfully show product/filter details, inspect small controlled cases before considering any wider process. Stop if automated access is blocked or prohibited. Only use permitted exports or API access for bulk offer collection.

## User next action

Open `Cardmarket - Cardyssey Pruefung` on the **Tiny Windows desktop**, sign in personally, then tell ChatGPT **„Cardmarket ist angemeldet“**. Do not provide username/password or screenshots with sensitive session tokens. The account does **not** guarantee availability of automated data access, and no price updates are promised before a real legitimate source test.

## Deployment/cleanup

This preparation does not modify the Cardyssey API/Android/Web build, production database, price caches, services or timers. Project scripts and documentation are versioned; generated review reports and local browser profile are intentionally not committed. To dispose of the test session, sign out in the dedicated browser and delete `%LOCALAPPDATA%\Cardyssey\CardmarketReviewProfile` on Windows after closing its browser window.
