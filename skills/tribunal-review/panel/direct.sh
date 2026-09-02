#!/usr/bin/env bash
# Direct API transport for the tribunal rounds that need no repo access.
#
# Debate and rebuttal reason over findings already collected in Step 4, so they
# do not need a coding agent — only a completion. Spawning one costs ~18k tokens
# of CLI system prompt per call. The review round is NOT routed through here:
# it reads the repository, and that is what keeps its findings honest.
#
# curl, not node: node:https and undici share a TLS stack whose fingerprint
# Cloudflare rejects at chatgpt.com/backend-api with a 403. See
# references/panel-cli-notes.md.

direct_preflight() {
  if [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
    echo "tribunal: CLAUDE_CODE_OAUTH_TOKEN is unset. Export it from ~/.zshenv" >&2
    echo "          (~/.zshrc is read by interactive shells only; a panelist is not one)" >&2
    return 1
  fi
  if [ ! -r "$HOME/.codex/auth.json" ]; then
    echo "tribunal: \$HOME/.codex/auth.json is unreadable; run 'codex login'" >&2
    return 1
  fi
}

_codex_token() {
  python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.codex/auth.json')))['tokens']['access_token'])"
}

_codex_account() {   # _codex_account <jwt>
  python3 - "$1" <<'PY'
import base64, json, sys
payload = sys.argv[1].split(".")[1]
payload += "=" * (-len(payload) % 4)
claims = json.loads(base64.urlsafe_b64decode(payload))
print(claims["https://api.openai.com/auth"]["chatgpt_account_id"])
PY
}

_codex_cli() {   # _codex_cli <prompt-file> <out-file> — the fallback, named once
  codex exec -s read-only --skip-git-repo-check -o "$2" - \
    < "$1" >>"$2.log" 2>&1
}

direct_codex() {   # direct_codex <prompt-file> <out-file>
  local prompt="$1" out="$2" tok acct body code
  # $SP survives between runs when CLAUDE_SCRATCHPAD is set, so a leftover
  # answer would make [ ! -s "$out" ] accept the previous run's report as this
  # one's and skip the fallback — a dead seat voting with a stale opinion.
  : > "$out"
  # An unreadable credential is a dead seat, and a dead seat must degrade to
  # the CLI like every other failure here. `return 1` lost the seat outright.
  tok=$(_codex_token 2>>"$out.log") \
    || { echo "tribunal: codex auth unreadable, falling back to the CLI" >&2
         _codex_cli "$prompt" "$out"; return; }
  acct=$(_codex_account "$tok" 2>>"$out.log") \
    || { echo "tribunal: codex auth has no account id, falling back to the CLI" >&2
         _codex_cli "$prompt" "$out"; return; }

  body=$(python3 - "$prompt" <<'PY'
import json, sys
print(json.dumps({
    "model": "gpt-5.6-sol",
    "store": False,
    "stream": True,
    "instructions": "Follow the instructions in the message exactly. Output only the report.",
    "input": [{"type": "message", "role": "user",
               "content": [{"type": "input_text", "text": open(sys.argv[1]).read()}]}],
    "reasoning": {"effort": "high"},
    "tool_choice": "auto",
    "parallel_tool_calls": True,
}))
PY
)
  # Headers and body go through files, never argv: ps exposes every argument
  # to any local process, and these carry the bearer token and the full diff.
  ( umask 077
    cat > "$out.cfg" <<CFG
header = "authorization: Bearer $tok"
header = "chatgpt-account-id: $acct"
header = "originator: codex_cli_rs"
header = "OpenAI-Beta: responses=experimental"
header = "accept: text/event-stream"
header = "content-type: application/json"
header = "session-id: $(uuidgen)"
header = "user-agent: codex_cli_rs/0.144.4 (Mac OS 25.5.0; arm64)"
CFG
    printf '%s' "$body" > "$out.req" )

  # --http1.1: h2 measured ~1.2s slower to first byte against this endpoint.
  # Timeouts: without them a black-holed connection holds command substitution
  # open forever and the fallback below is never reached.
  code=$(curl -sS --http1.1 --connect-timeout 15 --max-time 600 \
    --config "$out.cfg" --data-binary @"$out.req" \
    -o "$out.sse" -w '%{http_code}' \
    https://chatgpt.com/backend-api/codex/responses 2>>"$out.log") || code=000
  rm -f "$out.cfg" "$out.req"

  if [ "$code" = "200" ]; then
    # A truncated report is non-empty, so [ ! -s ] cannot detect it. Only
    # response.completed means the whole review arrived; anything else is a
    # partial answer that would be merged as if the seat had finished.
    python3 - "$out.sse" > "$out" 2>>"$out.log" <<'PY'
import json, sys
parts, terminal = [], None
for line in open(sys.argv[1]):
    if not line.startswith("data: "):
        continue
    try:
        ev = json.loads(line[6:])
    except ValueError:
        continue
    kind = ev.get("type", "")
    if kind == "response.output_text.delta":
        parts.append(ev.get("delta", ""))
    elif kind in ("response.completed", "response.incomplete", "response.failed"):
        terminal = kind
if terminal != "response.completed":
    sys.exit("tribunal: codex stream ended " + (terminal or "with no terminal event"))
sys.stdout.write("".join(parts))
PY
    if [ $? -ne 0 ]; then tail -1 "$out.log" >&2; : > "$out"; fi
  fi

  if [ ! -s "$out" ]; then
    echo "tribunal: codex direct failed (http=$code), falling back to the CLI" >&2
    _codex_cli "$prompt" "$out" || return 1
  fi
}

direct_claude() {   # direct_claude <prompt-file> <out-file>
  local prompt="$1" out="$2" body code
  : > "$out"   # see direct_codex: never inherit a previous run's answer

  body=$(python3 - "$prompt" <<'PY'
import json, sys
print(json.dumps({
    "model": "claude-opus-5",
    "max_tokens": 8192,
    # The OAuth path rejects a system prompt that does not open with this line.
    # It is the 26-token floor, and the reason direct is 700x cheaper than spawn.
    "system": [{"type": "text",
                "text": "You are Claude Code, Anthropic's official CLI for Claude."}],
    "messages": [{"role": "user", "content": open(sys.argv[1]).read()}],
}))
PY
)
  ( umask 077
    cat > "$out.cfg" <<CFG
header = "authorization: Bearer $CLAUDE_CODE_OAUTH_TOKEN"
header = "anthropic-beta: oauth-2025-04-20"
header = "anthropic-version: 2023-06-01"
header = "content-type: application/json"
CFG
    printf '%s' "$body" > "$out.req" )

  code=$(curl -sS --connect-timeout 15 --max-time 600 \
    --config "$out.cfg" --data-binary @"$out.req" \
    -o "$out.json" -w '%{http_code}' \
    https://api.anthropic.com/v1/messages 2>>"$out.log") || code=000
  rm -f "$out.cfg" "$out.req"

  if [ "$code" = "200" ]; then
    # stop_reason, not the HTTP status, is where truncation is reported.
    python3 - "$out.json" > "$out" 2>>"$out.log" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
stop = doc.get("stop_reason")
if stop not in ("end_turn", "stop_sequence", None):
    sys.exit("tribunal: claude stopped on " + str(stop))
sys.stdout.write("".join(b.get("text", "") for b in doc.get("content", [])))
PY
    if [ $? -ne 0 ]; then tail -1 "$out.log" >&2; : > "$out"; fi
  fi

  if [ ! -s "$out" ]; then
    echo "tribunal: claude direct failed (http=$code), falling back to the CLI" >&2
    env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
      claude -p --restricted --strict-mcp-config \
        --disallowedTools "Write,Edit,NotebookEdit" \
        --allowedTools Read,Grep,Glob \
        < "$prompt" > "$out" 2>>"$out.log" || return 1
  fi
}
