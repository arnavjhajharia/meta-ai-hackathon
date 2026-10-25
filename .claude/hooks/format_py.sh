#!/usr/bin/env bash
# PostToolUse: format and lint-fix any Python file Claude just wrote or edited.
f=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
case "$f" in *.py) ;; *) exit 0 ;; esac
RUFF="$CLAUDE_PROJECT_DIR/.venv/bin/ruff"; [ -x "$RUFF" ] || RUFF=$(command -v ruff) || exit 0
"$RUFF" format -q "$f" 2>/dev/null
"$RUFF" check --fix -q "$f" 1>&2 || true
exit 0
