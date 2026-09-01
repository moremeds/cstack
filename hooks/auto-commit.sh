#!/usr/bin/env bash
# Auto-commit on Stop: opt-in per project via ".claude/auto-commit" marker.
# Only runs inside a git repo that explicitly enabled this.
set +e
cd "${CLAUDE_PROJECT_DIR:-$PWD}" || exit 0
[ -f ".claude/auto-commit" ] || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

git add -A
if ! git diff --cached --quiet; then
  git commit -q -m "chore(ai): apply Claude edit" >/dev/null 2>&1
fi
exit 0
