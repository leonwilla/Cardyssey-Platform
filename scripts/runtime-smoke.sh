#!/usr/bin/env bash

set -euo pipefail

BASE_WEB_URL="${BASE_WEB_URL:-https://cardyssey.de}"
BASE_API_URL="${BASE_API_URL:-https://api.cardyssey.de}"
API_PREFIX="${API_PREFIX:-/api/v1}"
ANDROID_APK_URL="${ANDROID_APK_URL:-https://github.com/leonwilla/Cardyssey-Downloads/releases/latest/download/cardyssey-latest.apk}"
EBAY_SMOKE_CARD_ID="${CARDYSSEY_EBAY_SMOKE_CARD_ID:-me05-088}"
EBAY_SMOKE_LANGUAGE="${CARDYSSEY_EBAY_SMOKE_LANGUAGE:-de}"
E2E_ACCESS_TOKEN="${E2E_ACCESS_TOKEN:-}"
E2E_REFRESH_TOKEN=""

check() {
  label="$1"
  url="$2"
  code="$(curl -L -sS --connect-timeout 12 --max-time 45 -o /tmp/cardyssey-smoke-body -w '%{http_code}' "$url" || true)"
  if [ "$code" != "200" ]; then
    echo "FAIL: $label -> HTTP $code"
    cat /tmp/cardyssey-smoke-body 2>/dev/null || true
    return 1
  fi
  echo "OK: $label"
}

check_status() {
  label="$1"
  url="$2"
  expected="$3"
  code="$(curl -L -sS --connect-timeout 12 --max-time 45 -o /tmp/cardyssey-smoke-status-body -w '%{http_code}' "$url" || true)"
  if [ "$code" != "$expected" ]; then
    echo "FAIL: $label -> HTTP $code (expected $expected)"
    cat /tmp/cardyssey-smoke-status-body 2>/dev/null || true
    return 1
  fi
  echo "OK: $label -> HTTP $code"
}

check_api_health() {
  url="$BASE_API_URL$API_PREFIX/health"

  for attempt in $(seq 1 12); do
    code="$(curl -L -sS --connect-timeout 12 --max-time 45 -o /tmp/cardyssey-api-health.json -w '%{http_code}' "$url" || true)"

    if [ "$code" = "200" ] && python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path('/tmp/cardyssey-api-health.json').read_text())
if data.get('status') != 'ok':
    raise SystemExit(f"API health status={data.get('status')!r}")
if data.get('database') != 'connected':
    raise SystemExit(f"API database={data.get('database')!r}")
if data.get('version') != '0.2.4':
    raise SystemExit(
        f"production backend is stale: version={data.get('version')!r}, expected='0.2.4'"
    )
if data.get('ebayPricingMode') != 'CARDYSSEY_DIRECT_ONLY':
    raise SystemExit(
        f"unexpected eBay pricing mode={data.get('ebayPricingMode')!r}"
    )
if data.get('ebayDirectEnabled') is not True:
    raise SystemExit('direct Cardyssey eBay collector is disabled')
if not isinstance(data.get('ebayDirectSessionConfigured'), bool):
    raise SystemExit('missing ebayDirectSessionConfigured health flag')
cache_ttl = data.get('ebayPriceCacheTtlHours')
if not isinstance(cache_ttl, int) or cache_ttl <= 0:
    raise SystemExit(f'invalid eBay price cache TTL: {cache_ttl!r}')

