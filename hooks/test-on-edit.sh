#!/usr/bin/env bash
# Test-on-edit: opt-in per project via ".claude/test-on-edit" marker.
# Walks up from the edited file to find the nearest project root containing
# that marker. Runs npm test (node) or pytest (python). Tails output.
set +e
file=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$file" ] && exit 0

# Walk up to find marker + project type.
root=""
dir=$(dirname "$file")
while [ "$dir" != "/" ] && [ -n "$dir" ]; do
  if [ -f "$dir/.claude/test-on-edit" ]; then
    root="$dir"
    break
  fi
  dir=$(dirname "$dir")
done
[ -z "$root" ] && exit 0

cd "$root" || exit 0
case "$file" in
  *.py)
    if command -v pytest >/dev/null 2>&1; then
      timeout 60 pytest -q 2>&1 | tail -5
    fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
    if [ -f package.json ] && jq -e '.scripts.test' package.json >/dev/null 2>&1; then
      timeout 60 npm run test --silent 2>&1 | tail -5
    fi
    ;;
esac
exit 0
