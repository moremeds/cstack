---
description: Read-only audit of local branches, worktrees, and PR state. Classifies each as fully-merged / unique-work / stale / current and produces an action table. No destructive ops without explicit confirmation.
allowed-tools: Bash, Read, TaskCreate, TaskUpdate, TaskList
---

## Purpose

You repeatedly ask "scan the local branches and commits, see if anything is missed" or "all merged?" or for the cleanup table showing which branches/worktrees are safe to delete. This skill produces that table consistently and **never deletes anything itself**.

## Argument (optional)

`/branch-audit [--include-remote]`

- No arg → local branches + worktrees only.
- `--include-remote` → also enumerate remote branches and flag stale ones (no commits in 30+ days, not the default branch).

## Workflow

Use an available tracker only when useful; missing tracking tools do not block the audit.

### Step 1 — Gather raw state

Refresh remote refs with `git fetch` first; report a failure or stale refs.
Then gather these independent reads in parallel:

- `git branch -vv` — local branches with upstream tracking.
- `git worktree list` — every checked-out worktree.
- `git for-each-ref --sort=-committerdate --format='%(refname:short)|%(committerdate:iso8601)|%(authorname)' refs/heads/` — last commit per local branch.
- `gh pr list --state all --limit 60 --json number,headRefName,state,mergedAt,url` — open and recently-closed PRs (skip if `gh` unavailable; note in report).

If `--include-remote`: also `git for-each-ref refs/remotes/origin/`.

### Step 2 — Classify each branch

For every local branch (and remote branch if `--include-remote`):

1. **Merge status vs default branch** (`main` here, but detect it via `git symbolic-ref refs/remotes/origin/HEAD`):
   - `git merge-base --is-ancestor <branch> origin/<default>` → exit 0 means fully merged.
   - Else: `git log origin/<default>..<branch> --oneline` to enumerate unique commits.
2. **PR state**: match by `headRefName` against the `gh pr list` output.
3. **Worktree binding**: is any worktree checked out on this branch?
4. **Recency**: days since last commit.

### Step 3 — Recommend an action per branch

Use this decision table:

| Merged? | Has PR? | PR state | Has worktree? | Recommended action |
|---|---|---|---|---|
| Yes | Yes | merged | No | **Safe to delete local + remote** |
| Yes | Yes | merged | Yes | Delete worktree first, then branch |
| Yes | No | — | No | Safe to delete local (probably squash-merged with different SHA — verify) |
| No | Yes | open | — | Keep — PR in flight |
| No | Yes | closed (not merged) | — | Investigate — closed without merge; preserve or delete? Ask user |
| No | No | — | — | **Has unique work** — list the commits, ask user before any cleanup |

For worktrees, additionally check:
- A deleted upstream branch does not prove local work is merged. Verify local
  commits and dirty state before recommending worktree removal.
- Does the worktree have uncommitted changes? → never recommend deletion; flag for user review.

### Step 4 — Render the report

```
## Branch Audit — <date>

Default branch: <main|master>
Local branches: N | Worktrees: M | Open PRs: K

### Safe to delete (fully merged, no unique work, no active worktree)
| Branch | Last commit | PR | Action |
|---|---|---|---|
| ... | ... | #NN | `git branch -d X && git push origin --delete X` |

### Has unique work — preserve or ask user
| Branch | Unique commits | Last commit | Notes |
|---|---|---|---|
| ... | 3 | ... | <list the subjects> |

### Active / in-flight (do not touch)
| Branch | PR | State | Worktree? |
|---|---|---|---|

### Worktrees
| Path | Branch | Dirty? | Recommendation |
|---|---|---|---|

### Anomalies
- e.g. "worktree at X points to deleted branch Y"
- e.g. "branch Z has no upstream configured; remote push state unverified"
```

### Step 5 — Offer cleanup

After presenting the table, ask the user which items they want to act on. **Do not execute any deletion automatically.** Per their standing rules:
- Never destructive without explicit consent.
- Always open a PR before merging to main — so if any "has unique work" branch needs landing, suggest opening a PR, not direct merge.

When the user confirms specific deletions, execute them branch-by-branch and report each. For each remote deletion, the command is `git push origin --delete <branch>` — confirm one more time if the branch is the default branch or starts with `release/`.

## Stopping condition

- Report rendered. Cleanup is separate and does not keep a read-only audit open.
- Or: user signals stop.

## Guardrails

- **Read-only by default.** No `git branch -d`, no `git push --delete`, no `git worktree remove` without the user picking that specific item.
- **Never delete a worktree with uncommitted or untracked changes** — could destroy in-progress work.
- **Never delete the default branch** (`main`/`master`) or `release/*`.
- **Verify squash-merge before deleting a "no PR" branch** — `git log origin/main --grep="<branch-subject>"` to confirm content landed.
- Respect the user's project conventions: this project's default is `main`, branch naming uses `feat/`, `fix/`, `chore/`, `misc/` prefixes (never `codex/`).
