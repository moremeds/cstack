# RTK single-source design

## Goal

Make RTK guidance active in fresh Codex sessions while preserving cstack as the
only public source. A generated local `RTK.md` or an `@` path in public rules is
an unnecessary second runtime surface and therefore drift.

## Chosen design

- `rules/AGENTS.md` states the RTK shell-prefix rule directly because Codex loads
  the `AGENTS.md` instruction chain and does not expand a bare `@path` line.
- `rules/RTK.md` remains reference material inside cstack; it is not installed
  into the Codex home because Codex does not load it.
- The private bootstrap remains unchanged. Its existing `AGENTS.md` symlink is
  the only Codex global-rules entry point.

## Rejected alternatives

- Keep the output of `rtk init -g --codex`: it creates a local copy and writes a
  machine-specific path into public rules; a fresh-session probe showed the rule
  was not loaded.
- Link `~/.codex/RTK.md` back to cstack: the link would not drift by content, but
  it would still be an unused runtime path requiring installation and auditing.
- Put RTK in `AGENTS.override.md`: Codex would select the override instead of the
  shared global `AGENTS.md`, hiding the rest of the global rules.
- Generate a combined global file: that would replace a direct source link with
  another rendered artifact that can drift.

## Verification

- A contract test pins the exact operative RTK bullet and rejects every `@`
  import form, including relative and machine-specific paths.
- The existing sharing audit continues to cover the sole live Codex global-rules
  entry point, `~/.codex/AGENTS.md`.
- A fresh read-only Codex process reports the RTK rule as present without reading
  files or running tools.
