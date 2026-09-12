# Herdr-backed cross-model orchestration — design

**Date:** 2026-09-12 · **Status:** draft for discussion · **Branch:** `herdr-orchestration`

## Problem

cstack already has two orchestration surfaces and both are boxed in:

| Surface | How workers run | Ceiling |
| --- | --- | --- |
| `orchestrate` (Astra lead) | host-native subagents (`collaboration.spawn_agent`, Agent tool) | one harness, one vendor, one machine; no Cursor/Devin/Grok as workers |
| `tribunal-review` | one-shot `codex exec` / `cursor-agent -p` / `gemini -p` subprocesses | stateless, read-only, fire-and-collect; no back-and-forth, no long-lived worker |

The user wants a third mode: a **mastermind** (Fable in Claude Code, or Astra in
Codex) that drives long-lived agents of any kind, on any machine, through one
control plane, and keeps the conversation going across turns.

## What herdr gives us (verified on this machine, herdr 0.9.0)

- Terminal multiplexer that *recognizes* coding agents in panes and exposes a
  socket API via the `herdr` CLI. Kinds include `claude codex cursor devin
  gemini grok copilot opencode …` (23 total).
- Lifecycle states per agent: `idle | working | blocked | done | unknown`.
- The control verbs a mastermind needs already exist:
  `agent start <name> --kind K --pane ID`, `agent prompt <name> "…" --wait`,
  `agent wait --until blocked`, `agent read --source recent-unwrapped`,
  `agent send-keys`, `pane split/run/wait-output`, `worktree …`.
- Remote: `herdr --remote <ssh>` and `herdr machine add`; IDs and names are
  scoped per server, so a remote worker is addressed by (machine, name).
- Ships its own skill file (`herdr --skill`) that gates on `HERDR_ENV=1` and
  says "use only when the user explicitly mentions Herdr". That is the right
  default for ad-hoc use, but wrong for a *mode* — we want an opt-in skill that
  turns herdr into the transport.
- Live right now: this session (`w3:p1`, claude) sits next to `w3:p2` cursor
  and `w3:p3` devin, all in `~/projects/cstack`; same trio in `w2` for livewire.
- Integrations (`herdr integration status`): claude, codex, cursor, pi, opencode
  installed; **devin not installed** — devin state comes from screen detection
  only (`agent explain w3:p3` → rule `welcome_prompt_footer`, state `idle`).
- Docs (herdr.dev/docs, fetched 2026-09-12): the documented coordinator
  pattern is exactly `workspace create → pane split → agent start → agent wait
  --until idle → agent prompt --wait → agent read`. Results flow back only by
  reading terminal output; there is no message bus. Remote = one server per
  machine, `herdr machine add <ssh-target>`; Linux/macOS only verified.
- Docs also describe a plugin system (`herdr-plugin.toml`: actions, event
  hooks, startup hooks, link handlers, unsandboxed) and an unreviewed
  marketplace. No pricing page found.

## Proposal: one skill, `herd` — the lead chooses the transport

Not a plugin, not a daemon, not a new repo. A sixth cstack skill whose only
new idea is a **transport decision**. The lead (Fable in Claude Code, Astra in
Codex) already knows how to design a team (`orchestrate` §2); `herd` adds the
rule for *where each worker lives*:

| Transport | Primitive | Context | Lifetime | Use when |
| --- | --- | --- | --- | --- |
| **native subagent** | Agent tool / `collaboration.spawn_agent` | fork or blank, thrown away | one task | bounded labor: search, bulk read, mechanical edit; result only matters once |
| **peer session** (same provider) | `ListAgents` + `SendMessage` to `argon-9e`, `livewire-2a`… | fully independent, **persists across turns and compactions** | as long as the session | the other repo's context is the point: helium↔argon contract, livewire↔apex API shape; "ask the session that owns that code" |
| **herdr agent** (any provider, any machine) | `herdr agent prompt/read/wait` | independent, persistent, **different model lineage** | as long as the pane | need Grok/Devin/Codex eyes or hands, or a remote box; long-lived reviewer/implementer that keeps state between dispatches |

Decision rule, in this order:

1. Is the answer already in another live session's head? → peer session.
   `ListAgents` first; the session named after the repo that owns the code is
   the one to ask, whichever repo that is. Re-read code only when no owning
   session is live and idle.
