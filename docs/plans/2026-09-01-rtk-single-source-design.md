# RTK single-source design

## Goal

Make RTK guidance active in fresh Codex sessions while preserving cstack as the
only public source. A generated local `RTK.md`, a machine-specific path in public
rules, or a matching regular-file copy is drift.

## Chosen design

- `rules/AGENTS.md` states the RTK shell-prefix rule directly because Codex loads
  the `AGENTS.md` instruction chain and does not expand a bare `@path` line.
- `rules/RTK.md` remains the canonical RTK reference.
- The private bootstrap links `~/.codex/RTK.md` to `rules/RTK.md` and audits that
  exact target alongside the existing public surfaces.
- Missing cstack input fails closed before bootstrap mutates live config. A
  non-symlink live copy is reported as drift; bootstrap moves it to the
  recoverable trash directory before creating the canonical link.

## Rejected alternatives

- Keep the output of `rtk init -g --codex`: it creates a local copy and writes a
  machine-specific path into public rules; a fresh-session probe showed the rule
  was not loaded.
- Put RTK in `AGENTS.override.md`: Codex would select the override instead of the
  shared global `AGENTS.md`, hiding the rest of the global rules.
- Generate a combined global file: that would replace a direct source link with
  another rendered artifact that can drift.

## Verification

- Contract tests require a copied or incorrectly targeted `~/.codex/RTK.md` to
  be reported as drift rather than accepted as equivalent content.
- Bootstrap tests require the RTK source before mutation and create the link.
- The sharing audit reports the RTK entry as `ok` only for the canonical target.
- A fresh read-only Codex process reports the RTK rule as present without reading
  files or running tools.
