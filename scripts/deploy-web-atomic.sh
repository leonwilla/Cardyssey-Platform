#!/usr/bin/env bash
# Compatibility entrypoint: Cardyssey deployments no longer require sudo.
set -Eeuo pipefail
exec "$(dirname "$0")/deploy-web-unprivileged.sh" deploy
