#!/usr/bin/env bash
# Stop: Claude may not end a turn with failing lint or tests after changing Python.
# Exit code 2 feeds stderr back to Claude so it keeps working.
active=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("stop_hook_active", False))')
[ "$active" = "True" ] && exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0
[ -d tests ] || exit 0
# Only gate turns that touched Python.
if git rev-parse --git-dir >/dev/null 2>&1; then
  changed=$(git status --porcelain -- '*.py' | head -1)
  [ -z "$changed" ] && exit 0
fi
PY="$CLAUDE_PROJECT_DIR/.venv/bin/python"; [ -x "$PY" ] || PY=python3
if ! out=$("$PY" -m ruff check . 2>&1); then
  echo "Lint is failing. Fix before stopping:" >&2; echo "$out" | tail -30 >&2; exit 2
fi
if ! out=$("$PY" -m pytest -q -x 2>&1); then
  echo "Tests are failing. Fix before stopping (use the look skill if a clip test failed):" >&2
  echo "$out" | tail -40 >&2; exit 2
fi
exit 0
