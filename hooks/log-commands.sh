#!/usr/bin/env bash
# Append every Bash command Claude runs to a global log with timestamps.
set +e
cmd=$(jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$cmd" ] && exit 0
cwd=$(jq -r '.tool_input.cwd // empty' 2>/dev/null)
[ -z "$cwd" ] && cwd="$PWD"
printf '%s [%s] %s\n' "$(date -Iseconds)" "$cwd" "$cmd" >> "$HOME/.claude/command-log.txt"
exit 0
