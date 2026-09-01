#!/usr/bin/env bash
# PreToolUse(Bash) gate for the global CLAUDE.md rule "Never merge before CI is
# green." When the command is a `gh pr merge`, run `gh pr checks` for that PR
# first and block (exit 2) if any check is failing or still pending.
#
# Replaces the dead require-tests-for-pr.sh wiring, which was bound to an
# uninstalled github-MCP tool while real merges go through the gh CLI.

set -uo pipefail

payload="$(cat)"

if command -v jq >/dev/null 2>&1; then
  command_text="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null)"
  cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null)"
else
  exit 0
fi

[[ -z "$command_text" ]] && exit 0
[[ "$command_text" != *"gh pr merge"* ]] && exit 0
command -v gh >/dev/null 2>&1 || exit 0

# Extract an explicit PR number/URL argument if one was given. Flags may
# precede it (`gh pr merge --squash 123`), so scan every token after `merge`;
# strip quoted strings first so numbers inside --subject/--body aren't picked.
merge_tail="${command_text#*gh pr merge}"
stripped="$(printf '%s' "$merge_tail" | sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g")"
pr_arg=""
for tok in $stripped; do
  case "$tok" in
    ';'|'&&'|'||'|'|') break ;;
    -*) : ;;
    http://*|https://*) pr_arg="$tok"; break ;;
    *[!0-9]*|'') : ;;
    *) pr_arg="$tok"; break ;;
  esac
done

[[ -n "$cwd" && -d "$cwd" ]] && cd "$cwd" 2>/dev/null

# JSON is deterministic — no parsing of human-readable check tables.
rollup="$(gh pr view ${pr_arg:+"$pr_arg"} --json statusCheckRollup -q '.statusCheckRollup' 2>&1)" || exit 0

# No checks configured → nothing to wait for; allow.
[[ -z "$rollup" || "$rollup" == "[]" || "$rollup" == "null" ]] && exit 0

not_green="$(printf '%s' "$rollup" | jq -r '[.[] | select((.status // "COMPLETED") != "COMPLETED" or ((.conclusion // .state // "") | ascii_upcase | IN("SUCCESS","NEUTRAL","SKIPPED") | not))] | length' 2>/dev/null)"

if [[ -z "$not_green" ]]; then
  # jq parse failure — fail open but say so.
  echo "ci-green-before-merge: could not parse check rollup; not blocking."
  exit 0
fi

if [[ "$not_green" != "0" ]]; then
  echo "BLOCKED by ci-green-before-merge: $not_green check(s) not green for this PR" >&2
  echo "(global CLAUDE.md: 'Never merge before CI is green')." >&2
  printf '%s' "$rollup" | jq -r '.[] | "  \(.name // .context): \(.status // "COMPLETED") \(.conclusion // .state // "")"' 2>/dev/null | head -15 >&2
  echo "Wait for all checks to pass, then retry the merge." >&2
  exit 2
fi

exit 0
