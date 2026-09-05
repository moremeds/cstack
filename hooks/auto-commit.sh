#!/usr/bin/env bash
# Auto-commit on Stop: opt-in per project via ".claude/auto-commit" marker.
# Only commits the explicitly staged selection in an opted-in repository.
# Never stages work: the Stop event cannot establish ownership of dirty files.
set +e
cd "${CLAUDE_PROJECT_DIR:-$PWD}" || exit 0
[ -f ".claude/auto-commit" ] || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

if ! git diff --cached --quiet; then
  git commit -q -m "chore(ai): apply Claude edit" >/dev/null 2>&1
fi
exit 0
