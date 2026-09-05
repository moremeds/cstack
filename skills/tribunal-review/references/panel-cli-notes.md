# Panel CLI notes — why each launch flag is what it is

Read this only when a panelist fails to launch, returns nothing, or you are
about to change a flag in Step 3. Every claim here was measured on this
machine; the flags in `SKILL.md` are the conclusions.

## Launch-flag rationale (stripped from Step 3's code block)

```
# Use `codex exec`, NOT `codex exec review`. See the note below — `review`
# cannot take your prompt, so it cannot carry the focus or the output format.
# Embed the diff in the prompt file; `-` reads it from stdin.
# --skip-trust is REQUIRED headless; without it every run dies on the trust dialog.
# -p is what selects headless mode; per `gemini --help` it is APPENDED to stdin,
# so send the bulk (diff + files) on stdin and keep -p short. That avoids the
# $(cat …) escaping trap. Unverified on this machine — Gemini is unlicensed here;
# if stdin turns out to be ignored, fall back to -p "$(cat "$SP/prompt-gemini.md")".
# Measured on cursor-agent 2026.08.11, prompt "create /tmp/x then say DONE":
#   (no mode flag)      → file CREATED. `-p`'s own --help says it "has access to
#     all tools, including write and shell". The published docs claim that
#     without --force "changes are only proposed, not applied" — that is FALSE
#     for file creation. Do not rely on it.
#   --sandbox enabled   → file CREATED. Not a write guard for paths like /tmp.
#   --mode ask          → file NOT created; it answered that it can only give
#     guidance in this mode. This is the one that holds. `--mode plan` is also
#     read-only if you want planning-shaped output instead of Q&A.
# --trust is REQUIRED headless, exactly like Gemini's --skip-trust: without it
# every run dies on the workspace-trust dialog with exit 1 and no output.
# stdin works (verified), so the diff goes on stdin like everyone else's.
# Two traps, both verified:
#  1. --allowedTools is VARIADIC and swallows a trailing positional prompt
#     ("Input must be provided either through stdin or as a prompt argument").
#     Always pipe the prompt on stdin.
#  2. ANTHROPIC_API_KEY takes precedence over the claude.ai login and can fail
#     with "Credit balance is too low". Unset it so the subscription login wins.
#  3. A restrictive Codex seatbelt can block the macOS Keychain, while other
#     Codex permission profiles allow this command. The exact Step 0 probe is
#     authoritative; never predict availability from the orchestrator name.
#  4. NOT --permission-mode plan, and NOT --allowedTools as a guard. Measured on
#     claude 2.1.252, prompt "create /tmp/x then say DONE":
#       --allowedTools Read,Grep,Glob            → file CREATED. allowedTools is
#         an auto-approve list, not a deny list.
#       --disallowedTools Write,Edit,Bash        → file CREATED. The peer routed
#         around it through an MCP server's execute_shell_command, and
#         registered a new project as a further side effect.
#       --permission-mode plan                   → blocked, but wrote a plan file
#         into ~/.claude/plans/ and returned "Approve the plan…" instead of the
#         review. On a review-shaped prompt it usually answers normally; on an
#         analysis-shaped one it does not, and the report is lost.
#       --restricted --strict-mcp-config         → blocked, no plan file, review
#         returned intact. This is the one that holds.
#     --restricted also drops Bash and ignores user/project settings, so the peer
#     gets no hooks and no shell. That is why Step 2 embeds the diff in the
#     prompt: Read/Grep/Glob plus --add-dir is the whole context budget.
#     ("MultiEdit" is not a known tool name — naming it only prints a warning.)
# … your own review happens here …
# Enforce the launch-time deadline across the panel. Poll only the captured
# PIDs; never poll output files and never use a process-name pattern.
```

### Why not `codex exec review`

`codex exec review`'s scope flags are **mutually exclusive with a custom prompt**:

```
$ codex exec review --base master "my instructions"
error: the argument '--base <BRANCH>' cannot be used with '[PROMPT]'
```

