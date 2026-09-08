#!/usr/bin/env bash

BASE_WEB_URL="${BASE_WEB_URL:-https://cardyssey.de}"
BASE_API_URL="${BASE_API_URL:-https://api.cardyssey.de}"

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

check "Web homepage" "$BASE_WEB_URL/"
check "OpenAPI contract" "$BASE_WEB_URL/contracts/cardyssey.openapi.json"
check "Android release metadata" "$BASE_WEB_URL/api/android/latest"
check "API health" "$BASE_API_URL/health"

if [ -n "${E2E_ACCESS_TOKEN:-}" ]; then
  auth_check() {
    label="$1"
    path="$2"
    code="$(curl -sS -o /tmp/cardyssey-smoke-auth-body -w '%{http_code}' \
      -H "Authorization: Bearer $E2E_ACCESS_TOKEN" \
      "$BASE_API_URL$path" || true)"
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
