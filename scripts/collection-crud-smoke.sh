#!/usr/bin/env bash
set -euo pipefail

BASE_API_URL="${CARDYSSEY_API_URL:-https://api.cardyssey.de}"
API_PREFIX="${CARDYSSEY_API_PREFIX:-/api/v1}"

if [[ -z "${E2E_EMAIL:-}" || -z "${E2E_PASSWORD:-}" ]]; then
  echo "FAIL: E2E_EMAIL and E2E_PASSWORD are required"
  exit 1
fi

TMP_DIR="$(mktemp -d)"
ACCESS_TOKEN=""
REFRESH_TOKEN=""
KEY="cardyssey-smoke-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"

cleanup() {
  set +e

  if [[ -n "$ACCESS_TOKEN" ]]; then
    curl -sS --connect-timeout 10 --max-time 30 \
      -X DELETE \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      "$BASE_API_URL$API_PREFIX/collection/$KEY" \
      >/dev/null 2>&1 || true
  fi

  if [[ -n "$REFRESH_TOKEN" ]]; then
    python3 - "$TMP_DIR/logout.json" "$REFRESH_TOKEN" <<'PY'
import json
import sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({"refreshToken": sys.argv[2]}))
PY
    curl -sS --connect-timeout 10 --max-time 30 \
      -X POST \
      -H 'Content-Type: application/json' \
      --data-binary "@$TMP_DIR/logout.json" \
      "$BASE_API_URL$API_PREFIX/auth/logout" \
      >/dev/null 2>&1 || true
  fi

  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

export E2E_EMAIL E2E_PASSWORD
python3 - "$TMP_DIR/login.json" <<'PY'
import json
import os
import sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
    "email": os.environ["E2E_EMAIL"],
    "password": os.environ["E2E_PASSWORD"],
}))
PY

LOGIN_CODE="$(curl -sS --connect-timeout 12 --max-time 45 \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@$TMP_DIR/login.json" \
  -o "$TMP_DIR/login-response.json" \
  -w '%{http_code}' \
  "$BASE_API_URL$API_PREFIX/auth/login" || true)"

if [[ "$LOGIN_CODE" != "200" ]]; then
  echo "FAIL: login -> HTTP $LOGIN_CODE"
  exit 1
fi

readarray -t TOKENS < <(python3 - "$TMP_DIR/login-response.json" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
print(data.get("accessToken", ""))
print(data.get("refreshToken", ""))
PY
)
ACCESS_TOKEN="${TOKENS[0]:-}"
REFRESH_TOKEN="${TOKENS[1]:-}"

if [[ -z "$ACCESS_TOKEN" || -z "$REFRESH_TOKEN" ]]; then
  echo "FAIL: login response did not contain both tokens"
  exit 1
fi

echo "OK: login"

python3 - "$TMP_DIR/item-create.json" "$KEY" <<'PY'
import json
import sys
from pathlib import Path
key = sys.argv[2]
Path(sys.argv[1]).write_text(json.dumps({
    "key": key,
    "cardId": "smoke-card",
    "languageCode": "de",
    "name": "Cardyssey Smoke Test",
    "setId": "smoke",
    "setName": "Smoke Test",
    "localId": "1",
    "variant": "NORMAL",
    "condition": "NEAR_MINT",
    "quantity": 1,
    "marketUnitEur": {"TCG": 1.23},
    "marketSampleCount": {"TCG": 1}
}))
PY

CREATE_CODE="$(curl -sS --connect-timeout 12 --max-time 45 \
  -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  --data-binary "@$TMP_DIR/item-create.json" \
  -o "$TMP_DIR/create-response.json" \
  -w '%{http_code}' \
  "$BASE_API_URL$API_PREFIX/collection" || true)"

if [[ "$CREATE_CODE" != "201" ]]; then
  echo "FAIL: collection create -> HTTP $CREATE_CODE"
  cat "$TMP_DIR/create-response.json" 2>/dev/null || true
  exit 1
fi

echo "OK: create"

