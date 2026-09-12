# `herd` Skill Implementation Plan

> **For agentic workers:** execute with the user's `/execute-plan` skill as one
> linear thread (global rule: no subagent-driven development). Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a sixth cstack skill, `herd`, in which the lead model (Fable in Claude Code, Astra in Codex) chooses a transport per worker — native subagent, same-provider peer session, or herdr agent — and drives long-lived workers through an execution contract with a review gate.

**Architecture:** Pure prose skill plus one TOML roster and two reference files; no code runs at skill time except the `herdr` CLI and the host's native messaging. Tests are mutation-checked `unittest` assertions over the skill text, the same style as `tests/test_review_chain.py`, so a stale verb or a dropped rule fails CI.

**Tech Stack:** Markdown skill files, TOML (`tomllib`, Python 3.11+ stdlib), `python3 -m unittest`, herdr 0.9.0 CLI.

**Spec:** `docs/plans/2026-09-12-herdr-orchestration-design.md` — read it first; every task below cites the section it implements.

## Global Constraints

- Tests run with `python3 -m unittest discover -s tests` from the repo root and must stay green after every task.
- `tests/test_no_private_content.py` already scans the tree; nothing added may contain absolute home paths, account names, or private repo names. Use `~/projects/<repo>` or relative paths only.
- herdr verbs cited anywhere must exist in herdr 0.9.0: `agent list|get|read|send-keys|prompt|rename|focus|wait|attach|start|explain`, `pane split|run|wait-output|read|current|list|layout|move|close`, `workspace list|create`, `machine list|add`, `integration status|install`, `status`. Subcommands are hyphenated (`send-keys`, `wait-output`).
- Lessons from driving Cursor and Devin through herdr on 2026-09-12, all of which the files below must encode: (a) `agent start` fails with `agent_pane_busy` if the new pane's shell is not yet at its prompt, so wait for the prompt first; (b) every CLI injects its rules at startup, so an adopted long-lived worker keeps stale rules after a config change and must be restarted; (c) Devin blocks on a permission menu even for read-only `ls` unless started with `--permission-mode auto`; Cursor's equivalent is `--force`; (d) both answered inline without the alternate screen, so `agent read` was enough; (e) all four kinds now load the same rules and the c-memory index through the bootstrap-rendered `~/AGENTS.md`, verified in fresh sessions.
- Never auto-answer a `blocked` dialog in skill text unless the execution contract pre-approves that exact prompt (spec §Live prototype).
- Commit messages carry no AI attribution trailer (global rule).
- Worktrees live under `.worktrees/<branch>/` (global rule); this plan runs in `.worktrees/herdr-orchestration/`.

---

### Task 1: Roster file and its parser test

Implements spec §Roster.

**Files:**

- Create: `skills/herd/herd.example.toml`
- Test: `tests/test_herd.py`

**Interfaces:**

- Produces: `ROSTER = ROOT / "skills" / "herd" / "herd.example.toml"` and the `[[worker]]` schema `{name, kind, role, machine, args?}` that Task 4's SKILL.md describes verbatim. `args` is the list passed after `--` to `herdr agent start`; it is where each kind's approval mode lives.

- [ ] **Step 1: Write the failing test**