2. Does the work need a different model or a different machine? → herdr agent.
3. Otherwise → native subagent. Cheapest, no cleanup.

Both persistent transports (peer session, herdr agent) share the property the
user singled out: **completely independent context that stays warm**. The lead
treats them the same way — one bounded assignment, one fixed reply format,
integrate in its own context — and only the send/receive verbs differ.

```
$herd <task or approved plan>
```

- `orchestrate` stays as-is; `herd` links to its §2 for team design and adds
  the transport table. The lead never writes code itself.

### Ladder check (why not less)

1. *Just use herdr's own skill?* It forbids use unless the user says "herdr"
   every time and has no team-design or transport-choice half. Thin skill, not
   a new tool.
2. *Ship it as a herdr plugin?* A plugin adds actions/hooks *to herdr*; our
   logic runs *inside an agent* and only needs the CLI, which the docs call
   "the plugin API" anyway. No new capability, runs unsandboxed. Skip; revisit
   only for an event hook that pings the lead when a worker goes `blocked`.
3. *Extend `orchestrate` with a transport flag?* Its spawn section is entirely
   about native tool schemas; merging doubles its length. Separate skill,
   shared section by link.
4. *Peer sessions need nothing new.* `SendMessage` already works; the skill
   only writes down when to prefer it. Same reply-format contract as herdr
   workers so the lead's collect step is identical.

### Roster: the one new artifact

A per-project `herd.toml` declaring the herdr workers this project may drive.
Peer sessions are **not** enumerated: every live session under `~/projects` is
a peer, discovered at run time with `ListAgents`. The desk pairs (helium↔argon,
livewire↔apex) are examples, not a whitelist. Nothing else is persisted.

```toml
# herd.toml — who the mastermind may drive in this repo
[lead]
claude = "fable"          # lead when run from Claude Code
codex  = "gpt-6-astra"    # lead when run from Codex

[[worker]]
name = "reviewer"         # herdr agent name, [a-z][a-z0-9_-]{0,31}
kind = "cursor"           # herdr agent kind
model = "cursor-grok-4.6-high"
role = "cross-lineage reviewer, read-only"
machine = "local"

[[worker]]
name = "implementer"
kind = "devin"
role = "scoped implementation with tests"
machine = "local"

[[worker]]
name = "gpu-runner"
kind = "codex"
machine = "gpu-box"       # name from `herdr machine list`
role = "run benchmarks, report numbers"
```

Why a file and not the assignment table alone: the assignment table is per
task and lives in the conversation; the roster is per project and outlives
compaction. Ponytail: it is TOML because herdr's own config is TOML and every
runtime here can read it with stdlib (`tomllib` in Python 3.11+).

### Skill flow

1. **Gate.** `test "$HERDR_ENV" = 1` and `herdr status` compatible, else
   report and fall back to `orchestrate` (native) with a one-line reason.
2. **Discover, never assume.** `ListAgents` for peer sessions (idle ones only;
   never message a `working` session mid-task). `herdr agent list` → reconcile against
   `herd.toml`. Already-running idle agents are *adopted* by name (rename if
   needed). Missing ones are started: `pane split --current --no-focus` then
   `agent start <name> --kind <kind> --pane <id>`. Remote ones go through
   `herdr --remote <machine> agent …` with IDs rediscovered on that host.
3. **Design the team** exactly as `orchestrate` §2: one compact assignment
   table, roles invented from deliverables, model/effort per worker.
4. **Dispatch.** Per the transport table: `SendMessage` for peers, one
   `herdr agent prompt <name> "<assignment>" --wait --timeout N` per herdr
   worker, backgrounded, in parallel; Agent tool for native labor. Assignment text carries goal,
   worktree path, file ownership, acceptance check, and the fixed reply
   format: *changes, evidence, blockers, uncertainty*.
5. **Collect.** `agent wait` → `agent read --source recent-unwrapped`. If the
   agent used the alternate screen, follow herdr's documented fallback: ask
   the worker to write its answer to a file in the scratchpad and read that.
   `blocked` → `agent get` + `agent read`, show the user the dialog, never
   auto-approve.
6. **Integrate and accept** in the lead's own context. Verification stays
   evidence-based (`verification-before-completion`). Cross-model review still
   goes through `/tribunal-review` — `herd` does not replace it, but the
   reviewer seat can be the same persistent cursor agent instead of a fresh
   `cursor-agent -p` subprocess (later, not in v1).
