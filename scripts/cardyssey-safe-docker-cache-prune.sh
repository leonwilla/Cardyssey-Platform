#!/usr/bin/env bash
# Weekly, non-destructive builder cache maintenance.
# No Docker volumes, containers, databases, or in-use images are deleted.
set -Eeuo pipefail
exec 9>/tmp/cardyssey-safe-docker-cache-prune.lock
flock -n 9 || exit 0
if ! docker info >/dev/null 2>&1; then exit 0; fi
# Only unused builder cache entries older than 7 days.
docker builder prune --force --filter 'until=168h' 2>&1 | tail -5
# Only dangling, unused images older than 7 days; no -a.
docker image prune --force --filter 'until=168h' 2>&1 | tail -5
