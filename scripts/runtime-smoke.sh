#!/usr/bin/env bash

BASE_WEB_URL="${BASE_WEB_URL:-https://cardyssey.de}"
BASE_API_URL="${BASE_API_URL:-https://api.cardyssey.de}"
API_PREFIX="${API_PREFIX:-/api/v1}"
ANDROID_APK_URL="${ANDROID_APK_URL:-https://github.com/leonwilla/Cardyssey-Downloads/releases/latest/download/cardyssey-latest.apk}"

check() {
  label="$1"
  url="$2"
  code="$(curl -L -sS -o /tmp/cardyssey-smoke-body -w '%{http_code}' "$url" || true)"
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
  code="$(curl -L -sS -o /tmp/cardyssey-smoke-status-body -w '%{http_code}' "$url" || true)"
  if [ "$code" != "$expected" ]; then
    echo "FAIL: $label -> HTTP $code (expected $expected)"
    cat /tmp/cardyssey-smoke-status-body 2>/dev/null || true
    return 1
  fi
  echo "OK: $label -> HTTP $code"
}

check_android_metadata() {
  url="$BASE_WEB_URL/api/android/latest"
  code="$(curl -L -sS -o /tmp/cardyssey-android-release.json -w '%{http_code}' "$url" || true)"
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

check "Web homepage" "$BASE_WEB_URL/"
check "OpenAPI contract" "$BASE_WEB_URL/contracts/cardyssey.openapi.json"
check_android_metadata
check "Android latest APK" "$ANDROID_APK_URL"
check "API health" "$BASE_API_URL$API_PREFIX/health"
check_status \
  "Central pricing authentication guard" \
  "$BASE_API_URL$API_PREFIX/pricing/cards/__smoke__?language=en&variant=NORMAL" \
  "401"

if [ -n "${E2E_ACCESS_TOKEN:-}" ]; then
  auth_check() {
    label="$1"
    path="$2"
    code="$(curl -sS -o /tmp/cardyssey-smoke-auth-body -w '%{http_code}' \
      -H "Authorization: Bearer $E2E_ACCESS_TOKEN" \
      "$BASE_API_URL$API_PREFIX$path" || true)"
    if [ "$code" != "200" ]; then
      echo "FAIL: $label -> HTTP $code"
      cat /tmp/cardyssey-smoke-auth-body 2>/dev/null || true
      return 1
    fi
    echo "OK: $label"
  }

  auth_check "Authenticated profile" "/auth/me"
  auth_check "Collection read" "/collection"
  auth_check "Wishlist read" "/wishlist"
  auth_check "Marketplace read" "/marketplace"
  auth_check "Incoming offers read" "/offers/incoming"
  auth_check "Outgoing offers read" "/offers/outgoing"
else
  echo "INFO: E2E_ACCESS_TOKEN not set; authenticated read-only checks skipped."
fi
