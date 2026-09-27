# Herd routing and approval validation — 2026-09-28

Base: `f6b0aa26d0228c1cba0b3cb9b2f5a6b430086874`. Isolated branch: `feat/herd-cost-routing`. Existing unrelated untracked notes were preserved.

## Actual delegation

| Worker | Requested model / observed CLI label | Work and lead disposition |
| --- | --- | --- |
| herd-swe-routing, persistent Devin pane w3:pE | swe-2-max / SWE-2 Max | Read-only preparation; prolonged reasoning produced no diff. Interrupted before transferring exclusive ownership of the same worktree. Not counted as implementation. |
| herd-opus-routing, persistent Devin pane w3:pG | claude-opus-5-5-medium / Claude Opus 5.5 Medium | Implemented eight files and ran checks. Lead read the complete diff, corrected routing/permission contradictions, and accepted the cumulative result. |
| herd-opus-check, persistent Cursor pane w3:pF | claude-opus-5-5-medium / Claude Opus 5.5 | Read-only evaluation of eight scenarios, no implementation report supplied. Findings below were checked against source. |
| herd_final_check, native worker | gpt-6-luna / effective serving identity not independently exposed | Read-only final four-scenario check; correctly retained real delegation, approval boundaries, low-overhead native routing and authorized release execution. |

CLI labels and launch arguments establish configured models, not independently verified serving identity. No measured token/cost savings are claimed. The lead performed scope decisions, permission handling, review, integration corrections and final validation; it did not author the worker's initial implementation.

## Review disposition

- Fixed: explicit herd now requires bulk execution by workers and a dispatch record, not a token subtask followed by lead takeover.
- Fixed: contract approval list now reflects existing user authorization; the roster's command examples do not approve arbitrary arguments or effects.
- Fixed: read-only investigation may narrow an existing executor role using restrictive launch settings; no new role fleet is required.
- Fixed: ordinary native work skips external discovery; Luna/Sol require host-advertised availability. Explicit transport requests still cannot be silently substituted.
- Fixed: model aliases cannot be silently substituted; a caller-mandated legacy alias requires observed identity evidence. Removed a misleading alias test and strengthened actual roster permission/parity checks.
- Fixed: generic independent Fable review is model-based; separately invoked review workflows retain their own mandated model and transport constraints.
- Fixed: authorized release steps are an explicit exception to default delivery prohibitions. The lead approves the contract, reviews effects and owns acceptance; no new user confirmation per already-authorized step.
- Retained: one task can contain sequential steps toward one deliverable; stopping after that task is consistent with avoiding a review round for every command.
- Retained: commit policy belongs to the caller. execute-plan's implementation commit requirement is its policy, not a contradiction with other callers that authorize no commits.

## Runtime evidence and limits

- herdr 0.9.0 endpoint was compatible; workers ran interactively in background tabs.
- SWE startup was initially swallowed by a shell update question. The lead observed the failed command and relaunched in the same pane, preserving work.
- The lead observed multiple real Devin approval menus, inspected in-scope target edits and approved the displayed one-time option. Subsequent diffs and resumed tools confirmed execution. The worker report said "No approval dialogs"; this is not accepted as runtime evidence, because the lead directly handled them.
- Inherited lead-pane metadata pointed at another workspace. Reverse prompts were disabled; reports were collected via files and bounded terminal reads.
- CLI discovery listed Opus 5.5 and Fable 5.1 on both providers. SWE was marked Free; the October 31 expiry is user-reported, not independently established. Discovery snapshots were cached and filtered.
- Cursor executed actual read-only tools in ask mode without force. Cursor implementation writes under the new sandbox roster were not exercised. No production release, backfill or data-lake mutation was performed.
- All task-created workers were stopped/idle before cleanup, and their evidence saved in lead-local Git administrative storage. Existing unrelated panes were preserved. No serving-model attestations or token savings were fabricated.

## Verification

- Lead: `python3 -m unittest discover -s tests` — 124 tests passed after final corrections.
- Lead: skill-creator `quick_validate.py` — herd, orchestrate and execute-plan valid, using offline cached PyYAML.
- Lead: `git diff --check` passed.
- Behavioral checks are advisory simulations; they do not prove every future agent will obey. The new dispatch/artifact/acceptance requirements make violations inspectable rather than invisible.

Delivery is a PR. Merge, installed-skill activation and remote-machine rollout are separate, not claimed here.
