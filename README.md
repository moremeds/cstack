# cstack

An agent configuration that checks its own work.

Most shared agent configs are a list of rules and nothing else — nothing
notices when a rule is ignored. This one is four layers, and each layer exists
because the one above it cannot enforce itself:

```
rules/          what the agent is told          CLAUDE.md, AGENTS.md
   ↓ who enforces it?
hooks/          mechanical interception         exit 2 blocks the tool call
   ↓ who applies it to real output?
skills/         a multi-pass review chain       cross-model panel, per-pass fixes
   ↓ who keeps these honest?
tests/          contract tests, mutation-checked
```

Built for Claude Code and Codex together. Neither runtime reads the other's
skill directory, so anything meant for both lives in one place here and is
symlinked into both.

## Layers

### `rules/`

`CLAUDE.md` and `AGENTS.md` — the standing instructions. Written as rules with
their reasons attached, because a rule whose reason is missing gets rationalized
away the first time it is inconvenient.

Some sections are scoped to a domain (market-data work has its own
no-fabrication rules). Those say so in the section, and name no projects — fill
in your own.

### `hooks/`

Shell hooks that run before or after a tool call. `git-guard.sh` is the clearest
case: global rules say "never push straight to master" and "never add AI
attribution trailers to commits", and this hook exits 2 on either, feeding the
reason back to the model. A rule the agent merely reads is a suggestion; a rule
that returns exit 2 is a constraint.

Set `GIT_GUARD_PR_EXEMPT` (colon-separated repo paths) for repos whose
documented workflow really is direct-push. Unset by default — nothing is exempt.

### `skills/`

**Pending** — the review chain (`tribunal-review`, `review-cycle`,
`execute-plan`) lands here once its current round of edits is finished. Holding
the move rather than copying mid-flight, because two copies drift and the drift
is silent.

### `tests/`

Contract tests over the config itself. Two rules they follow:

1. **Every assertion is mutation-checked.** It must fail on a tree where the
   thing it protects is broken. Assertions that pass either way are the specific
   bug this suite was written after finding — four of them, in one review round,
   each with a docstring correctly describing a contract it did not actually
   check.
2. **`test_no_private_content.py` runs before anything is published.** This repo
   is public, and a private marker reaching a commit is unfixable: deleting the
   file later leaves the blob reachable in history.

```bash
python3 -m unittest discover -s tests
```

## Install

Not yet — the install path arrives with `skills/`.

## License

MIT. `rules/RTK.md` documents a third-party CLI and is included as
documentation only.