```python
"""herd's failure mode is a stale verb or a dropped rule, not a crash.

Every assertion is mutation-checked: it must fail on a tree where the
contract it protects has been broken.
"""

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERD = ROOT / "skills" / "herd"
ROSTER = HERD / "herd.example.toml"

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")  # herdr live-agent name rule
KINDS = {
    "pi", "claude", "codex", "gemini", "cursor", "devin", "agy", "cline", "omp",
    "mastracode", "opencode", "copilot", "kimi", "kiro", "droid", "amp", "grok",
    "hermes", "kilo", "qodercli", "qwen", "maki", "muse",
}  # `herdr agent` help, 0.9.0


class TestRoster(unittest.TestCase):
    def setUp(self):
        self.doc = tomllib.loads(ROSTER.read_text())

    def test_workers_have_required_keys(self):
        for w in self.doc["worker"]:
            for key in ("name", "kind", "role", "machine"):
                self.assertIn(key, w, f"worker {w} lacks {key}")

    def test_names_are_valid_and_unique(self):
        names = [w["name"] for w in self.doc["worker"]]
        for n in names:
            self.assertRegex(n, NAME_RE)
        self.assertEqual(len(names), len(set(names)))

    def test_kinds_are_real_herdr_kinds(self):
        for w in self.doc["worker"]:
            self.assertIn(w["kind"], KINDS)

    def test_args_are_lists(self):
        for w in self.doc["worker"]:
            if "args" in w:
                self.assertIsInstance(w["args"], list, w["name"])

    def test_interactive_kinds_preapprove_reads(self):
        """Devin blocks on read-only `ls` without this; Cursor on any command."""
        flags = {"devin": "--permission-mode", "cursor": "--force"}
        for w in self.doc["worker"]:
            if w["kind"] in flags:
                self.assertIn(flags[w["kind"]], w.get("args", []), w["name"])

    def test_no_peer_whitelist(self):
        """Spec: peers are the whole ecosystem, discovered live, never listed."""
        self.assertNotIn("peer", self.doc)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_herd -v`
Expected: FAIL with `FileNotFoundError` on `ROSTER.read_text()`.

- [ ] **Step 3: Write the roster**

```toml
# herd.example.toml — herdr workers this repo's lead may drive.
# Copy to <repo>/herd.toml and edit. Peer sessions are NOT listed here:
# every live session under ~/projects is a peer, found with ListAgents.

[[worker]]
name = "reviewer"               # herdr live-agent name: [a-z][a-z0-9_-]{0,31}
kind = "cursor"                 # a kind from `herdr agent` help
role = "cross-lineage reviewer, read-only"
machine = "local"               # "local" or a label from `herdr machine list`
# passed after `--` to `herdr agent start`; --force = auto-approve commands
# (cursor-agent --help), otherwise the first shell command blocks the worker
args = ["--force", "--model", "cursor-grok-4.6-high"]

[[worker]]
name = "implementer"
kind = "devin"
role = "scoped implementation with tests, one plan task per dispatch"
machine = "local"
# "auto" auto-approves read-only tools only (devin --help); edits still block
# and are answered under the execution contract
args = ["--permission-mode", "auto"]

[[worker]]
name = "bench"
kind = "codex"
role = "run benchmarks on the remote box, report numbers only"
machine = "gpu-box"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_herd -v`
Expected: 6 tests PASS.

- [ ] **Step 5: Mutation check, then commit**

Temporarily change `kind = "devin"` to `kind = "swe2"`; run the test; expect `test_kinds_are_real_herdr_kinds` to FAIL. Revert. Then delete the devin `args` line; expect `test_interactive_kinds_preapprove_reads` to FAIL. Revert.

```bash
git add skills/herd/herd.example.toml tests/test_herd.py
git commit -m "herd: example roster and parser test"
```

---

### Task 2: herdr CLI reference, pinned to 0.9.0

Implements spec §What herdr gives us and §Skill flow steps 2, 4, 5.

**Files:**

- Create: `skills/herd/references/herdr-cli.md`
- Modify: `tests/test_herd.py` (append)

**Interfaces:**

- Produces: the verb list `HERDR_VERBS` that Task 4's test reuses to check SKILL.md.

- [ ] **Step 1: Append the failing test**