get_collection() {
  local output="$1"
  local code
  code="$(curl -sS --connect-timeout 12 --max-time 45 \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -o "$output" \
    -w '%{http_code}' \
    "$BASE_API_URL$API_PREFIX/collection" || true)"
  if [[ "$code" != "200" ]]; then
    echo "FAIL: collection read -> HTTP $code"
    exit 1
  fi
}

get_collection "$TMP_DIR/after-create.json"
python3 - "$TMP_DIR/after-create.json" "$KEY" <<'PY'
import json
import sys
from pathlib import Path
items = json.loads(Path(sys.argv[1]).read_text())
key = sys.argv[2]
match = next((item for item in items if item.get("key") == key), None)
if match is None:
    raise SystemExit("FAIL: created item not found")
if match.get("quantity") != 1:
    raise SystemExit(f"FAIL: created quantity={match.get('quantity')!r}")
if abs((match.get("positionValueEur") or {}).get("TCG", 0) - 1.1316) > 1e-6:
    raise SystemExit(f"FAIL: central valuation mismatch: {match.get('positionValueEur')!r}")
print("OK: create verified")
PY

python3 - "$TMP_DIR/item-update.json" "$KEY" <<'PY'
import json
import sys
from pathlib import Path
key = sys.argv[2]
Path(sys.argv[1]).write_text(json.dumps({
    "key": key,
    "cardId": "smoke-card",
    "languageCode": "de",
    "name": "Cardyssey Smoke Test",
    "setId": "smoke",
    "setName": "Smoke Test",
    "localId": "1",
    "variant": "NORMAL",
    "condition": "NEAR_MINT",
    "quantity": 2,
    "marketUnitEur": {"TCG": 1.23},
    "marketSampleCount": {"TCG": 1}
}))
PY

UPDATE_CODE="$(curl -sS --connect-timeout 12 --max-time 45 \
  -X PUT \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  --data-binary "@$TMP_DIR/item-update.json" \
  -o "$TMP_DIR/update-response.json" \
  -w '%{http_code}' \
  "$BASE_API_URL$API_PREFIX/collection/$KEY" || true)"

if [[ "$UPDATE_CODE" != "200" ]]; then
  echo "FAIL: collection update -> HTTP $UPDATE_CODE"
  cat "$TMP_DIR/update-response.json" 2>/dev/null || true
  exit 1
fi

echo "OK: update"

get_collection "$TMP_DIR/after-update.json"
python3 - "$TMP_DIR/after-update.json" "$KEY" <<'PY'
import json
import sys
from pathlib import Path
items = json.loads(Path(sys.argv[1]).read_text())
key = sys.argv[2]
match = next((item for item in items if item.get("key") == key), None)
if match is None:
    raise SystemExit("FAIL: updated item not found")
if match.get("quantity") != 2:
    raise SystemExit(f"FAIL: updated quantity={match.get('quantity')!r}")
expected = 1.23 * 0.92 * 2
actual = (match.get("positionValueEur") or {}).get("TCG")
if not isinstance(actual, (int, float)) or abs(actual - expected) > 1e-6:
    raise SystemExit(f"FAIL: updated central valuation={actual!r}, expected={expected!r}")
print("OK: update verified")
PY

DELETE_CODE="$(curl -sS --connect-timeout 12 --max-time 45 \
  -X DELETE \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o "$TMP_DIR/delete-response.txt" \
  -w '%{http_code}' \
  "$BASE_API_URL$API_PREFIX/collection/$KEY" || true)"

if [[ "$DELETE_CODE" != "204" ]]; then
  echo "FAIL: collection delete -> HTTP $DELETE_CODE"
  cat "$TMP_DIR/delete-response.txt" 2>/dev/null || true
  exit 1
fi

echo "OK: delete"

get_collection "$TMP_DIR/after-delete.json"
python3 - "$TMP_DIR/after-delete.json" "$KEY" <<'PY'
import json
import sys
from pathlib import Path
items = json.loads(Path(sys.argv[1]).read_text())
key = sys.argv[2]
if any(item.get("key") == key for item in items):
    raise SystemExit("FAIL: deleted item still present")
print("OK: delete verified")
PY

echo "OK: collection CRUD smoke completed"
