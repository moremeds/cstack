#!/usr/bin/env bash
# Universal post-write formatter. Runs after Write/Edit.
# Reads Claude hook JSON from stdin, dispatches formatter by extension.
# Always exits 0 so formatter failures never block edits.

set +e
file=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$file" ] && exit 0
[ ! -f "$file" ] && exit 0

case "$file" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format "$file" >/dev/null 2>&1
      ruff check --fix --select I "$file" >/dev/null 2>&1
    elif command -v black >/dev/null 2>&1; then
      black -q "$file" >/dev/null 2>&1
    fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.jsonc|*.css|*.scss|*.md|*.mdx|*.html|*.yml|*.yaml)
    # Walk up from the file's directory to find the nearest node_modules/.bin/prettier.
    prettier_bin=""
    dir=$(dirname "$file")
    while [ "$dir" != "/" ] && [ -n "$dir" ]; do
      if [ -x "$dir/node_modules/.bin/prettier" ]; then
        prettier_bin="$dir/node_modules/.bin/prettier"
        break
      fi
      dir=$(dirname "$dir")
    done
    if [ -n "$prettier_bin" ]; then
      "$prettier_bin" --write --log-level=silent "$file" >/dev/null 2>&1
    elif command -v prettier >/dev/null 2>&1; then
      prettier --write --log-level=silent "$file" >/dev/null 2>&1
    else
      npx --no-install prettier --write --log-level=silent "$file" >/dev/null 2>&1
    fi
    ;;
esac

exit 0
