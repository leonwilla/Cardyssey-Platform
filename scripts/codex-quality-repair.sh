#!/usr/bin/env bash
# Bounded self-repair attempt based on actual Cardmarket DE/EN quality gaps.
set -euo pipefail
umask 077
ROOT=/home/tv/cardshop
LAB=/home/tv/cardyssey-codex-lab
STATE=/home/tv/.local/state/cardyssey-codex
CODEX=/home/tv/.local/npm/bin/codex
mkdir -p "$STATE"
exec 9>"$STATE/repair.lock"
flock -n 9 || { echo "REPAIR_ALREADY_RUNNING"; exit 0; }
"$CODEX" login status >/dev/null 2>&1 || { echo "CHATGPT_LOGIN_REQUIRED"; exit 0; }
python3 "$ROOT/scripts/cardmarket/core/cardmarket-quality-gate.py" > "$STATE/quality-last-run.json"
set +e
python3 - "$STATE/quality-last-run.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
if x["status"] != "QUALITY_GAP":
 print("QUALITY_OK_NO_REPAIR_NEEDED")
 raise SystemExit(10)
PY
rc=$?
set -e
if [ "$rc" = 10 ]; then exit 0; fi
if [ "$rc" != 0 ]; then exit "$rc"; fi
if [ ! -d "$LAB/.git" ] && [ ! -f "$LAB/.git" ]; then
  git -C "$ROOT" worktree add --detach "$LAB" HEAD
fi
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
cp "$STATE/quality-last-run.json" "$STATE/before-$STAMP.json"
cat > "$STATE/task-$STAMP.txt" <<EOF
You are working on Cardyssey in an ISOLATED Git worktree, not production.
Read /home/tv/cardshop/scripts/cardmarket/core/cardmarket-quality-gate.py and the before quality JSON at $STATE/before-$STAMP.json.
Improve source code and automated tests for the GREATEST root cause of missing Cardmarket DE/EN IDs/URLs first.
There are 19,284 DE and 21,291 EN catalog cards. Avoid assuming product identities or substituting German prices for English.
A provider product candidate is not a verified print, edition, language, or NM condition. Preserve those distinctions.
Write a specific test for your fix, run relevant unit tests, and report before/after expected changes.
Do not alter production database, launch browser collectors, evade site access controls, write credentials, use API keys,
push to GitHub, deploy, or fabricate prices or URLs. Do not remove existing data.
Prefer official Cardmarket product catalog/priceguide files and existing evidence.
If a fix needs new verification evidence, report exactly why, instead of guessing.
Do not edit files outside this worktree. Write code/test changes here only.
EOF
echo "STARTING_CODEX_$STAMP"
set +e
/usr/bin/timeout --signal=TERM --kill-after=30s 1800s "$CODEX" exec \
  -C "$LAB" --sandbox workspace-write --color never \
  -o "$STATE/last-agent-answer.txt" \
  - < "$STATE/task-$STAMP.txt" > "$STATE/run-$STAMP.log" 2>&1
rc=$?
set -e
echo "$rc" > "$STATE/exit-$STAMP.txt"
git -C "$LAB" status --short > "$STATE/diff-$STAMP.txt"
echo "CODEX_EXIT=$rc LOG=$STATE/run-$STAMP.log CHANGES=$STATE/diff-$STAMP.txt"
exit "$rc"
