#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.." &&
  pwd
)"

cd "$ROOT"

python3 scripts/write-contract.py

scripts/contract-check.sh

scripts/generate-clients.sh

echo
echo "=== CONTRACT PIPELINE OK ==="
