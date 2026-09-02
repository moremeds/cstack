# Tribunal direct transport — design

## Goal

Cut the per-call overhead of the tribunal panel by calling the model APIs
directly instead of spawning a coding-agent CLI, **without** losing the repo
access that makes the review round trustworthy.

## The measurement that started this

Per-call floor, measured on this machine:

| transport | latency | prompt floor |
| --- | --- | --- |
| `codex exec` (spawn) | 9.7s | 18,241 tokens |
| codex direct (curl) | ~3.0s | 20 tokens |
| `claude -p` (spawn) | 8.0s | large, unmeasured |
| claude direct (curl) | 1.4s | 26 tokens |

The CLI floor is its own system prompt, tool schemas, and `AGENTS.md`
injection. The tribunal never uses any of it: a panelist writes one report and
exits. A full run is three calls per seat, so Codex alone burns ~54,700 tokens
of floor before a single byte of diff.

## Why not convert every round

`prompts/review.md` tells the reviewer *"You are running read-only inside the
repository. Open the touched files"* and then makes it load-bearing: *"a wrong
file path or line number discredits every other finding you make."* That
instruction is the skill's anti-hallucination mechanism, and `codex exec -C
"$REPO_OR_WORKTREE"` is what implements it.

A direct Responses API call is a single completion with no tools. Converting
the review round removes the reviewer's ability to check a claim against the
code — a quality regression disguised as a transport change.

`prompts/debate.md` and `prompts/rebuttal.md` carry no such instruction. They
reason over findings already collected in Step 4. They need no repo access at
all.

## The rule

Split by round, not by seat.

| round | needs the repo | transport |
| --- | --- | --- |
| Step 3 review | yes | CLI, unchanged |
| Step 5 debate | no | direct |
| Step 5 rebuttal | no | direct |

Two of three calls per seat convert. Codex floor per run drops from ~54,700 to
~18,200 tokens; panel latency from ~29s to ~13s. The review round is untouched,
so review quality cannot regress.

## Why this also fixes an under-specification

Step 5 currently ships **no dispatch code** — only prose telling the
orchestrator to "run debate and rebuttal for all contested items in one batched
call each." Every orchestrator improvises it, most likely by copying the Step 3
CLI block. This design gives Step 5 the code it never had.

## Transport

Both seats go through `curl`, not Node. Node's TLS fingerprint is rejected by
Cloudflare at the ChatGPT backend (403); the cipher-order workaround does not
help, because `node:https` and `undici` share the same TLS stack. `curl` is
also what a bash skill already has.

**Codex** — `POST https://chatgpt.com/backend-api/codex/responses`, SSE.
Bearer token from `$HOME/.codex/auth.json` at `.tokens.access_token`;
`chatgpt-account-id` is decoded from that JWT's payload at
`["https://api.openai.com/auth"].chatgpt_account_id`. Reply text arrives as
`response.output_text.delta` events.

**Claude** — `POST https://api.anthropic.com/v1/messages` with
`anthropic-beta: oauth-2025-04-20`. The token is `$CLAUDE_CODE_OAUTH_TOKEN`, a
long-lived `sk-ant-oat0` credential, and that environment variable is the only
source. The OAuth path also requires the system prompt to open with the Claude
Code identity line — that line is the 26-token floor, and it is not optional.

Two credential sources are deliberately **not** read. `$HOME/.claude/.credentials.json`
still exists on this machine holding a token the server reports as revoked, so
reading it yields a silent 401. The macOS Keychain entry
(`security find-generic-password -s "Claude Code-credentials"`) is live but
expires within hours, which buys nothing the env var does not already give.

The variable is exported from `~/.zshrc`, which **only interactive shells
read**: `zsh -ic` sees it, `zsh -lc` does not, and neither does a
non-interactive tool shell. A panelist launched in the background is exactly
that kind of shell. Moving the export to `~/.zshenv` is what makes env-only
correct; that is a change to the operator's dotfiles, outside this repo. Until
then the variable's presence is an environment precondition, not an assumption
the code may make.

## Fail at the door, fall back inside it

Two different failures, two different answers.

**Missing credential** is a precondition, so it is checked once before the
panel launches, and it aborts with the reason named. A run that discovers this
per-call, mid-debate, reports a degraded consensus as if it were a real one.

**A non-2xx on a call that did go out** (rate limit, 5xx, a revoked token) falls
back to that seat's CLI invocation for that call and notes the fallback in the
run header. This is the one piece of error handling the design will not trade
away — a debate round quietly missing a panelist changes the consensus
arithmetic without telling anyone.

## Components

- `skills/tribunal-review/panel/direct.sh` — `direct_codex` and `direct_claude`,
  each taking a prompt file and an output file, each falling back to the CLI on
  failure. One file, two functions, no abstraction over "provider".
- `skills/tribunal-review/SKILL.md` — Step 5 gains the dispatch block that
  calls them; Step 3 is untouched.
- `skills/tribunal-review/references/panel-cli-notes.md` — records the Node/TLS
  403 finding and the stale-credentials-file trap, so neither is rediscovered.

## Testing

Contract tests in `tests/test_tribunal_transport.py`, stdlib `unittest`,
following `tests/test_review_chain.py`:

- `direct.sh` never hardcodes a token, an account id, or a home path
- a missing `$CLAUDE_CODE_OAUTH_TOKEN` aborts before launch, naming the variable
- both functions fall back to the CLI on a non-2xx (simulated with a stub)
- SKILL.md's Step 5 references the dispatch block rather than the Step 3 CLI
- the review round still names `-C "$REPO_OR_WORKTREE"` — a mutation test
  against the regression this design exists to avoid

Live calls are not part of the suite; they need credentials CI does not have.

## Out of scope

- Converting the review round (packing file contents into the prompt, or
  building read-only tools over the Responses API). Revisit only if the
  remaining single CLI call per seat proves too slow in practice.
- Cursor/Grok and Gemini. No direct path is measured for either, and Gemini is
  unlicensed on this machine.
- Retry or refresh of an expired token. Falling back to the CLI already covers
  it, and the CLI refreshes its own credentials.
- Keychain or `.credentials.json` as a second credential source. One source,
  checked once, with a named failure beats a chain that can silently pick the
  revoked one.