```python
CLI_REF = HERD / "references" / "herdr-cli.md"
HERDR_VERBS = {
    "agent list", "agent get", "agent read", "agent send-keys", "agent prompt",
    "agent rename", "agent wait", "agent start", "agent explain",
    "pane split", "pane run", "pane wait-output", "pane read", "pane layout", "pane close",
    "workspace list", "machine list", "integration status", "integration install",
    "status",
}
VERB_RE = re.compile(r"herdr ((?:agent|pane|workspace|machine|integration) [a-z-]+|status)\b")


def cited_verbs(text):
    return set(VERB_RE.findall(text))


class TestCliReference(unittest.TestCase):
    def setUp(self):
        self.body = CLI_REF.read_text()

    def test_pinned_to_a_version(self):
        self.assertRegex(self.body, r"herdr 0\.9\.0")

    def test_every_cited_verb_exists(self):
        unknown = cited_verbs(self.body) - HERDR_VERBS
        self.assertEqual(unknown, set(), f"verbs not in herdr 0.9.0: {unknown}")

    def test_hyphenated_subcommands(self):
        for bad in ("send_keys", "wait_output", "sendkeys"):
            self.assertNotIn(bad, self.body)

    def test_reverse_channel_documented(self):
        """The worker prompts the lead's pane; herdr's own docs never say so."""
        self.assertIn("HERDR_PANE_ID", self.body)
        self.assertRegex(self.body, r"agent prompt \S*\$?\{?LEAD", )

    def test_waits_for_shell_prompt_before_start(self):
        self.assertIn("agent_pane_busy", self.body)
        self.assertLess(self.body.index("pane wait-output"), self.body.index("agent start implementer"))

    def test_restart_after_rule_change(self):
        self.assertIn("inject their rules at startup", self.body)

    def test_blocked_is_not_auto_answered(self):
        blocked = self.body[self.body.index("## blocked"):]
        self.assertNotIn("send-keys reviewer y", blocked)
        self.assertIn("ask the user", blocked)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_herd.TestCliReference -v`
Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Write the reference**

````markdown
# herdr CLI for `herd` — verified against herdr 0.9.0 on 2026-09-12

The installed binary is the authority. Re-run `herdr agent` and `herdr pane`
(bare group, no subcommand) after any `herdr update` and re-verify this file.
Subcommands are hyphenated: `send-keys`, `wait-output`. Never `send_keys`.

## Gate

```bash
test "${HERDR_ENV:-}" = 1 || { echo "not inside herdr"; exit 1; }
herdr status | grep -q 'endpoint_compatible: yes'
```
````

## Discover

```bash
herdr agent list                       # JSON: .result.agents[] {agent, agent_status, pane_id, cwd}
herdr agent get <name|pane>            # one agent
herdr agent explain <name|pane>        # why herdr thinks it is in that state
herdr integration status               # which kinds report lifecycle natively
herdr machine list --json              # saved SSH profiles; empty is normal
```

States: `idle` | `working` | `blocked` | `done` | `unknown`. `idle` and
`done` both accept input. `unknown` proves nothing.

## Adopt or start

Adopt an idle agent that already exists (keeps its context):

```bash
herdr agent rename w3:p2 reviewer
```

Start a missing one in a sibling pane, keeping the user's focus and cwd. The
new shell needs a moment to reach its prompt; `agent start` on a pane that is
not yet an available shell fails with `agent_pane_busy`, so wait for the
prompt first. Native flags from the roster's `args` go after `--`:

```bash
P=$(herdr pane split --current --direction right --cwd "$PWD" --no-focus | jq -r .result.pane.pane_id)
herdr pane wait-output "$P" --regex '[$%❯>] ?$' --timeout 15000
herdr agent start implementer --kind devin --pane "$P" --timeout 60000 -- --permission-mode auto
herdr agent wait implementer --until idle --timeout 60000
```

All CLIs inject their rules at startup. After a bootstrap or rules change,
an adopted worker is running on the old rules; restart it (close its pane
if you created it, or ask the user) rather than assuming it caught up.

Remote workers: run the same commands through `herdr --remote <machine>`;
IDs and names are per server, so rediscover them there.

## Dispatch and wait

```bash
herdr agent prompt implementer "$(cat "$SP/assign-implementer.md")" --wait --timeout 1800000 &
```

`--wait` returns on the first settled `idle`/`done`/`blocked`. It returns
`agent_prompt_stalled` if no `working` activity is seen within five seconds
of submission; that does not prove the prompt was lost. Inspect before
resending.

## Collect

```bash
herdr agent read implementer --source recent-unwrapped --lines 200
```

If more `--lines` reveals nothing (alternate screen), ask the worker to write
its full reply to a file under `$SP/` and answer with the path only, then
read the file. Fallback only; never request file output up front.

## Reverse channel (worker → lead)

Every managed pane has `$HERDR_PANE_ID`. Put the lead's id in the assignment
as `LEAD_PANE`, and the worker reports without being polled:

