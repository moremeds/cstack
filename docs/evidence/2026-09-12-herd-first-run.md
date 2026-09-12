# herd: first real run (2026-09-12)

Lead: Fable (Claude Code, pane w3:p1). Task: the six config-sync fixes from the
two-machine audit. Three transports exercised.

| Worker | Transport | Task | Result |
| --- | --- | --- | --- |
| implementer (Devin SWE-2 Max, local, adopted from cstack pane) | herdr agent | c-memory: ingest the second machine's sessions | 1 reject (slug mapping missed `/Volumes/…/projects/x`), fixed on top; PR c-memory #6 |
| Opus subagent | native | clauded: track `~/projects/CLAUDE.md`, Codex reads rendered AGENTS.md | accepted first pass, one follow-up folded in; PR clauded #27 |
| mini-runner (Devin SWE-2 High, remote, started fresh) | herdr agent over ssh | read-only inventory of the mini's transcript dirs | accepted; its evidence produced the reject above |
| livewire-2a (Claude) | peer session | reported three contract gaps from its own Devin run | folded into the skill |

Observed, now in the skill text:

- `pane wait-output` prompt regex `[$%❯>] ?$` fails on a right-prompt theme
  (clock after the prompt). Loosened to `[$%❯>]( .*)?$`.
- Devin's first-run welcome screen swallowed the first prompt
  (`agent_prompt_stalled`, input empty). Resend once.
- An adopted Devin whose pane cwd is repo A, working in a worktree of repo B,
  re-prompts for every command class (`ls`, `cat`, `find`, edits in `/tmp`).
  Start the worker with `--cwd` at the worktree.
- A remote worker cannot `herdr agent prompt` the lead's pane (different
  server). Report via file, collect with `--wait` + `ssh cat`.
- `herdr agent wait` times out on long test gates; loop while `working`.
- Workers add `Co-Authored-By` / `Generated with` trailers unless rule 5 is
  repeated in every dispatch.
- `herdr agent get` has no `--json` flag; output is JSON already.

Not exercised: Astra as lead; Codex worker; the mini-runner writing anything.
