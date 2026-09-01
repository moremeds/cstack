# Public Config Single Source Design

## Goal

Make `cstack` the only source of public global rules, hooks, commands, and shared
skills, so running the machine bootstrap cannot restore stale copies.

## Ownership boundary

`cstack` owns publishable configuration:

- `rules/CLAUDE.md` and `rules/AGENTS.md`
- `hooks/*.sh`
- `commands/*.md`
- `skills/*`
- their public contract tests and documentation

The private bootstrap repository owns machine- and account-specific state:

- the rendered settings template
- plugin inventory
- private skills and commands
- memory and machine provisioning metadata

It may link public files from `cstack`, but it must not contain copies of them.

## Bootstrap flow

The private bootstrap resolves a configurable `CSTACK_REPO`, defaulting to
`$HOME/projects/cstack`. It fails before changing live configuration when the
repository is absent. It then links public rules, hooks, commands, and skills
directly from that checkout. Private commands and skills continue to use their
existing private sources.

Running bootstrap repeatedly must preserve the same resolved targets. Existing
foreign symlink targets continue to be recorded by the current recovery logic
before retargeting.

## Drift prevention

The private repository deletes its duplicate public rules, hooks, reference, and
command. Contract tests enforce both sides of the boundary:

1. public copies cannot reappear in the private tree;
2. every public bootstrap surface must point at `CSTACK_REPO`;
3. shared skills must still fan out to both Codex and Claude;
4. the bootstrap remains syntactically valid.

Live verification, rather than a repository-only unit test, covers idempotence.

`cstack` keeps its existing public-content and review-chain tests. Its README
documents the complete install surface, including Codex rules and public
commands.

## Verification

- Run both repositories' unit-test suites.
- Run the bootstrap twice.
- Confirm the second run creates no new public-symlink recovery records. The
  existing rendered-settings backup on each run is private state and is not a
  public-link drift signal.
- Resolve every live public symlink and confirm it is under the `cstack`
  checkout.
- Compare every live public file with its source.
- Start a fresh Codex probe to confirm the global rule and shared-skill surfaces
  are discoverable after the cutover.

## Non-goals

- Moving rendered settings, plugin inventory, private skills, private commands,
  or memory into the public repository.
- Adding a second installer to `cstack`.
- Preloading skill prompt/reference files into every session.