```bash
herdr agent prompt $LEAD_PANE "herd-report implementer task 3: commit abc123, evidence docs/evidence/t3.md, no deviations"
```

The lead sees it as an ordinary prompt in its own pane. Use it for
per-task reports under the execution contract.

## blocked

`agent prompt` refuses with `agent_blocked` while a dialog is open. Then:

```bash
herdr agent get implementer
herdr agent read implementer --source recent-unwrapped --lines 80
```

Show the dialog to the user and ask the user what to answer. Only when the
execution contract pre-approves that exact prompt may the lead answer it
with `herdr agent send-keys implementer <key>`. Devin's menus are numbered
(`1` = approve once), so a pre-approved answer is `send-keys implementer 1 enter`.
Prefer starting the worker with the roster's approval flag so read-only
commands never block at all.

## Teardown

```bash
herdr pane close <pane you created>
```

Only panes this skill created. Adopted workers stay.

## Safety (from herdr's own skill file, verbatim in spirit)

- `--no-focus` for background work; `--current` or explicit ids, never the
  focused pane.
- Never close panes, tabs, or workspaces you did not create.
- Never `herdr server stop` from a live session.
- A timeout does not prove non-delivery; do not blindly resend.

````

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_herd -v`
Expected: all PASS.

- [ ] **Step 5: Mutation check, then commit**

Change `send-keys` to `send_keys` once in the file; expect `test_hyphenated_subcommands` and `test_every_cited_verb_exists` to FAIL. Revert.

```bash
git add skills/herd/references/herdr-cli.md tests/test_herd.py
git commit -m "herd: pinned herdr CLI reference with reverse channel"
````

---

### Task 3: Execution contract template

Implements spec §Live prototype (contract + gate) and §Skill flow step 4 reply format.

**Files:**

- Create: `skills/herd/references/execution-contract.md`
- Modify: `tests/test_herd.py` (append)

**Interfaces:**

- Produces: the literal report line format `herd-report <worker> task <n>: commit <sha>, evidence <path>, deviations: <text|none>` that Task 4's SKILL.md tells the lead to parse.

- [ ] **Step 1: Append the failing test**

```python
CONTRACT = HERD / "references" / "execution-contract.md"
REPORT_LINE = "herd-report <worker> task <n>: commit <sha>, evidence <path>, deviations: <text|none>"


class TestContract(unittest.TestCase):
    def setUp(self):
        self.body = CONTRACT.read_text()

    def test_review_gate_rule_present(self):
        self.assertIn("Stop after every task", self.body)
        self.assertIn("Do not start the next task until", self.body)

    def test_report_format_is_exact(self):
        self.assertIn(REPORT_LINE, self.body)

    def test_rejected_work_fixed_on_top(self):
        self.assertIn("fix on top", self.body)
        self.assertIn("never rewrite", self.body)

    def test_lead_pane_slot(self):
        self.assertIn("LEAD_PANE", self.body)

    def test_preapproved_prompts_slot(self):
        self.assertIn("<pre-approved prompts", self.body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_herd.TestContract -v`
Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Write the template**

````markdown
# Execution contract for a `herd` worker

Paste this block, with the `<slots>` filled, at the top of the plan or
assignment the worker receives. Lifted from the livewire notify-rewrite
plan of 2026-09-12, generalized.

```text
## Execution contract — read before Task 0

You are worker `<name>` (kind `<kind>`), working in `<worktree path>`.
The lead is herdr pane `LEAD_PANE=<pane id>`.

1. Scope. Implement only the tasks in this plan, in order. Anything the
   plan does not name is out of scope; report it, do not do it.
2. Files. You own: <globs>. You never write: <globs, e.g. data lake,
   ledgers, production config>.
3. Environment. Commands run only in <allowed dirs>; temp files under
   <temp dir>. No network calls except <list|none>.
4. Evidence. Every task leaves `<evidence dir>/t<n>.md` with the exact
   commands run, exit codes, and pasted output the reviewer can re-run.
5. Commits. One commit per task, message `task <n>: <plan title>`. No
   attribution trailers.
6. Review gate. Stop after every task. Report with exactly one line:
   herd-report <worker> task <n>: commit <sha>, evidence <path>, deviations: <text|none>
   sent as: herdr agent prompt $LEAD_PANE "<that line>"
   Do not start the next task until the lead replies `herd-continue <n+1>`.
7. Rejections. If the lead replies `herd-reject <n>: <reason>`, fix on top
   with a new commit and report again; never rewrite or amend the rejected
   commit.
8. Blocked. You were started with read-only commands pre-approved. For any
   other permission prompt, stop and wait; the lead answers only prompts
   listed here: <pre-approved prompts, e.g. "edit files under src/">, and
   everything else goes to the user.
9. Deviations. Any step you could not do as written is a deviation. Name it
   in the report line; do not silently substitute.
```
````