Same for `--uncommitted` and `--commit`, and stdin (`-`) counts as a prompt. So
`codex exec review --base X` runs Codex's own built-in review prompt and nothing
else — it cannot carry the focus text, the specialty preamble, or the `ISSUE-N`
output format this skill merges on. It also has no `-C/--cd` and no `-s/--sandbox`.

Use `codex exec -s read-only` and put the diff in your prompt. `codex exec review`
is only useful as a standalone one-shot outside this skill.

## Panelist failures, by error string

| Failure                             | Do                                                                                                         |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Gemini dies on trust                | you forgot `--skip-trust`. Retry once with it                                                              |
| Gemini: "no valid license"          | installed but not entitled. Drop it, note `gemini: unlicensed` in the header, move on                      |
| Cursor: `ERROR: SecItemCopyMatching failed -50` | The active sandbox blocked the Keychain. `CURSOR_API_KEY` may sidestep it (unverified — probe it, do not assume). Otherwise drop the seat and name it in the header; do not generalize the result to every Codex runtime |
| Cursor: "⚠ Workspace Trust Required", exit 1, no output | `--trust` is missing. Headless runs cannot answer the dialog. Same class as Gemini's `--skip-trust` |
| Cursor wrote a file during review | `--mode ask` (or `--mode plan`) was missing. `-p` alone has write and shell access — its own `--help` says so, and the published docs' "without `--force` changes are only proposed" is false for file creation. `--sandbox enabled` does not stop it either |
| Cursor: unknown model id | it does not error usefully — check `cursor-agent --list-models` first. An id that looks right but is not present degrades the review silently, exactly like Gemini's `-m` |
| Codex hangs on network              | retry once with the `env -u *_PROXY` prefix                                                                |
| Claude: "Credit balance is too low" | `ANTHROPIC_API_KEY` is overriding the claude.ai login. Retry with `env -u ANTHROPIC_API_KEY`               |
| Claude: "Not logged in · Please run /login" | The active sandbox may be blocking the Keychain. Do not retry the same command repeatedly; drop the seat and report the probe result. Changing sandbox or credentials requires the user's explicit choice |
| Claude: "Input must be provided…"   | `--allowedTools` ate your positional prompt. Pipe it on stdin instead                                      |
| Claude returns "Approve the plan…" instead of a review, and a file appears in `~/.claude/plans/` | You used `--permission-mode plan`. It is a real read-only guard but it persists a plan and can swallow the report. Use `--restricted --strict-mcp-config` (Step 3, note 4) |
| Claude wrote a file despite `--allowedTools` / `--disallowedTools` | Neither flag is a sandbox — `--allowedTools` only auto-approves, and an MCP server's shell tool routes around a deny list. Only `--restricted --strict-mcp-config` held in testing |


### Why the direct transport uses curl, not Node

`node:https` and `undici` share one TLS stack, and Cloudflare rejects its
fingerprint at `chatgpt.com/backend-api` with a 403. Reordering ciphers to
match curl's does not fix it. Measured 2026-09-02; use `curl`.

### Why only `$CLAUDE_CODE_OAUTH_TOKEN`

`$HOME/.claude/.credentials.json` may still exist holding a token the server
reports as revoked — reading it yields a silent 401 that looks like a dead
seat. The Keychain entry is live but expires within hours. The env var is a
long-lived credential and is the only source `direct.sh` reads. Export it from
`~/.zshenv`: `~/.zshrc` is read by interactive shells only, and a backgrounded
panelist is not one.

### Round split

Review reads the repository and stays on the CLI. Debate and rebuttal do not,
and go direct. Do not "simplify" by routing review through `direct.sh` — that
deletes the check behind `review.md`'s "a wrong file path or line number
discredits every other finding you make."

## Codex direct model selection

Direct debate/rebuttal defaults to `gpt-6-astra` with `low` reasoning.
`TRIBUNAL_CODEX_MODEL` can select another account-supported model; direct and
CLI fallback use that same selection, both with `low` effort. The direct
user-agent version is read from `codex --version`; it is omitted when unknown
instead of inventing a client version. First-pass repository review continues
to use the separate CLI launch in SKILL.md. Model availability must be verified
against the account; selecting a name does not establish access.
