#!/usr/bin/env bash
# File-scoped linter after Write/Edit. Dispatches by extension.
# Outputs <=10 lines so Claude can react. Always exits 0.
set +e
file=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$file" ] && exit 0
[ ! -f "$file" ] && exit 0

case "$file" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      out=$(ruff check "$file" 2>&1)
      [ -n "$out" ] && echo "$out" | tail -10
    fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
    # Find nearest eslint binary walking up.
    eslint_bin=""
    dir=$(dirname "$file")
    while [ "$dir" != "/" ] && [ -n "$dir" ]; do
      if [ -x "$dir/node_modules/.bin/eslint" ]; then
        eslint_bin="$dir/node_modules/.bin/eslint"
        break
      fi
      dir=$(dirname "$dir")
    done
    if [ -n "$eslint_bin" ]; then
      out=$("$eslint_bin" --fix "$file" 2>&1)
      [ -n "$out" ] && echo "$out" | tail -10
    fi
    ;;
esac
exit 0