Reviewer checklist (the lead runs this on every `herd-report`):

- commit maps to the plan task, nothing more
- evidence file commands are real and re-runnable; re-run one
- forbidden paths untouched (`git show --stat <sha>`)
- deviations either accepted in the reply or the task is rejected

````

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_herd -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/herd/references/execution-contract.md tests/test_herd.py
git commit -m "herd: execution contract template with review gate"
````

---

### Task 4: `SKILL.md` — transport decision and flow

Implements spec §Proposal (transport table, decision rule), §Skill flow, §Worktree discipline, §Ladder.

**Files:**

- Create: `skills/herd/SKILL.md`
- Modify: `tests/test_herd.py` (append)

**Interfaces:**

- Consumes: `HERDR_VERBS`, `cited_verbs` (Task 2), `REPORT_LINE` (Task 3), roster schema (Task 1).

- [ ] **Step 1: Append the failing test**

```python
SKILL = HERD / "SKILL.md"


class TestSkill(unittest.TestCase):
    def setUp(self):
        self.body = SKILL.read_text()

    def test_frontmatter(self):
        self.assertTrue(self.body.startswith("---\nname: herd\n"))

    def test_three_transports_in_decision_order(self):
        sec = self.body[self.body.index("## 2. Choose a transport"):]
        sec = sec[:sec.index("## 3.")]
        order = [sec.index(k) for k in ("peer session", "herdr agent", "native subagent")]
        self.assertEqual(order, sorted(order), "decision order is peer → herdr → native")

    def test_gate_falls_back_to_orchestrate(self):
        self.assertIn('test "${HERDR_ENV:-}" = 1', self.body)
        self.assertIn("`orchestrate`", self.body)

    def test_cites_only_real_herdr_verbs(self):
        unknown = cited_verbs(self.body) - HERDR_VERBS
        self.assertEqual(unknown, set())

    def test_uses_contract_report_line(self):
        self.assertIn("herd-report", self.body)
        self.assertIn("herd-continue", self.body)
        self.assertIn("herd-reject", self.body)

    def test_never_messages_working_session(self):
        self.assertIn("never message a session whose status is `working`", self.body)

    def test_blocked_surfaced_not_answered(self):
        self.assertIn("show the user the dialog", self.body)
        self.assertNotIn("send-keys reviewer y", self.body)

    def test_roster_args_and_restart_rule(self):
        self.assertIn("`args`", self.body)
        self.assertIn("restart", self.body)

    def test_same_setup_precondition(self):
        self.assertIn("same rules, skills, and memory", self.body)

    def test_links_orchestrate_team_design(self):
        self.assertIn("orchestrate/SKILL.md", self.body)

    def test_under_250_lines(self):
        self.assertLessEqual(self.body.count("\n"), 250)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_herd.TestSkill -v`
Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Write the skill**

````markdown
---
name: herd
description: Lead-chosen transport for delegated work — native subagent, same-provider peer session, or a herdr agent of any model on any machine — driven through an execution contract with a per-task review gate. Use when a task needs long-lived workers, another repo's live session, or a different model lineage; use `orchestrate` for single-harness native teams.
---

# Herd

`$herd <task or approved plan>`

The lead is whoever is running: Fable in Claude Code, Astra in Codex. The
lead designs the team, picks a transport per worker, dispatches, reviews, and
integrates. The lead never writes code itself.

## 1. Gate

```bash
test "${HERDR_ENV:-}" = 1 && herdr status | grep -q 'endpoint_compatible: yes'
```
````

