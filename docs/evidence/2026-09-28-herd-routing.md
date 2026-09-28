# Herd routing and approval validation — 2026-09-28

Historical evidence for the earlier Astra-led policy; the current operational-lead and review rules are in `skills/herd/SKILL.md`, `skills/orchestrate/SKILL.md`, and `rules/`.

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

## Acceptance ownership clarification

The user clarified that Astra is the final judge for all work. Herd now defines
its lead as Astra, rather than whichever model happens to be running. Every
deliverable, milestone and cumulative result requires Astra's own evidence check
and acceptance; worker reports, passing tests and reviewer votes cannot close
that gate. Other models may coordinate execution. If Astra is unavailable,
acceptance remains open. This does not replace required user authorization.

## Model-independent review and user routing tiers

The user subsequently prohibited review by the same canonical model, even across
providers, sessions, versions or effort settings. The earlier Cursor/Opus check
of Devin/Opus work is retained as historical diagnostic feedback, but is not
counted as independent review under this rule. Sol 6 implements the new rule;
a fresh Cursor/Fable reviewer is assigned the complete cumulative candidate,
whose substantive authors are Opus, Astra and Sol. Astra owns final acceptance.
The new tier table records the user's approximate routing preference, not a
measured benchmark or a claim that models sharing a tier have equal prices.

Fable's cumulative review exercised seven cases: cross-provider Opus self-review
(rejected), Astra-authored work (different-model review before acceptance),
Sol-to-Fable review, Fable-to-Astra review, eligible same-tier different models,
unknown identity, and scoped approval versus production deletion. Sol corrected
the material findings: stale Claude acceptance ownership, coordinator authority,
and configured-model evidence criteria. It also tied release authorization to
the user, prohibited disclosed bulk takeover without changing the herd request,
and removed an inert example permission key. The lead checked these corrections.

Configured canonical identity uses host-controlled model selection and available
runtime labels, not worker self-description. This run selected native Sol 6 via
the host spawn tool and Cursor Fable 5.1 via explicit launch arguments; the
Cursor label displayed Fable 5.1. Provider-serving attestation remains unverified.
Fable's own full test attempt had three errors because its read-only sandbox
blocked temporary Git initialization; that does not establish a code regression
or reproduce the lead's passing test run. No new unit test claims to enforce
semantic agent behavior; the scenario review is retained as behavioral evidence.

Fable's follow-up confirmed M1–M3 and L1–L3 resolved and reported no remaining
blockers. The lead independently read the cumulative changes and accepted them.
Final lead verification: 124 tests passed; Herd and Orchestrate skill validation
and diff checks passed. Worker `herd_model_rules` (native Sol 6) completed six
assigned files without committing. Reviewer `herd-fable-review` (Cursor Fable
5.1, pane `w3:pH`) made no edits; its initial and follow-up reports were saved
in lead-local Git administrative storage before closing the task-created pane.
Astra retains acceptance for all tasks; the Claude rule correction is deliberate.
