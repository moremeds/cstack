---
name: seesaw-review
description: Review a bounded bug-fix patch for regressions in related behavior. Verify the original fix and preserved contracts with a lead and one independent Fable/Astra peer. Use for focused fixes to shared paths, error handling, filtering, fallback, retry, or scheduling; ordinary nonfunctional edits need only self-review.
---

# Seesaw Review

`seesaw-review [<patch, PR, or task target>]`

Check what the patch must change and what it must preserve. This is a bounded
code review, not a whole-repository audit. It does not replace an explicitly
required `review-cycle` or `tribunal-review`, or their risk-based gates.

## Scope and ownership

The lead owns requirements, its own review, material finding decisions and final
acceptance. Reuse the caller's scope, tracker and evidence notes. Without a
caller, create a scratch directory outside the repository for this review's
notes and peer reports. Standalone review grants no source edits, commits,
delivery or deployment; return proposed fixes.
When the caller already authorizes fixes, apply only those within that scope.
Workers never gain additional write authority from this skill.

If security, data integrity, concurrency, storage protocols or cross-system
assumptions warrant broader review, route to `review-cycle` with the evidence
collected here. A small diff is not a reason to reduce a required gate. Do not
start duplicate workflows when already inside one; return to its lead.

## 1. Freeze the question

With no target, use the current task patch. Without a caller baseline or PR,
resolve the default branch merge-base; report an unresolved scope as a gap.
Record the original failure, intended behavior and task boundary before reading
peer findings. Pin the original pre-patch revision and target snapshot in the
existing notes, including staged, unstaged and in-scope untracked files. Resolve
the base from the caller's recorded baseline or the PR target merge-base, not
an assumed HEAD. If unavailable, disclose it; do not invent before/after proof.
Keep this original base throughout corrections; also record each round's delta.

From requirements, actual callers and relevant incident rules, name the few
behaviors this patch must preserve. Record the lead's initial assessment before
reading the peer's conclusions. Passing existing behavior is not automatically
correct: explicitly identify behavior the approved fix intends to change.

## 2. Trace related behavior

Read the cumulative task diff and enclosing code. Locate direct callers,
sibling implementations of the same rule and consumers of changed results.
Record the relevant paths and why they matter. For persistent state, inspect
failure, retry and the next normal operation; for timing or environment changes,
check the actual schedule, entrypoint, configuration or deployment path involved.
Expand inspection only along concrete dependencies, not into unrelated cleanup.

Judge each path against its own contract. A scanner may report a corrupt file
as missing while a publisher must reject an incomplete replacement. Finding a
sibling does not authorize copying its exception handling or changing its scope.
Classify findings as introduced regression, incomplete original fix, or unrelated
pre-existing issue. The first two affect task acceptance; report the third
separately without silently fixing it. An unchanged caller can still be broken
by this patch. Every material claim needs a concrete input, state sequence or
source-supported failure, not a generic risk label.

## 3. Verify both sides

Reuse the smallest relevant existing checks. Where feasible, demonstrate the
original bug failing before and passing after, and required preserved behavior
passing on both versions. Use isolated fixtures/checkouts; never revert dirty
work or replay writes against production data to obtain a baseline.

Exercise the real failing interface, not a mock that swallows it. Select the
most relevant adverse input or state sequence. An error-handling fix needs
checks of returned status and stored/output artifacts, not only absence of an
exception or exit 0. For example, ignoring metadata sidecars must still reject
corrupt real data and a directory with no real data. Add a check only for a
concrete regression or acceptance gap. Record commands, outcomes, snapshot and
host; missing required evidence remains a gate gap, not a passing caveat.

## 4. One independent peer

Use `herd` for one read-only independent seat: Fable for an Astra lead, Astra for
a Claude Code lead (Fable or Opus). Verify serving identity; no downgrade or substitution. Optional
Cursor uses verified Grok 4.7 or newer; Devin may execute authorized checks or
fixes but never review or vote. If the required peer is unavailable, report the
missing gate and continue useful lead checks without a passing verdict.

Reuse herd's startup, permissions, readable pane placement and handoff rules.
Reuse only the read-only assignment and matching request/snapshot marker rules
from [herd-panel](../tribunal-review/references/herd-panel.md). The lead saves
the complete response as `seesaw-peer-<snapshot>-<round>.txt` in the existing
evidence directory and reads it directly. Expand terminal reads until the full
report and both matching markers are captured; an echo, partial response or
timeout is not a review. Preserve prior reports. This skill owns the single-peer
composition and verdict; do not invoke tribunal collection, debate or votes.

Give the peer the original issue, requirements, cumulative target, relevant
paths and raw check evidence, without the lead's verdict or another reviewer's
conclusions. Ask for a concrete counterexample to the patch's preservation
claims and any missing related path; it must read source, not trust the patch
summary. The lead independently verifies material findings and records reasons
for accepting or rejecting them. External approval is not lead acceptance.

## 5. Corrections and stopping

With already-authorized fixes, preserve the original baseline and successful
checks. For each correction, identify a new snapshot, review its cumulative
changes plus round delta, rerun affected checks, and have the same independent
peer verify the new bytes and relevant regressions. A previous verdict cannot
approve a later patch. Keep untouched evidence with its original snapshot label.

Allow at most two correction rounds in this invocation. If they do not close
the findings, the same behavior breaks again, the premise changes, or impact
cannot be bounded, return ESCALATE for diagnosis or the caller's broader review.
Do not reset the round count or baseline to continue patching indefinitely.
Scope changes still need authorization; exhaustion or timeout never means PASS.

## Report and handoff

Return one short table in the existing task notes:

| Intended change or preserved behavior | Related path | Check / evidence / snapshot | Result or gap |
| --- | --- | --- | --- |

Verdict: **PASS** only for this bounded patch when the original fix, preservation
checks, required peer and lead acceptance are evidenced on the final snapshot;
**FIX** for concrete unmet requirements; **ESCALATE** for unbounded impact,
repeated failure or an unavailable required gate. Name unverified items and
unrelated old issues separately. This verdict does not assert deployment or
production success and cannot satisfy a different required review gate.

Before closing worker context, save each agent's requested/observed model,
assignment, actual contribution, findings and lead disposition, evidence and
remaining issues in the caller's notes. Once all necessary information is with
the lead and no concrete follow-up needs that context, close task-created panes
under herd's teardown rules. Include each worker's contribution in the report.