If that fails, herdr workers are unavailable. Say so in one line and continue
with the other two transports; if the task needed a different model or
machine, stop and report. `orchestrate` remains the skill for a purely
native team.

## 2. Choose a transport

Design roles first, exactly as `skills/orchestrate/SKILL.md` §2: one compact
assignment table, roles invented from this task's deliverables. Then place
each role, in this order:

| Transport                                   | Primitive                                | Context                                            | Pick it when                                                                                                                                                                                                 |
| ------------------------------------------- | ---------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **peer session** (same provider)            | `ListAgents` → `SendMessage`             | independent, persists across turns and compactions | the answer or the change belongs to a repo that has a live session. Ask the session named after that repo instead of re-reading its code. Every session under `~/projects` is a peer; there is no whitelist. |
| **herdr agent** (any provider, any machine) | `herdr agent …`                          | independent, persistent, different model lineage   | the role needs eyes or hands from another model (Grok, Devin, Codex, …), a remote box, or a worker that keeps state across dispatches                                                                        |
| **native subagent**                         | Agent tool / `collaboration.spawn_agent` | disposable                                         | bounded labor whose result matters once: search, bulk read, extraction, mechanical edit                                                                                                                      |

Rules that hold across all three:

- `ListAgents` first; never message a session whose status is `working`.
- One bounded assignment per worker: goal, worktree path, file ownership,
  acceptance check, and the reply format from
  `references/execution-contract.md`. Workers do not delegate further.
- Workers that write code get a worktree under `.worktrees/<branch>/`
  (`git worktree add`), and the herdr pane's `--cwd` points at it.

## 3. Discover and adopt herdr workers

Precondition: every worker kind runs on the same rules, skills, and memory
as the lead. That is the bootstrap's job (rendered `~/AGENTS.md`, shared
`~/.agents/skills`, c-memory index), not this skill's; when in doubt, ask a
fresh worker which instruction files it loaded before trusting it.

Read `herd.toml` in the repo root (schema and example in `herd.example.toml`:
`[[worker]]` with `name`, `kind`, `role`, `machine`, optional `args` — the
native flags passed after `--` at start, which is where each kind's
approval mode lives). Then:

```bash
herdr agent list
```

- A roster worker already live and `idle`: adopt it by name
  (`herdr agent rename <pane> <name>`). Its context is the point; keep it.
- Missing: split a sibling pane with `--no-focus`, wait for the shell prompt,
  `herdr agent start … -- <args>`, wait for `idle`. Commands and JSON paths are
  in `references/herdr-cli.md`.
- Adopted after a rules or bootstrap change: the worker injected its rules at
  startup and is stale; restart it, or ask the user to.
- `machine` other than `local`: run the same through `herdr --remote <machine>`
  and rediscover ids there.
- Not in the roster: do not start it. Report the gap.

## 4. Dispatch under the execution contract

Fill `references/execution-contract.md` with the worker's name, worktree,
owned and forbidden paths, evidence dir, and `LEAD_PANE=$HERDR_PANE_ID`.
Put it at the top of the plan or assignment. Then, all workers in parallel:

- peer session: `SendMessage` with the assignment.
- herdr agent: `herdr agent prompt <name> "<assignment>" --wait --timeout <ms>`,
  backgrounded.
- native subagent: the host's spawn tool, `model` set explicitly.

## 5. Review gate

The worker reports one line per task:

```
herd-report <worker> task <n>: commit <sha>, evidence <path>, deviations: <text|none>
```

It arrives as a prompt in the lead's own pane (reverse channel) or as a peer
message. The lead runs the reviewer checklist in the contract and replies
with exactly one of:

- `herd-continue <n+1>` — accepted.
- `herd-reject <n>: <reason>` — worker fixes on top, never rewrites.

If `herdr agent prompt` returns `agent_blocked`, or a wait ends `blocked`:
`herdr agent get` and `herdr agent read`, then show the user the dialog and
ask what to answer. Answer only prompts the contract pre-approved.

## 6. Integrate and accept

Integration, cross-check, and final acceptance happen in the lead's context
with evidence, never on a worker's say-so. Cross-model review still goes
through `/tribunal-review`; `herd` does not replace it.

## 7. Teardown

