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
  code="$(curl -L -sS --connect-timeout 12 --max-time 45 -o /tmp/cardyssey-api-health.json -w '%{http_code}' "$url" || true)"
  if [ "$code" != "200" ]; then
    echo "FAIL: API health -> HTTP $code"
    cat /tmp/cardyssey-api-health.json 2>/dev/null || true
    return 1
  fi

  python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path('/tmp/cardyssey-api-health.json').read_text())
if data.get('status') != 'ok':
    raise SystemExit(f"FAIL: API health status={data.get('status')!r}")
if data.get('database') != 'connected':
    raise SystemExit(f"FAIL: API database={data.get('database')!r}")
if data.get('version') != '0.2.3':
    raise SystemExit(
        f"FAIL: production backend is stale: version={data.get('version')!r}, expected='0.2.3'"
    )
if 'compSniperConfigured' not in data:
    raise SystemExit('FAIL: production backend has not picked up the multi-provider eBay health contract')
if data.get('soldCompsConfigured') is not True:
    raise SystemExit('FAIL: production backend has no SOLDCOMPS_API_KEY fallback configured')
if data.get('soldCompsEbaySessionConfigured') is not True:
    raise SystemExit('FAIL: production backend has no authenticated SoldComps eBay fallback session configured')
cache_ttl = data.get('ebayPriceCacheTtlHours')
if not isinstance(cache_ttl, int) or cache_ttl <= 0:
    raise SystemExit(f'FAIL: invalid eBay price cache TTL: {cache_ttl!r}')

print(
    'OK: API health -> '
    f"version {data.get('version', 'unknown')}, "
    f"CompSniper={'configured' if data.get('compSniperConfigured') else 'not configured'}, "
    f"SoldComps fallback configured, eBay session=configured, cache TTL={cache_ttl}h"
)
PY
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
  url="$BASE_API_URL$API_PREFIX/pricing/cards/$EBAY_SMOKE_CARD_ID?language=$EBAY_SMOKE_LANGUAGE&condition=NEAR_MINT&market=EBAY"
  code="$(curl -sS --connect-timeout 12 --max-time 90 -o /tmp/cardyssey-smoke-ebay.json -w '%{http_code}' \
    -H "Authorization: Bearer $E2E_ACCESS_TOKEN" \
    "$url" || true)"

  if [ "$code" != "200" ]; then
    echo "FAIL: eBay production pricing probe -> HTTP $code"
    cat /tmp/cardyssey-smoke-ebay.json 2>/dev/null || true
    return 1
  fi

  python3 - <<'PY'
import json
from pathlib import Path

path = Path('/tmp/cardyssey-smoke-ebay.json')
data = json.loads(path.read_text())
market = data.get('market')
source = data.get('source')
mean = data.get('eur')
low = data.get('rangeLowEur')
high = data.get('rangeHighEur')
samples = data.get('sampleCount')

if market != 'EBAY':
    raise SystemExit(f'FAIL: eBay pricing probe returned market={market!r}')
if source not in {'COMPSNIPER', 'SOLDCOMPS'}:
    raise SystemExit(f'FAIL: eBay pricing probe has no supported sold provider quote (source={source!r})')
if not isinstance(mean, (int, float)) or mean <= 0:
    raise SystemExit(f'FAIL: eBay pricing probe has invalid mean eur={mean!r}')
if not isinstance(low, (int, float)) or low <= 0:
    raise SystemExit(f'FAIL: eBay pricing probe has invalid rangeLowEur={low!r}')
if not isinstance(high, (int, float)) or high <= 0:
    raise SystemExit(f'FAIL: eBay pricing probe has invalid rangeHighEur={high!r}')
if low > high:
    raise SystemExit(f'FAIL: eBay pricing range is reversed: {low!r}..{high!r}')
if mean < low - 1e-9 or mean > high + 1e-9:
    raise SystemExit(f'FAIL: eBay mean {mean!r} lies outside sold range {low!r}..{high!r}')
if not isinstance(samples, int) or samples < 1:
    raise SystemExit(f'FAIL: eBay pricing probe has invalid sampleCount={samples!r}')

print(
    f'OK: eBay production pricing -> provider {source}, mean {mean:.2f} EUR, '
    f'range {low:.2f}-{high:.2f} EUR from {samples} sold comp(s)'
)
PY
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
