<div align="center">

# cstack

**C**laude Code · **C**odex · **C**ursor · **C**henxi

**Four skills for finishing agent work without losing the plot.**

The plan was approved. The agent is busy. You still should not have to take
its word for it.

![license](https://img.shields.io/badge/license-MIT-black)
![runtimes](https://img.shields.io/badge/runtimes-Claude%20Code%20%C2%B7%20Codex-black)
![skills](https://img.shields.io/badge/skills-4-black)
![tests](https://img.shields.io/badge/tests-mutation--checked-black)

</div>

---

cstack is a small, opinionated workflow for four moments that keep happening
when you work with coding agents:

| The moment | Reach for |
| --- | --- |
| "The plan is approved. Please stop asking and finish it." | [`execute-plan`](#execute-plan--approved-plan--verified-branch) |
| "Do not just review this. Fix what you find and check it again." | [`review-cycle`](#review-cycle--review-that-changes-the-artifact) |
| "I do not want one model grading its own homework." | [`tribunal-review`](#tribunal-review--an-actual-second-opinion) |
| "Stop narrating. Tell me what is actually true right now." | [`whatup`](#whatup--when-you-no-longer-trust-the-status-update) |

That is the product: four portable `SKILL.md` files that work in Claude Code
and Codex. The rules, hooks, and tests elsewhere in this repository support
them; they are not a second product you have to adopt.

## Install in Claude Code

```text
/plugin marketplace add moremeds/cstack
/plugin install cstack@cstack
```

All four skills install together because they call one another. `review-cycle`
uses `tribunal-review`; `execute-plan --full-cycle` wraps execution with
`review-cycle` before and after the work.

Already in the middle of a messy session? Start with:

```text
/whatup
```

It is deliberately the least ambitious skill here. It changes nothing. It
checks the work and tells you where you actually are.

## How the four skills fit together

```text
approved plan ──▶ execute-plan ──▶ verified branch and evidence
                      │
                      └─ --full-cycle ─▶ review ─▶ execute ─▶ review + e2e

anything you wrote ─▶ review-cycle
                           │
                           └─ Pass 2 ─▶ tribunal-review

lost the thread ──────────────────────▶ whatup
```

Three skills form a delivery chain. `whatup` sits beside it and can be used at
any time, especially when the chain has been running long enough that the
progress report starts to sound smoother than the work itself.

## The skills

### `whatup` — when you no longer trust the status update

```text
/whatup [PR N | a path | a phrase]
```

Agents rarely announce that they have drifted. They keep moving and describe
the movement as progress. `whatup` is the interruption for that moment.

It rereads the goal, checks the branch, dirty files, recent commits, PR state,
and test evidence, then answers in the language of the conversation:

- what this work is for;
- what is happening now;
- what actually works and what failed;
- what breaks if you stop here;
- what decision is waiting on you.

Every claim carries its evidence beside it or is marked unverified. It also
checks earlier "done" and "passing" claims against the fresh state. If the
story changed, that mismatch is the first line of the readout, not a quiet
correction buried at the end.

`whatup` is read-only. It names the next step; it does not take it.

### `execute-plan` — approved plan → verified branch

```text
/execute-plan <plan-path> [--full-cycle]
```

Once a plan is approved, the agent should stop reopening settled questions and
execute the thing. `execute-plan` creates an isolated worktree, moves through
the plan in a straight line, commits at real milestones, runs the plan's checks,
and ends with a table of claims, evidence, and commands you can use to verify
the evidence yourself.

The bare skill handles execution. `--full-cycle` adds a review gate before any
implementation, reviews the finished cumulative diff, and runs the plan's real
end-to-end check when one exists.

It can still stop, but only for a real fork: a broken business assumption, a
scope change, or missing authority. "I wanted to check whether you still want
the plan you already approved" is not a fork.

### `review-cycle` — review that changes the artifact

```text
/review-cycle [quick] [target] [focus …]
```

A findings list is not a reviewed artifact. It is a list next to an unchanged
artifact.

`review-cycle` runs a fixed sequence of passes. The important part is what
happens between them: it applies the valid fixes and reruns the repository's
own verification before the next pass begins.

```text
self-review
  → cross-model tribunal
  → adversarial pass
  → simplicity pass
  → cumulative reread
  → assumption check
  → confidence calibration
```

The final report includes a fixed pass ledger. A skipped or unavailable step
must appear as skipped or unavailable; it cannot disappear while the verdict
still says `SHIP`.

This works on code, implementation plans, and prose. The questions change with
the artifact: a README is reviewed for what it makes readers believe, while a
plan is checked against the code it is about to change.

### `tribunal-review` — an actual second opinion

```text
/tribunal-review [target] [quick|deep] [focus: …]
```

Asking the same model twice often gives you the same blind spots twice.
`tribunal-review` lets the invoking agent orchestrate and vote while other
available model CLIs review the same artifact independently.

| Seat | Weight |
| --- | ---: |
| Orchestrator | **1.0** |
| Claude or Codex peer | **1.0** |
| Cursor / Grok | **1.0** |
| Gemini advisor | 0.5 |

Findings are merged by weighted agreement. A lone finding is contested, then
sent through debate and rebuttal instead of being accepted because one model
said it confidently.

Before the review starts, every seat is probed for a real response. An installed
CLI may be logged out, unlicensed, or unable to reach its credentials. Missing
reviewers are named in the verdict; a solo review is never presented as a
four-model tribunal.

The weights are a routing rule, not a scientific accuracy score. They represent
independent model lineages. cstack does not pretend they prove more than that.

## Why this exists

I built these skills after seeing the same failure in different forms: the
agent did plenty of work, the report sounded complete, and the evidence proved
something narrower than the sentence wrapped around it.

One measured session made the lesson hard to ignore. A 177-minute cross-model
review missed five false assumptions about the code. Running and reading the
relevant code exposed all five in roughly five minutes. The answer was not
"review even more." It was to give review and execution different jobs:

- review challenges judgment, consistency, and blind spots;
- execution falsifies claims about what the code actually does;
- status reports show the evidence instead of asking you to trust the narrator.

cstack does not make a bad premise true, and a green test does not prove the
parts of the system it never exercised. The skills are designed to keep those
limits visible.

## Inside the repository

```text
skills/    the product       execute-plan, review-cycle, tribunal-review, whatup
rules/     standing guidance maintainer defaults for Claude Code and Codex
hooks/     hard guardrails   block or rewrite selected tool calls
commands/  small entry points shared Claude Code commands
tests/     contract checks   keep the workflow and public boundary honest
```

The four skills have one source here. Claude Code and Codex discover them from
different directories, so a checkout-based setup links the same skill folders
into both `~/.claude/skills/` and `~/.agents/skills/`. Do not copy them and
create two versions that can drift.

The supporting hooks include Git safety, CI-before-merge, formatting, linting,
opt-in tests, opt-in auto-commit, command logging, and RTK command rewriting.
Some return exit 2 to block the tool call and feed the reason back to the agent.

The test suite is intentionally about contracts, not line coverage:

```bash
python3 -m unittest discover -s tests
```

Assertions are mutation-checked: a test must fail when the behavior it claims
to protect is broken. The publication guard also checks for private markers
before they enter a public Git history, where deleting them later would be too
late.

Machine-specific settings, credentials, plugin inventories, memories, and
private skills do not belong here. This repository is public because that
boundary is enforced, not because the private half of the setup does not exist.

## Install from a checkout

Clone the repository, then symlink the skill directories into the runtime roots
you use:

| Source | Claude Code | Codex and other Agent Skills runtimes |
| --- | --- | --- |
| `skills/<name>/` | `~/.claude/skills/<name>` | `~/.agents/skills/<name>` |

Link the folders; do not copy them. Editing through either live path then edits
the source in this checkout, leaving one place to review, test, and publish.

The `rules/`, `hooks/`, and `commands/` directories are the maintainer's setup
and are optional. The four skills do not require you to replace your own global
agent configuration.

## License

[MIT](LICENSE)