Adopted workers stay. Panes the skill created are closed only when the user
asks. Never close what you did not create; never stop the herdr server.

## Non-goals (v1)

No daemon, no message bus, no herdr plugin, no auto-answered dialogs, no
cost tracking, no reuse of herdr seats inside `tribunal-review`.

````

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_herd -v`
Expected: all PASS.

- [ ] **Step 5: Mutation check, then commit**

Swap the peer-session and native-subagent rows in the table; expect `test_three_transports_in_decision_order` to FAIL. Revert.

```bash
git add skills/herd/SKILL.md tests/test_herd.py
git commit -m "herd: skill with transport decision, gate, and contract flow"
````

---

### Task 5: Register the sixth skill

Implements spec §Deliverables rows 5 and 6.

**Files:**

- Modify: `README.md:17-30` (quickstart table, "five skills" sentence) and the `## The five skills` heading and the `skills/` line near `README.md:243`
- Modify: `.claude-plugin/plugin.json` description, `.codex-plugin/plugin.json` description
- Modify: `rules/AGENTS.md:31-35` and `rules/CLAUDE.md:80` (one added sentence each)
- Modify: `tests/test_herd.py` (append)

- [ ] **Step 1: Append the failing test**

```python
README = ROOT / "README.md"
MANIFESTS = [ROOT / ".claude-plugin" / "plugin.json", ROOT / ".codex-plugin" / "plugin.json"]
RULES = [ROOT / "rules" / "AGENTS.md", ROOT / "rules" / "CLAUDE.md"]


class TestRegistration(unittest.TestCase):
    def test_readme_lists_six_skills(self):
        body = README.read_text()
        self.assertIn("`$herd <task>`", body)
        self.assertNotIn("five skills", body)
        self.assertIn("six skills", body)

    def test_manifests_name_herd(self):
        for m in MANIFESTS:
            self.assertIn("herd", m.read_text(), m.name)

    def test_rules_route_to_herd(self):
        for r in RULES:
            self.assertIn("`herd`", r.read_text(), r.name)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_herd.TestRegistration -v`
Expected: 3 FAIL.

- [ ] **Step 3: Edit README**

Add to the quickstart table after the `$orchestrate` row:

```markdown
| drive long-lived workers across sessions, models, and machines | `$herd <task>` |
```

Replace every `five skills` with `six skills` (`grep -n 'five' README.md` shows the spots, including the badge `skills-5` → `skills-6`). Add a section after `### orchestrate`:

````markdown
### `herd`

```text
$herd <task or approved plan>
```
````

