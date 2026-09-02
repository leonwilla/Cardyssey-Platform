#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.." &&
  pwd
)"

SPEC="$ROOT/contracts/cardyssey.openapi.json"

echo "=== REDOCLY ==="

cd "$ROOT"

npx --yes \
  @redocly/cli@2.49.0 \
  lint \
  --extends=minimal \
  "$SPEC"

echo
echo "=== OPENAPI GENERATOR ==="

docker run \
  --rm \
  -v "$ROOT:/local" \
  openapitools/openapi-generator-cli:v7.24.0 \
  validate \
  -i /local/contracts/cardyssey.openapi.json

echo
echo "CONTRACT OK"