7. **Teardown.** Leave adopted agents alone. Close only panes the skill
   created, and only when the user asks; herdr's safety rules apply verbatim.

### Worktree discipline

Workers that write code get their own worktree under `.worktrees/<branch>/`
(global rule). `herdr worktree` can create it, but v1 uses plain
`git worktree add` so the path convention stays ours; the pane's `--cwd` points
at it.

## Live prototype: livewire ↔ devin, 2026-09-12

The livewire session (`w2:p1`, Fable) is already doing this by hand and it is
the shape v1 should codify:

- The plan file carries an **execution contract** for the worker (rules 1–13
  of `livewire/docs/superpowers/plans/2026-09-12-notify-rewrite.md`), and rule
  13 is a **review gate**: the worker stops after every task, reports task id,
  commit SHA, evidence entries, and deviations; the lead reviews against the
  plan and the safety rules, replies through herdr, then releases the next
  task. Rejected work is fixed on top, never rewritten.
- **Reverse channel exists.** The worker addresses the lead the same way:
  `herdr agent prompt w2:p1 "<report>"`. So the lead need not poll; it can
  hand the worker its own pane id and wait. This is the piece herdr's docs
  never spell out and the skill must.
- The lead saved a memory note (`herdr-cross-agent-review.md`) with the
  blocked-dialog recipe: `pane read` then `pane send-keys y`. **v1 disagrees:**
  `blocked` is surfaced to the user, not auto-answered, unless the execution
  contract pre-approves specific prompts. Note also that memory calls the
  worker "Cursor swe2"; herdr classifies `w2:p3` as `devin` (SWE-2 Max). The
  roster fixes naming so notes stop drifting.
- Devin state is fine for this loop: it settles to `idle` after a turn (seen
  live), so open question 2 is mostly answered for the review-gate cadence.

So v1 = **contract + gate + two-way herdr prompts**, generalized from that
session and written down once instead of re-derived per repo.

## Deliverables (single PR)

| # | Item | Size |
| --- | --- | --- |
| 1 | `skills/herd/SKILL.md` — transport table + decision rule + flow, ≤ 250 lines, links to `orchestrate` §2 | new |
| 2 | `skills/herd/references/herdr-cli.md` — the verified verbs and JSON paths, copied from `herdr --skill` output on 0.9.0 with a version stamp | new |
| 3 | `skills/herd/herd.example.toml` | new |
| 3b | `skills/herd/references/execution-contract.md` — the rule template (worker stops per task, report format, review gate, safety rules slots, reverse-channel pane id) lifted from the livewire plan | new |
| 4 | `tests/test_herd.py` — parses the example roster, checks the SKILL.md quotes only verbs present in `herdr agent`/`herdr pane` help (mutation-style, matches existing tests) | new |
| 5 | `rules/…` one paragraph: when to pick `orchestrate` vs `herd` vs `tribunal-review` | edit |
| 6 | README: sixth skill row | edit |
| 7 | `docs/plans/2026-09-12-herdr-orchestration.md` — the step plan for `/execute-plan` | new |

Explicitly **not** in v1: a daemon, a message bus, a web UI, a Codex-side
`herdr` MCP, auto-answering `blocked` dialogs, cost tracking.

## Open questions for the user

1. Lead model choice is per runtime (Fable/Astra) — fixed in `herd.toml` or
   always "whoever is running"? Proposal: whoever is running; the `[lead]`
   block is documentation only and can be dropped.
2. Devin as a worker: recognized by screen detection only (no integration
   installed, and `herdr integration install devin` exists — run it first).
   Devin's turn model (cloud-executed) may not settle to `idle` the way
   claude/codex do. Needs one spike: `herdr agent prompt devin-cstack "echo ok" --wait --timeout 60000`.
3. Remote machines: none saved yet (`herdr machine list` is empty). v1 keeps
   the `machine` field in the roster but only exercises `local`.

## First validation (before writing the skill)

Drive the two idle agents already beside this session by hand:

```bash
herdr agent rename w3:p2 reviewer
herdr agent prompt reviewer "List the five skills in skills/ and reply in one line." --wait --timeout 120000
herdr agent read reviewer --source recent-unwrapped --lines 40
```

Same for `w3:p3` (devin). If both round-trips work, the skill is mostly
prose; if devin does not settle, its row in the roster gets a
`wait = "file"` fallback and that is the only branch in the skill.
