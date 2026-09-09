#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.." &&
  pwd
)"

SPEC="/local/contracts/cardyssey.openapi.json"
GENERATOR="openapitools/openapi-generator-cli:v7.24.0"

UID_NOW="$(id -u)"
GID_NOW="$(id -g)"

python3 \
  "$ROOT/scripts/enrich-admin-contract.py"

rm -rf \
  "$ROOT/web/lib/generated/cardyssey" \
  "$ROOT/generated/android-client"

mkdir -p \
  "$ROOT/web/lib/generated/cardyssey" \
  "$ROOT/generated/android-client"


echo "=== TYPESCRIPT CLIENT ==="

docker run \
  --rm \
  --user "${UID_NOW}:${GID_NOW}" \
  -e HOME=/tmp \
  -v "$ROOT:/local" \
  "$GENERATOR" \
  generate \
  -i "$SPEC" \
  -g typescript-fetch \
  -o /local/web/lib/generated/cardyssey \
  --additional-properties \
supportsES6=true,npmName=cardyssey-contract,npmVersion=0.2.0


echo
echo "=== KOTLIN CLIENT ==="

docker run \
  --rm \
  --user "${UID_NOW}:${GID_NOW}" \
  -e HOME=/tmp \
  -v "$ROOT:/local" \
  "$GENERATOR" \
  generate \
  -i "$SPEC" \
  -g kotlin \
  -o /local/generated/android-client \
  --additional-properties \
packageName=de.cardyssey.generated,library=jvm-okhttp4,serializationLibrary=moshi,dateLibrary=java8,artifactId=cardyssey-api-client,artifactVersion=0.2.0


echo
echo "=== GENERATED ==="

echo -n "Web files: "
find \
  "$ROOT/web/lib/generated/cardyssey" \
  -type f \
  | wc -l

echo -n "Android files: "
find \
  "$ROOT/generated/android-client" \
  -type f \
  | wc -l


echo
echo "=== PUBLISH ANDROID CLIENT ==="

python3 - "$ROOT" <<'PYZIP'
from pathlib import Path
import sys
import zipfile

root = Path(sys.argv[1])

source = (
    root
    / "generated/android-client/src/main/kotlin"
)

target = (
    root
    / "web/public/contracts/cardyssey-android-client.zip"
)

target.parent.mkdir(
    parents=True,
    exist_ok=True
)

with zipfile.ZipFile(
    target,
    "w",
    compression=zipfile.ZIP_DEFLATED
) as archive:

    for file in source.rglob("*.kt"):
        archive.write(
            file,
            file.relative_to(source)
        )

print(
    f"Android Client veröffentlicht: {target}"
)
PYZIP
