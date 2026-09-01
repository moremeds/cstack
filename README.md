# cstack

**C**laude Code, **C**odex, **C**ursor, and **C**henxi.

One agent configuration shared across three runtimes, plus the person who has to
live with what they produce.

Most shared agent configs are a list of rules and nothing else — nothing notices
when a rule is ignored. This one is four layers, and each exists because the one
above it cannot enforce itself:

```
rules/     what the agent is told           CLAUDE.md, AGENTS.md
   ↓  who enforces it?
hooks/     mechanical interception          exit 2 blocks the tool call
   ↓  who applies it to real output?
commands/  public runtime entry points       shared operational commands
   ↓  who reviews their behavior?
skills/    a multi-pass review chain        cross-model panel, per-pass fixes
   ↓  who keeps these honest?
tests/     contract tests, mutation-checked
```

Claude Code and Codex do not read each other's skill directory, and a Claude
slash command is invisible to Codex entirely. So anything meant for more than one
runtime lives in one place here and is symlinked into each.

## `rules/`

`CLAUDE.md` and `AGENTS.md` — the standing instructions, written as rules with
their reasons attached. A rule whose reason is missing gets rationalized away the
first time it is inconvenient.

Sections scoped to a domain say so in the section and name no projects. Fill in
your own.

`RTK.md` documents a third-party CLI. Codex receives the operative rule directly
from `AGENTS.md`; the reference stays in this checkout and is not installed or
imported with an `@` path. Claude's rewrite hook works without loading it.

## `hooks/`

Rules the agent merely reads are suggestions. These return exit 2, which blocks
the tool call and feeds the reason back to the model.

| Hook                       | Does                                                                                                              |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `git-guard.sh`             | blocks direct pushes to `master`/`main`, blocks AI attribution trailers in commit messages, warns on `git add -A` |
| `ci-green-before-merge.sh` | intercepts `gh pr merge`, runs `gh pr checks` first, blocks while anything is failing or pending                  |
| `format-on-write.sh`       | formats by file extension after every write; always exits 0, so a missing formatter never blocks an edit          |
| `lint-on-edit.sh`          | lints the edited file, capped at 10 lines of output so the model can actually react to it                         |
| `test-on-edit.sh`          | runs the nearest project's tests; opt-in per project via a `.claude/test-on-edit` marker                          |
| `auto-commit.sh`           | commits on stop; opt-in per project via a `.claude/auto-commit` marker                                            |
| `log-commands.sh`          | appends every Bash command to a timestamped log                                                                   |
| `rtk-rewrite.sh`           | rewrites commands through `rtk`, a third-party token-saving CLI proxy, when it is installed                                  |

`git-guard.sh` reads `GIT_GUARD_PR_EXEMPT` — colon-separated repo paths whose
documented workflow really is direct-push. Unset by default: nothing is exempt.

The two opt-in hooks stay silent until a project drops in its marker file. A hook
that fires everywhere gets disabled everywhere.

## `commands/`

Public runtime commands that are safe to share across machines. Machine- or
account-specific commands stay in the private bootstrap repository.

## `skills/`

The review chain, three skills that call each other:

**`tribunal-review`** runs a cross-model panel. Whoever invokes it orchestrates
and also votes; the others review independently and findings merge by weighted
consensus.

| Seat          | Weight |
| ------------- | ------ |
| orchestrator  | 1.0    |
| peer runtime  | 1.0    |
| Cursor / Grok | 0.95   |
| Gemini        | 0.5    |

Two reviewers agreeing clears consensus; one alone goes to debate and rebuttal.
Every panelist is probed for liveness before use — `which` is not enough. An
installed CLI can be logged out, unlicensed, or sandboxed away from its own
credentials, and a silently missing seat turns a "tribunal" into a solo review
that still reports a verdict.

**`review-cycle`** wraps that in six passes and reports a **pass ledger**: one
fixed row per pass, which cannot be omitted. Across 12 logged runs the verdict
line appeared 12 times while the assumption check behind it appeared 6. Nothing
errored — the weak runs just omitted the section and looked identical to the
thorough ones.

## `tests/`

Contract tests over the configuration itself, following two rules.

**Every assertion is mutation-checked.** It must fail on a tree where the thing
it protects is broken. This is not a style preference — one review round found
four assertions here that each had a docstring correctly describing a contract,
and each passed on a tree where that contract was violated:

```python
self.assertIn("tribunal-review", body)   # green with the call reverted
```

The word appeared elsewhere in the file. The test knew what it was for and
checked something else.

**`test_no_private_content.py` runs before anything is published.** This repo is
public and a private marker reaching a commit is unfixable: deleting the file
later leaves the blob reachable in history, and a public repo is indexed within
minutes. Absolute home paths, bare IPs, email addresses, SSH remotes. Add your
own before publishing — employer, private orgs, internal hostnames.

```bash
python3 -m unittest discover -s tests
```

## Install

Clone, then link each public surface directly from this checkout:

- `rules/CLAUDE.md` → `~/.claude/CLAUDE.md`
- `rules/AGENTS.md` → `~/.codex/AGENTS.md`
- `hooks/*.sh` → `~/.claude/hooks/*.sh`
- `commands/*.md` → `~/.claude/commands/*.md`
- `skills/*` → both `~/.claude/skills/*` and `~/.agents/skills/*`

Use symlinks, not copies. Editing through a live path then writes back here, so
there is no second public copy to keep in step. A machine-private bootstrap may
create these links, but it must consume this checkout rather than vendor the
files.

Machine-local and account-specific configuration (rendered settings, plugin
inventory, private skills and commands) belongs in a separate private repo. The
split is by what can be published, not by what is convenient.

## License

MIT.
