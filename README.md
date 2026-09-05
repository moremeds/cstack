<div align="center">

# cstack

**C**laude Code · **C**odex · **C**ursor · **C**henxi

**Four portable skills for reviewing, executing, and understanding agent work.**

![license](https://img.shields.io/badge/license-MIT-black)
![runtimes](https://img.shields.io/badge/runtimes-Claude%20Code%20%C2%B7%20Codex-black)
![skills](https://img.shields.io/badge/skills-4-black)
![tests](https://img.shields.io/badge/tests-mutation--checked-black)

</div>

---

## Quickstart

| When you need to… | Use |
| --- | --- |
| find out what is actually happening | `/whatup` |
| execute an already-approved plan | `/execute-plan <plan-path>` |
| review, fix, and re-verify an artifact | `/review-cycle <target>` |
| get an independent cross-model review | `/tribunal-review <target>` |

cstack is a Claude Code and Codex skills plugin. The four skills install
together and share the same source files across runtimes.

## The four skills

### `whatup`

> **Plain-language status, grounded in evidence.**

```text
/whatup [PR N | a path | a phrase]
```

**Use it when:** the agent has been working for a while and you no longer trust
the narration enough to know what is done, what failed, or what happens if you
stop.

**What it does:** rereads the goal and checks the branch, dirty files, recent
commits, PR state, artifacts, and test evidence. It also compares earlier
"done" and "passing" claims with the fresh state.

**What you get:** one plain-language screen covering purpose, current state,
what works, what failed, what remains, and the decision waiting on you. Every
claim carries its evidence beside it or is marked unverified.

`whatup` is read-only. It names the next step; it does not take it.

#### Research behind `whatup`

The skill takes its premise from
["AI Agents Push Humans Out of the Loop"](https://arxiv.org/abs/2608.23642)
(Mitchell, Ghosh & Passi, 2026): **"current approaches to the development and
deployment of AI agent systems do not support effective human oversight – they
contribute to its degradation."**

The paper's audit mechanism checks an agent's narrative against the raw record
to find where they diverge. `whatup` turns that into a concrete rule: before it
writes the status, it checks earlier claims against what it just verified. A
mismatch becomes the opening line instead of a quietly corrected fact.

---

### `execute-plan`

> **An approved plan in; a verified branch out.**

```text
/execute-plan <plan-path> [--full-cycle]
```

**Use it when:** the plan is already written and approved. You want the agent to
stop reopening settled questions and carry it through.

**What it does:** creates an isolated worktree, executes in a straight line,
commits at meaningful milestones, runs the plan's checks, and verifies the
evidence before reporting completion.

**What you get:** a branch or PR plus a table of claims, evidence, and commands
you can use to re-verify each claim.

Add `--full-cycle` to review the plan before implementation, review the final
cumulative diff, and run the plan's real end-to-end check when one exists.

---

### `review-cycle`

> **Review that changes the artifact, not just comments beside it.**

```text
/review-cycle [quick] [target] [focus …]
```

**Use it when:** code, a plan, or prose is finished and needs a disciplined
review before it ships.

**What it does:** runs a fixed review sequence and applies valid fixes between
passes. After each apply step, it reruns the repository's own verification
before continuing.

```text
self-review → tribunal → adversarial → simplicity
            → cumulative reread → assumptions → acceptance
```

**What you get:** the improved artifact and a complete pass ledger. A skipped
or unavailable step remains visible; it cannot disappear while the verdict
still says `SHIP`.

Ordinary edits use self-review and relevant checks; invoke this cycle when
requested or warranted by impact and uncertainty, including high-risk single-file changes.
Completion follows acceptance evidence, not subjective confidence scores.

The review adapts to the target. Code is checked for defects, plans against the
repository they intend to change, and prose for false or misleading claims.

---

### `tribunal-review`

> **A second opinion from a different model lineage.**

```text
/tribunal-review [target] [quick|deep] [focus: …]
```

**Use it when:** one model reviewing its own work is not enough.

**What it does:** the invoking agent orchestrates and votes while other
available model CLIs review the same artifact independently. Findings are
merged by weighted agreement; contested findings go through debate and
rebuttal.

| Seat | Weight |
| --- | ---: |
| Orchestrator | **1.0** |
| Claude or Codex peer | **1.0** |
| Cursor / Grok | **1.0** |
| Gemini advisor | 0.5 |

**What you get:** one deduplicated verdict with consensus findings, contested
items, dismissed low-confidence claims, and the exact panel that answered.

Every seat is probed for a real response before use. An installed CLI may be
logged out, unlicensed, or unable to reach its credentials. Missing reviewers
are named; a solo review is never presented as a four-model tribunal.

The weights represent lineage independence, not measured accuracy.

## Workflow

```text
approved plan ──▶ execute-plan ──▶ verified branch / PR
                      │
                      └─ --full-cycle ─▶ review ─▶ execute ─▶ review + e2e

finished artifact ─▶ review-cycle
                          │
                          └─ Pass 2 ─▶ tribunal-review

lost the thread ─────────────────────▶ whatup
```

`execute-plan`, `review-cycle`, and `tribunal-review` form the delivery chain.
`whatup` is independent and read-only, so you can use it at any point.

## Install

### Claude Code plugin

```text
/plugin marketplace add moremeds/cstack
/plugin install cstack@cstack
```

This installs all four skills together, plus the shared Claude Code commands
and hooks.

### From a checkout

Clone the repository, then symlink each skill directory into the runtime roots
you use:

| Source | Claude Code | Codex and other Agent Skills runtimes |
| --- | --- | --- |
| `skills/<name>/` | `~/.claude/skills/<name>` | `~/.agents/skills/<name>` |

Use symlinks, not copies. Both runtimes then load the same `SKILL.md`, leaving
one source to review, test, and publish.

## Astra guidance audit

See [the official-guidance audit](docs/astra-guidance-audit.md) for the source
mapping, preserved safeguards, validation, and performance limits. These are
workflow changes, not a claim of measured model speedup.

The optional auto-commit hook now commits only explicitly staged work; it never
stages the workspace. Test-on-edit remains opt-in and is diagnostic, not acceptance
evidence. Hook checks are best-effort helpers, not a complete security boundary.

## What else is in the repo?

```text
skills/    the plugin       execute-plan, review-cycle, tribunal-review, whatup
rules/     standing rules   maintainer defaults for Claude Code and Codex
hooks/     hard guardrails  block or rewrite selected Claude Code tool calls
commands/  entry points     small shared Claude Code commands
tests/     contracts        mutation-checked workflow and publication guards
```

The skills are the product. Everything else supports the maintainer's own daily
setup and is optional. Machine-specific settings, credentials, memories, plugin
inventories, and private skills stay outside this public repository.

Run the contract suite with:

```bash
python3 -m unittest discover -s tests
```

Assertions are mutation-checked: each one must fail when the contract it claims
to protect is broken. The publication guard also catches private markers before
they enter public Git history.

## License

[MIT](LICENSE)