The lead picks a transport per worker: a same-provider peer session for
work that belongs to another live repo, a herdr agent for another model or
machine, a native subagent for disposable labor. Persistent workers run
under an execution contract with a per-task review gate. Requires
[herdr](https://herdr.dev) for the herdr transport; the other two work
without it.

````

Add `herd` to the `skills/` line near line 243.

- [ ] **Step 4: Edit manifests**

`.claude-plugin/plugin.json` description → `"Review, execution, and status skills, plus native Astra orchestration and herdr-backed cross-model herding where supported: orchestrate, herd, execute-plan, review-cycle, tribunal-review, whatup, shared hooks and commands."`

`.codex-plugin/plugin.json` description → `"Agent orchestration, herding, review, execution, and status skills: orchestrate, herd, execute-plan, review-cycle, tribunal-review, whatup."`

- [ ] **Step 5: Edit rules**

`rules/AGENTS.md`, after the `orchestrate` bullet ending "continue locally and disclose it.":

```markdown
- Use `herd` instead when a worker must outlive one task, live in another
  repo's session, or run on another model or machine; it adds the transport
  choice and a per-task review gate on top of `orchestrate`'s team design.
````

`rules/CLAUDE.md` line 80, append one sentence to the Opus/Sonnet bullet before "A subagent never delegates further":

```markdown
`herd` is the cross-session, cross-model, cross-machine variant: the running lead (Fable or Astra) picks peer session, herdr agent, or native subagent per worker.
```

- [ ] **Step 6: Run the whole suite**

Run: `python3 -m unittest discover -s tests`
Expected: OK. `test_no_private_content` must still pass; if it flags a path, replace it with a relative one.

- [ ] **Step 7: Commit**

```bash
git add README.md .claude-plugin/plugin.json .codex-plugin/plugin.json rules/AGENTS.md rules/CLAUDE.md tests/test_herd.py
git commit -m "herd: register sixth skill in README, manifests, and rules"
```

---

### Task 6: Live validation against the idle cursor pane

Implements spec §First validation. Manual, evidence recorded; nothing automated hits herdr in CI. Already observed on 2026-09-12 and to be written into the evidence file as prior evidence: fresh `cursor` and `devin` agents started via `pane split` + `agent start`, answered a diagnostic prompt inline (no alternate screen), and `agent read` captured the full reply; `devin` without `--permission-mode auto` blocked on a read-only `ls` with a numbered menu and was released with `send-keys 1 enter`. Untested so far: the reverse channel (step 3).

**Files:**

- Create: `docs/evidence/2026-09-12-herd-roundtrip.md`

- [ ] **Step 1: Confirm the target is idle and not owned by another task**

Run: `herdr agent get w3:p2` and `herdr agent list`
Expected: `w3:p2` is `cursor`, `agent_status` is `idle`, cwd is `~/projects/cstack`. If it is `working`, stop; do not interrupt.

- [ ] **Step 2: Adopt and round-trip**

```bash
herdr agent rename w3:p2 reviewer
herdr agent prompt reviewer "Reply with exactly one line: herd-report reviewer task 0: commit none, evidence none, deviations: none" --wait --timeout 120000
herdr agent read reviewer --source recent-unwrapped --lines 40
```

Expected: the read output contains the `herd-report reviewer task 0` line.

- [ ] **Step 3: Reverse channel**

```bash
herdr agent prompt reviewer "Run this shell command and nothing else: herdr agent prompt $HERDR_PANE_ID 'herd-report reviewer task 0: reverse ok'" --wait --timeout 120000
```

Expected: the lead's own pane receives `herd-report reviewer task 0: reverse ok` as a prompt.

- [ ] **Step 4: Record evidence**

Write `docs/evidence/2026-09-12-herd-roundtrip.md` with the three commands, their exit codes, and the pasted `agent read` output. State plainly which of steps 2 and 3 passed. If step 3 failed (cursor lacks `HERDR_ENV`, or no herdr in its PATH), record that and change the SKILL.md sentence "It arrives as a prompt in the lead's own pane (reverse channel) or as a peer message" to say the lead polls with `herdr agent wait` for that kind; keep tests green.

- [ ] **Step 5: Commit**

```bash
git add docs/evidence/2026-09-12-herd-roundtrip.md skills/herd/SKILL.md
git commit -m "herd: live round-trip evidence against herdr cursor pane"
```

---

### Task 7: Deliver

- [ ] **Step 1: Full suite and line count**

Run: `python3 -m unittest discover -s tests && wc -l skills/herd/SKILL.md`
Expected: OK; SKILL.md ≤ 250 lines.

- [ ] **Step 2: Push and open the PR**

```bash
git push -u origin herdr-orchestration
gh pr create --title "herd: lead-chosen transport for cross-session, cross-model, cross-machine work" --body-file docs/plans/2026-09-12-herdr-orchestration-design.md
```

Wait for CI green before merging (global rule). Do not merge without the user's word.

---

## Self-review

- **Spec coverage:** roster → T1; herdr verbs, reverse channel, blocked → T2; contract + gate → T3; transport table, decision order, gate fallback, worktree rule, non-goals → T4; README, manifests, rules → T5; first validation and devin/cursor open question → T6. Design doc travels in the PR body (T7). Spec row "3b contract template" → T3. Spec open question 2 (devin settle) is answered by the live prototype and needs no task; roster in-repo and tribunal untouched are decided in T4's non-goals.
- **Placeholders:** none; every file's full content is in its task.
- **Type consistency:** `HERDR_VERBS`, `cited_verbs`, `REPORT_LINE`, `HERD`, `ROOT` defined in T1/T2/T3 and reused unchanged in T4/T5. Report vocabulary `herd-report` / `herd-continue` / `herd-reject` identical in T3, T4, T6.