print(
    'OK: API health -> '
    f"version {data.get('version')}, "
    'eBay mode=CARDYSSEY_DIRECT_ONLY, '
    f"direct session={'configured' if data.get('ebayDirectSessionConfigured') else 'not configured'}, "
    f"cache TTL={cache_ttl}h"
)
PY
    then
      return 0
    fi

    if [ "$attempt" -lt 12 ]; then
      echo "INFO: API deployment not ready yet (attempt $attempt/12, HTTP $code); retrying in 15s."
      sleep 15
    fi
  done

  echo "FAIL: API health did not reach the direct Cardyssey eBay release."
  cat /tmp/cardyssey-api-health.json 2>/dev/null || true
  return 1
}
check_android_metadata() {
  url="$BASE_WEB_URL/api/android/latest"
  code="$(curl -L -sS --connect-timeout 12 --max-time 45 -o /tmp/cardyssey-android-release.json -w '%{http_code}' "$url" || true)"
  if [ "$code" != "200" ]; then
    echo "FAIL: Android release metadata -> HTTP $code"
    cat /tmp/cardyssey-android-release.json 2>/dev/null || true
    return 1
  fi

  python3 - <<'PY'
import json
from pathlib import Path

path = Path('/tmp/cardyssey-android-release.json')
data = json.loads(path.read_text())
required = {
    'versionName': str,
    'versionCode': int,
    'buildNumber': int,
    'commit': str,
    'builtAt': str,
    'file': str,
    'sizeBytes': int,
    'sha256': str,
}
missing = [name for name, kind in required.items() if not isinstance(data.get(name), kind)]
if missing:
    raise SystemExit('FAIL: Android release metadata invalid fields: ' + ', '.join(missing))
if data['buildNumber'] < 1 or data['versionCode'] < 1 or data['sizeBytes'] < 1:
    raise SystemExit('FAIL: Android release metadata contains invalid numeric values')
if len(data['sha256']) != 64:
    raise SystemExit('FAIL: Android release metadata contains invalid sha256')
print(f"OK: Android release metadata -> build {data['buildNumber']} ({data['builtAt']})")
PY
}

e2e_logout() {
  if [ -z "${E2E_REFRESH_TOKEN:-}" ]; then
    return 0
  fi

  export E2E_REFRESH_TOKEN
  python3 - <<'PY'
import json
import os
from pathlib import Path

Path('/tmp/cardyssey-smoke-logout.json').write_text(
    json.dumps({'refreshToken': os.environ['E2E_REFRESH_TOKEN']})
)
PY

  curl -sS --connect-timeout 12 --max-time 30 \
    -H 'Content-Type: application/json' \
    --data-binary @/tmp/cardyssey-smoke-logout.json \
    "$BASE_API_URL$API_PREFIX/auth/logout" \
    >/dev/null 2>&1 || true

  rm -f /tmp/cardyssey-smoke-logout.json
  E2E_REFRESH_TOKEN=""
}

e2e_login() {
  if [ -n "${E2E_EMAIL:-}" ] || [ -n "${E2E_PASSWORD:-}" ]; then
    if [ -z "${E2E_EMAIL:-}" ] || [ -z "${E2E_PASSWORD:-}" ]; then
      echo "FAIL: E2E_EMAIL and E2E_PASSWORD must either both be set or both be empty"
      return 1
    fi

    export E2E_EMAIL E2E_PASSWORD
    python3 - <<'PY'
import json
import os
from pathlib import Path

Path('/tmp/cardyssey-smoke-login.json').write_text(
    json.dumps({
        'email': os.environ['E2E_EMAIL'],
        'password': os.environ['E2E_PASSWORD'],
    })
)
PY

    code="$(curl -sS --connect-timeout 12 --max-time 45 \
      -H 'Content-Type: application/json' \
      --data-binary @/tmp/cardyssey-smoke-login.json \
      -o /tmp/cardyssey-smoke-login-response.json \
      -w '%{http_code}' \
      "$BASE_API_URL$API_PREFIX/auth/login" || true)"

    rm -f /tmp/cardyssey-smoke-login.json

    if [ "$code" != "200" ]; then
      echo "FAIL: E2E login -> HTTP $code"
      rm -f /tmp/cardyssey-smoke-login-response.json
      return 1
    fi

    E2E_ACCESS_TOKEN="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('/tmp/cardyssey-smoke-login-response.json').read_text()).get('accessToken', ''))
PY
)"
    E2E_REFRESH_TOKEN="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('/tmp/cardyssey-smoke-login-response.json').read_text()).get('refreshToken', ''))
PY
)"
    rm -f /tmp/cardyssey-smoke-login-response.json

    if [ -z "$E2E_ACCESS_TOKEN" ] || [ -z "$E2E_REFRESH_TOKEN" ]; then
      echo "FAIL: E2E login response did not contain both tokens"
      return 1
    fi

    trap e2e_logout EXIT
    echo "OK: E2E login"
  elif [ -n "$E2E_ACCESS_TOKEN" ]; then
    echo "INFO: using legacy E2E_ACCESS_TOKEN fallback"
  fi
}

