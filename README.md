<div align="center">

# cstack

**C**laude Code · **C**odex · **C**ursor · **C**henxi

*One agent configuration shared across three runtimes,
plus the person who has to live with what they produce.*

![license](https://img.shields.io/badge/license-MIT-black)
![runtimes](https://img.shields.io/badge/runtimes-Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20Cursor-black)
![install](https://img.shields.io/badge/install-symlinks%2C%20not%20copies-black)
![tests](https://img.shields.io/badge/tests-mutation--checked-black)

</div>

---

## Why four layers

Most shared agent configs are a list of rules and nothing else — nothing notices
when a rule is ignored. This one is four layers, and each exists because the one
above it cannot enforce itself:

```
rules/     what the agent is told         CLAUDE.md, AGENTS.md
   ↓  who enforces it?
hooks/     mechanical interception        exit 2 blocks the tool call
   ↓  who applies it to real work?
skills/    portable multi-step workflows  the review chain, plus whatup
   ↓  who keeps these honest?
tests/     contract tests over all of it  mutation-checked
```

Claude Code and Codex do not read each other's skill directory, and a Claude
slash command is invisible to Codex entirely. So anything meant for more than one
runtime lives in one place here and is symlinked into each.

---

## `skills/`

The substance of this repo. Four skills, each a single Markdown file with no
runtime API — so the file Claude Code loads and the file Codex loads are the
same file, not two copies drifting apart.

```
approved plan ─▶ execute-plan ─▶ review-cycle ─▶ tribunal-review
                                    (as Pass 2)

lost the thread ─▶ whatup
```

The first three chain rightward. `whatup` calls nothing and nothing calls it —
it is the one you run when you stop trusting the narration.

### `tribunal-review` — cross-model panel

```
/tribunal-review [target] [quick|deep] [focus: …]
```

Two instances of the same model share the same blind spots, so a second opinion
from the same lineage is not a second opinion. Whoever invokes this orchestrates
*and* votes; the other CLIs review independently and findings merge by weighted
consensus.

| Seat | Weight |
| --- | --- |
| orchestrator | **1.0** |
| peer runtime | **1.0** |
| Cursor / Grok | **1.0** |
| Gemini | 0.5 |

Two reviewers agreeing clears consensus; one alone goes to debate and rebuttal.

> [!IMPORTANT]
> Every panelist is probed for liveness before use — `which` is not enough. An
> installed CLI can be logged out, unlicensed, or sandboxed away from its own
> credentials, and a silently missing seat turns a "tribunal" into a solo review
> that still reports a verdict.

### `review-cycle` — six passes, fixes applied between them

```
/review-cycle [quick] [target] [focus …]
```

Self-review → tribunal → adversarial → simplicity → cumulative re-read →
assumption check → confidence calibration. Each pass applies its own fixes and
re-runs the repo's own verification commands *before* the next pass starts, so
the expensive passes spend their attention on a clean artifact instead of
re-finding bugs you already knew about.

Ends in a **pass ledger** — one fixed row per pass, none of which may be omitted.

> Across 12 logged runs the verdict line appeared **12** times while the
> assumption check behind it appeared **6**. Nothing errored — the weak runs just
> dropped the section, and the verdict came out looking identical.

### `execute-plan` — approved plan → verified branch

```
/execute-plan <plan-path> [--full-cycle]
```

Worktree → straight-through implementation → milestone commits → evidence-based
verification, then a summary of what was actually verified rather than what was
written. No mid-flight questions: the plan was approved already, and stopping to
re-litigate it is how a straight line turns back into a negotiation.

### `whatup` — plain-language status

```
/whatup [PR N | a path | a phrase]
```

The question you actually ask when work feels off track: what is this for, what
is happening right now, what works, what failed and how badly, what breaks if we
stop here, what decision is waiting on you, where the branch and PR stand.
Answered in the language of the conversation, light on technical detail and
heavy on functional detail.

> [!IMPORTANT]
> Grounded in `git`, `gh`, and this session's test runs, with the evidence
> printed **beside each claim** — a drifted agent narrates drift-free progress
> from memory, and a grounding ritual it performs privately gets silently
> dropped. Read-only: it names the next step, it does not take it.

---

## `rules/`

`CLAUDE.md` and `AGENTS.md` — the standing instructions, written as rules with
their reasons attached. **A rule whose reason is missing gets rationalized away
the first time it is inconvenient.**

Sections scoped to a domain say so in the section and name no projects. Fill in
your own.

> [!NOTE]
> `RTK.md` documents a third-party CLI and is reference only — not installed, not
> imported by an `@` path; Codex gets the operative rule from `AGENTS.md`
> directly. Do not run `rtk init -g --codex` after installation: its generated
> `RTK.md` and `@` line are redundant, and Codex does not expand that line.

---

## `hooks/`

Rules the agent merely reads are suggestions. These return **exit 2**, which
blocks the tool call and feeds the reason back to the model.

| Hook | Does |
| --- | --- |
| `git-guard.sh` | blocks direct pushes to `master`/`main` and AI attribution trailers; warns on `git add -A` |
| `ci-green-before-merge.sh` | intercepts `gh pr merge`, blocks while any check is failing or pending |
| `format-on-write.sh` | formats by extension after every write; always exits 0, so a missing formatter never blocks an edit |
| `lint-on-edit.sh` | lints the edited file, capped at 10 lines so the model can actually react |
| `test-on-edit.sh` | runs the nearest project's tests — opt-in via a `.claude/test-on-edit` marker |
| `auto-commit.sh` | commits on stop — opt-in via a `.claude/auto-commit` marker |
| `log-commands.sh` | appends every Bash command to a timestamped log |
| `rtk-rewrite.sh` | routes commands through `rtk`, a token-saving CLI proxy, when installed |

`git-guard.sh` reads `GIT_GUARD_PR_EXEMPT` — colon-separated repo paths whose
documented workflow really is direct-push. Unset by default: nothing is exempt.

The two opt-in hooks stay silent until a project drops in its marker file.
**A hook that fires everywhere gets disabled everywhere.**

---

## `commands/`

Public slash commands that are safe to share across machines. Not a layer of the
chain above — just the thin entry points. Machine- and account-specific commands
stay in the private bootstrap repository.

---

## `tests/`

```bash
python3 -m unittest discover -s tests
```

Contract tests over the configuration itself, under two rules.

**Every assertion is mutation-checked** — it has to fail on a tree where the
thing it protects is broken. One review round found four assertions here whose
docstrings described a contract correctly and which passed anyway on a tree that
violated it:

```python
self.assertIn("tribunal-review", body)   # green with the call reverted
```

The word appeared elsewhere in the file. The test knew what it was for and
checked something else.

**`test_no_private_content.py` runs before anything is published.** A private
marker reaching a commit in a public repo is unfixable — deleting the file later
leaves the blob reachable in history, and a public repo is indexed within
minutes. It catches absolute home paths, bare IPs, email addresses, and SSH
remotes; add your own before publishing.

---

## Install

Clone, then link each public surface directly from this checkout:

| From | To |
| --- | --- |
| `rules/CLAUDE.md` | `~/.claude/CLAUDE.md` |
| `rules/AGENTS.md` | `~/.codex/AGENTS.md` |
| `hooks/*.sh` | `~/.claude/hooks/*.sh` |
| `commands/*.md` | `~/.claude/commands/*.md` |
| `skills/*` | `~/.claude/skills/*` **and** `~/.agents/skills/*` |

> [!WARNING]
> Use symlinks, not copies. Editing through a live path then writes back here, so
> there is no second public copy to keep in step. A machine-private bootstrap may
> create these links, but it must consume this checkout rather than vendor the
> files.

Machine-local and account-specific configuration (rendered settings, plugin
inventory, private skills and commands) belongs in a separate private repo. The
split is by what can be published, not by what is convenient.

---

## License

[MIT](LICENSE).
