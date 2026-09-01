#!/usr/bin/env bash
# PreToolUse(Bash) guard enforcing three standing rules from global CLAUDE.md:
#   1. BLOCK  git push to origin master/main  ("Always open a PR before merging")
#   2. BLOCK  git commit containing AI attribution trailers (Co-Authored-By: Claude etc.)
#   3. WARN   git add -A / git add .          (risks committing unrelated untracked files)
#
# Exit 2 blocks the tool call (stderr is fed back to the model); exit 0 allows.
# Repos listed in $GIT_GUARD_PR_EXEMPT (colon-separated paths, relative to $HOME
# or absolute) are exempt from rule 1 — for repos whose documented workflow is
# direct commit+push to the default branch. Unset by default: nothing is exempt.

set -uo pipefail

payload="$(cat)"

get_field() {
  local field="$1"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$payload" | jq -r "$field // empty" 2>/dev/null
  else
    printf ''
  fi
}

command_text="$(get_field '.tool_input.command')"
cwd="$(get_field '.cwd')"

[[ -z "$command_text" ]] && exit 0

# --- Rule 2: no AI attribution trailers in commits (applies everywhere) ---
if [[ "$command_text" == *"git commit"* ]]; then
  if printf '%s' "$command_text" | grep -qE 'Co-Authored-By: *Claude|Generated-By:|Assisted-By:'; then
    echo "BLOCKED by git-guard: global CLAUDE.md forbids AI attribution trailers" >&2
    echo "(Co-Authored-By: Claude / Generated-By / Assisted-By). Rewrite the commit" >&2
    echo "message without the trailer." >&2
    exit 2
  fi
fi

# --- Rule 3: warn on git add -A / git add . (applies everywhere, non-blocking) ---
if printf '%s' "$command_text" | grep -qE 'git add ((-A|--all)([[:space:]]|$)|\.([[:space:]]|$))'; then
  echo "git-guard warning: 'git add -A/.' risks staging pre-existing untracked files."
  echo "Prefer staging explicit paths (global CLAUDE.md / execute-plan rule)."
fi

# --- Rule 1: no direct push to origin master/main ---
# Exempt repos with a documented direct-push workflow (see $GIT_GUARD_PR_EXEMPT).
IFS=':' read -ra _exempt <<< "${GIT_GUARD_PR_EXEMPT:-}"
for _e in "${_exempt[@]}"; do
  [[ -z "$_e" ]] && continue
  [[ "$_e" != /* ]] && _e="$HOME/$_e"
  [[ "$cwd" == "$_e"* ]] && exit 0
done

if [[ "$command_text" == *"git push"* ]]; then
  # Token walk: after `git push ... origin`, any non-flag token equal to
  # master/main (or a refspec ending in :master/:main) is a blocked push.
  # `git push` with no refspec (or `... origin HEAD`) pushes the current
  # branch, so those fall back to checking the branch checked out in cwd.
  in_push=0
  saw_origin=0
  blocked=0
  saw_push=0
  saw_ref=0
  check_current_branch=0
  for tok in $command_text; do
    case "$tok" in
      ';'|'&&'|'||'|'|') in_push=0; saw_origin=0 ;;
      push) [[ $in_push -eq 0 ]] && in_push=1 && saw_push=1 ;;
      origin) [[ $in_push -eq 1 ]] && saw_origin=1 ;;
      -*) : ;;
      *)
        if [[ $in_push -eq 1 && $saw_origin -eq 1 ]]; then
          saw_ref=1
          case "$tok" in
            master|main|*:master|*:main) blocked=1 ;;
            HEAD) check_current_branch=1 ;;
          esac
        fi
        ;;
    esac
  done
  # Implicit push: no explicit refspec means git pushes the current branch.
  if [[ $saw_push -eq 1 && $saw_ref -eq 0 ]]; then
    check_current_branch=1
  fi
  if [[ $blocked -eq 0 && $check_current_branch -eq 1 ]]; then
    branch="$(git -C "${cwd:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    case "$branch" in
      master|main) blocked=1 ;;
    esac
  fi
  if [[ $blocked -eq 1 ]]; then
    echo "BLOCKED by git-guard: direct push to origin master/main is forbidden" >&2
    echo "(global CLAUDE.md: 'Always open a PR before merging to master/main')." >&2
    echo "Push the feature branch and open a PR with 'gh pr create' instead." >&2
    exit 2
  fi
fi

exit 0