auth_check() {
  label="$1"
  path="$2"
  code="$(curl -sS --connect-timeout 12 --max-time 45 -o /tmp/cardyssey-smoke-auth-body -w '%{http_code}' \
    -H "Authorization: Bearer $E2E_ACCESS_TOKEN" \
    "$BASE_API_URL$API_PREFIX$path" || true)"
  if [ "$code" != "200" ]; then
    echo "FAIL: $label -> HTTP $code"
    cat /tmp/cardyssey-smoke-auth-body 2>/dev/null || true
    return 1
  fi
  echo "OK: $label"
}

ebay_price_check() {
  card_url="$BASE_API_URL$API_PREFIX/cards/$EBAY_SMOKE_CARD_ID"
  code="$(curl -sS --get --connect-timeout 12 --max-time 60     -o /tmp/cardyssey-smoke-ebay-card.json -w '%{http_code}'     -H "Authorization: Bearer $E2E_ACCESS_TOKEN"     --data-urlencode "language=$EBAY_SMOKE_LANGUAGE"     "$card_url" || true)"

  if [ "$code" != "200" ]; then
    echo "FAIL: eBay smoke card lookup -> HTTP $code"
    cat /tmp/cardyssey-smoke-ebay-card.json 2>/dev/null || true
    return 1
  fi

  mapfile -t ebay_variants < <(python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path('/tmp/cardyssey-smoke-ebay-card.json').read_text())
variants = data.get('variants')
if not isinstance(variants, list) or not variants:
    raise SystemExit('FAIL: eBay smoke card has no physical variants')

seen = set()
for variant in variants:
    variant_id = variant.get('id') if isinstance(variant, dict) else None
    if isinstance(variant_id, str) and variant_id and variant_id not in seen:
        seen.add(variant_id)
        print(variant_id)
        if len(seen) >= 8:
            break
PY
  )

  if [ "${#ebay_variants[@]}" -eq 0 ]; then
    echo "FAIL: eBay smoke card returned no usable variant IDs."
    return 1
  fi

  echo "INFO: probing $EBAY_SMOKE_CARD_ID/$EBAY_SMOKE_LANGUAGE with ${#ebay_variants[@]} exact variant(s)."

  found_quote=0
  variant_index=0
  for variant_id in "${ebay_variants[@]}"; do
    variant_index=$((variant_index + 1))
    quote_file="/tmp/cardyssey-smoke-ebay-$variant_index.json"
    price_url="$BASE_API_URL$API_PREFIX/pricing/cards/$EBAY_SMOKE_CARD_ID"
    code="$(curl -sS --get --connect-timeout 12 --max-time 90       -o "$quote_file" -w '%{http_code}'       -H "Authorization: Bearer $E2E_ACCESS_TOKEN"       --data-urlencode "language=$EBAY_SMOKE_LANGUAGE"       --data-urlencode "condition=NEAR_MINT"       --data-urlencode "market=EBAY"       --data-urlencode "variantId=$variant_id"       "$price_url" || true)"

    if [ "$code" != "200" ]; then
      echo "FAIL: eBay production pricing probe ($variant_id) -> HTTP $code"
      cat "$quote_file" 2>/dev/null || true
      return 1
    fi

    if ! classification="$(QUOTE_FILE="$quote_file" EXPECTED_VARIANT="$variant_id" python3 - <<'PY'
import json
import os
from pathlib import Path

data = json.loads(Path(os.environ['QUOTE_FILE']).read_text())
expected_variant = os.environ['EXPECTED_VARIANT']
market = data.get('market')
source = data.get('source')
mean = data.get('eur')
low = data.get('rangeLowEur')
high = data.get('rangeHighEur')
samples = data.get('sampleCount')
recent = data.get('recentSales')

if market != 'EBAY':
    raise SystemExit(f'FAIL: eBay pricing probe returned market={market!r}')
if data.get('variantId') != expected_variant or data.get('exactVariantMatch') is not True:
    raise SystemExit(
        f"FAIL: eBay pricing probe did not preserve exact variant {expected_variant!r}: "
        f"variantId={data.get('variantId')!r}, exact={data.get('exactVariantMatch')!r}"
    )

if source is None:
    fields = {
        key: data.get(key)
        for key in (
            'baseEur', 'eur', 'sampleCount', 'rangeLowEur',
            'rangeHighEur', 'updatedAtMs'
        )
    }
    dirty = {key: value for key, value in fields.items() if value is not None}
    if dirty:
        raise SystemExit(
            f'FAIL: empty eBay quote contains stale price evidence: {dirty!r}'
        )
    if recent not in (None, []):
        raise SystemExit(
            f'FAIL: empty eBay quote contains stale recent sales: {recent!r}'
        )
    print(f'EMPTY:{expected_variant}')
    raise SystemExit(0)

if source != 'CARDYSSEY_EBAY':
    raise SystemExit(
        f'FAIL: forbidden external eBay source returned: source={source!r}'
    )
if not isinstance(mean, (int, float)) or mean <= 0:
    raise SystemExit(f'FAIL: eBay pricing probe has invalid mean eur={mean!r}')
if not isinstance(low, (int, float)) or low <= 0:
    raise SystemExit(f'FAIL: eBay pricing probe has invalid rangeLowEur={low!r}')
if not isinstance(high, (int, float)) or high <= 0:
    raise SystemExit(f'FAIL: eBay pricing probe has invalid rangeHighEur={high!r}')
if low > high or not (low <= mean <= high):
    raise SystemExit(
        f'FAIL: invalid eBay mean/range relationship: mean={mean!r}, range={low!r}..{high!r}'
    )
if not isinstance(samples, int) or samples < 1:
    raise SystemExit(f'FAIL: eBay pricing probe has invalid sampleCount={samples!r}')
if not isinstance(recent, list) or not recent:
    raise SystemExit('FAIL: direct eBay quote has no verified recentSales evidence')
for sale in recent:
    if not isinstance(sale, dict):
        raise SystemExit(f'FAIL: malformed verified sale: {sale!r}')
    price = sale.get('soldPriceEur')
    if not isinstance(price, (int, float)) or price <= 0:
        raise SystemExit(f'FAIL: verified sale has invalid EUR price: {sale!r}')

print(
    f'PRICE:{expected_variant}:{mean:.2f}:{low:.2f}:{high:.2f}:{samples}'
)
PY
    )"; then
      return 1
    fi

    case "$classification" in
      PRICE:*)
        IFS=':' read -r _ chosen_variant mean low high samples <<<"$classification"
        echo "OK: direct Cardyssey eBay pricing -> variant $chosen_variant, mean $mean EUR, range $low-$high EUR from $samples verified sale(s)."
        found_quote=1
        break
        ;;
      EMPTY:*)
        echo "INFO: no verified direct eBay sales for exact variant $variant_id."
        ;;
      *)
        echo "FAIL: unexpected eBay probe classification: $classification"
        return 1
        ;;
    esac
  done

  if [ "$found_quote" -eq 0 ]; then
    echo "OK: direct Cardyssey eBay route is healthy; $EBAY_SMOKE_CARD_ID currently has no verified sale for any tested exact variant."
  fi
}
check "Web homepage" "$BASE_WEB_URL/"
check "OpenAPI contract" "$BASE_WEB_URL/contracts/cardyssey.openapi.json"
check_android_metadata
check "Android latest APK" "$ANDROID_APK_URL"
check_api_health
check_status \
  "Central pricing authentication guard" \
  "$BASE_API_URL$API_PREFIX/pricing/cards/__smoke__?language=en&variant=NORMAL" \
  "401"

e2e_login

if [ -n "$E2E_ACCESS_TOKEN" ]; then
  auth_check "Authenticated profile" "/me"
  auth_check "Collection read" "/collection"
  auth_check "Wishlist read" "/wishlist"
  auth_check "Marketplace read" "/marketplace"
  auth_check "Incoming offers read" "/offers/incoming"
  auth_check "Outgoing offers read" "/offers/outgoing"
  ebay_price_check
else
  echo "INFO: E2E credentials not set; authenticated read-only and eBay pricing checks skipped."
fi
