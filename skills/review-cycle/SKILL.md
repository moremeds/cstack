---
name: review-cycle
description: Multi-pass review discipline with per-pass apply — self-review → tribunal-review cross-model tribunal → adversarial → simplicity/ponytail → final self-review → assumption verification → confidence calibration. Adapts its passes to code, plans, or prose. Each pass applies its own fixes and re-verifies before the next pass starts. Use after writing a plan, finishing prose, or completing an implementation.
---

## Runtime

Portable — runs under Claude Code and Codex both. Runtime-specific tracking is
routed by capability below; Pass 2's `tribunal-review` call is otherwise the
same. If `tribunal-review` is not installed, say so and stop — do not substitute
your own review and report it as a tribunal pass.

## Purpose

You have asked for this review discipline repeatedly across many projects and artifact types (code diffs, plans, PR claims, book chapters). This skill encodes it once, generically — it does not assume any single project's stack or standing rules.

## Argument (optional)

Claude Code: `/review-cycle [quick] [target] [focus text...]`

Codex: `$review-cycle [quick] [target] [focus text...]`

- `quick` (optional, first token) → abbreviated cycle: Pass 1 + a single non-debated tribunal pass (passed through to `tribunal-review` as its own `quick` modifier) + Pass 5 assumption check. Skips Pass 3 (adversarial), Pass 3b (simplicity), Pass 4, and the Pass 6 confidence loop; Pass 1's standing-rule check is still required. Use for small diffs, doc touch-ups, or anything where six passes is ceremony. Omit for the full cycle (default).
- `target` (optional):
  - No arg → review the **current branch's diff vs the repo's default base branch**.
  - A path → review **that plan/spec/doc/prose file** for adequacy before implementation or publication.
  - `pr <N>` → review **PR #N** via `gh pr diff`. Also fetch `gh pr view --json title,body` — Pass 1 must check whether the diff actually resolves what the PR description/linked issue claims, not just internal correctness.
- `focus text` (optional, everything after target) → free-text emphasis, e.g. "focus on the ndx/rut fallback path", "see if we can simplify", "ensure correctness of chapter 4". Thread this focus into Pass 1's critique, Pass 2's `focus:` argument to `tribunal-review`, and Pass 3's adversarial scenarios. A focus narrows attention; it never replaces the standard checks.

## Artifact type detection (drives which pass content applies)

Determine one of three types before Pass 1. Don't ask the user unless genuinely ambiguous — infer from the target:

| Type | Signals |
|------|---------|
| **code** | Target is a diff/PR/file with source extensions (`.py .ts .tsx .go .rs .sql` etc.), or no arg and `git diff` touches source files |
| **plan** | Target path lives under a plans/specs directory, filename/content reads as a design doc or implementation plan, or the user's focus text says "plan"/"spec"/"design" |
| **prose** | Target is documentation/book/article content — no runtime behavior, the correctness question is factual/structural, not execution-shaped |

If a target mixes types (e.g., a PR with both code and a design doc), default to **code** rules for verification gates but pull in the **plan** critique sections for the doc portion too.

These three types are the same three review classes `tribunal-review` uses, and
Pass 2 passes the type through as `--diff`/`--pr`/`--base` (code), `--plan`
(plan), or `--prose` (prose). Do not collapse prose into plan: the plan class
tells reviewers that prose polish is wasted effort, which suppresses the whole
point of a prose review.

This type selects the content used in Pass 1 (critique sections), the verification gates, Pass 3 (adversarial framing), and Pass 6 (unit of analysis) below — look up the matching row/branch in each of those sections.

## Workflow — do not skip steps

### Task tracking

Track every applicable pass, but route the tracker by available capability:

| Capability | Tracking rule |
|---|---|
| `TaskCreate` + `TaskUpdate` + `TaskList` | Claude Code: create one task per applicable pass and update its state as you go. |
| `update_plan` | Codex: use the same pass list as plan steps and keep exactly one `in_progress` pass. |
| Neither | Keep the pass ledger in the response and say that live task tracking is unavailable. |

When invoked from a parent tracker (for example `execute-plan`), reuse the
parent tracker instead of replacing it. Keep the parent review gate as the
container, preserve its other milestones, and make only the current review pass
the one `in_progress` item. Mark skipped quick-mode passes explicitly rather
than silently deleting them. Stop early **only** if a gate fails and the user
opts to abort.

**Why per-pass apply matters:** the tribunal and the adversarial pass are most valuable on a *clean* artifact. Batching all fixes into one big apply step at the end means they waste cycles on bugs you already caught. Apply between passes → each later pass sees less noise and finds deeper issues.

**Passes run in order.** Pass 2 is the slow step because it waits on external CLIs, but it is `tribunal-review`'s job to be slow efficiently: that skill launches every panel member in the background and runs the orchestrator's own review in the gap before collecting. Call it as one unit and let it manage its own concurrency — do not reach inside it to launch reviewers yourself. See Pass 2.

### Apply discipline (used by Passes 1–3)

- **Apply high-confidence fixes immediately**: clear bugs, spec violations, typos, missing edge cases the spec called out, broken cross-layer wiring (API ↔ types ↔ UI ↔ DB), factual errors (prose).
- **Defer judgment-call fixes** until after the Pass 2 tribunal weighs in: architecture pushes, scope changes, taste calls, anything where you're unsure whether the change is an improvement.
- **Track what you deferred** in your task list so Pass 2 can revisit them with the tribunal's input.

### Verification gates (run after each pass's apply step)

Don't hardcode a stack. Discover gates from the repo itself, every time:

- Read the target repo's `CLAUDE.md`/`AGENTS.md` for its own build/test/lint commands and any standing rules (banned patterns, required tools, forbidden data sources) — those are project-specific and override anything generic here.
- **code**: look for `pyproject.toml` (test runner + whether bare `python`/`pytest` is banned), `package.json` (`npm run typecheck`/`test`/`gen:types` scripts), a migrations directory (replay script), an OpenAPI/contract file (regen + diff check). Run whatever actually exists; don't invent commands the repo doesn't have.
- **plan**: no runtime gates. Check internal consistency (does step 4 depend on something step 7 introduces?) and consistency against the named design doc or linked spec.
- **prose**: no runtime gates. Check factual claims against cited/available sources and internal consistency across sections/chapters.

Record exact commands and pass/fail in your task notes after every pass. If a gate fails, fix forward before starting the next pass.

### Pass 1 — Self-review against the spec → apply → verify

1. Identify the spec. If reviewing code, locate the matching plan (ask the user where it lives if unsure, or check the PR description). If reviewing a plan, the user's request plus any referenced design doc is the spec. If reviewing prose, the spec is factual accuracy plus whatever structural/style brief the user gave. If target is a PR, also pull `gh pr view --json title,body` as part of the spec — the PR's own stated intent.
2. Read the spec and the artifact end-to-end.
3. Produce a structured critique. Use the row matching the artifact type:

   | Type | Critique sections |
   |------|-------------------|
   | code | Correctness vs spec · Edge cases · Cross-layer consistency · Standing-rule violations (from the repo's own CLAUDE.md/AGENTS.md) · Test coverage gaps · Is there a materially simpler approach to the whole spec (stdlib/native/DB constraint instead of this code)? — approach-level only; line-level cleanup waits for Pass 3b · Assumptions you made that aren't verified |
   | plan | Consistency with the named design/spec · Sequencing correctness (does a later step depend on an earlier one that doesn't produce it?) · Completeness (steps missing to reach the stated goal) · Standing-rule violations · Is there a materially simpler approach reaching the same goal? · Assumptions you made that aren't verified |
   | prose | Factual correctness against sources · Internal consistency (claims that contradict earlier sections) · Structural completeness vs the brief · Unsupported claims needing a citation or a flag · Standing-rule violations |

   If a focus was given, add a dedicated critique line for it.
4. List the concrete fixes. Tag each as **high-confidence** or **judgment-call** per the apply discipline above.
5. **Apply** the high-confidence fixes. Keep the judgment-call list for Pass 2.
6. **Verify** per the gates section.
7. Record the Pass-1 fix list (applied + deferred) in your task notes so Pass 2 can cross-reference.

### Pass 2 — Cross-model tribunal via `tribunal-review` → apply → verify

**Invoke the `tribunal-review` skill. Do not hand-roll this pass.** One call,
with the artifact type mapped to its review class and the user's focus passed
through verbatim:

```
tribunal-review <target-flag> [quick] [focus: <the user's focus text>]
```

| This skill's type | Target flag to pass |
|---|---|
| code, no arg | `--diff` (uncommitted) or `--base <default branch>` (branch diff) |
| code, `pr <N>` | `--pr <N>` |
| plan | `--plan <path>` |
| prose | `--prose <path>` |

In `quick` mode pass `quick` through; the tribunal then skips its own debate and
rebuttal instead of you skipping the tribunal.

**Everything about running the external CLIs belongs to that skill** — which
binaries are alive, how they are launched and waited on, how findings merge by
weighted consensus, and what happens when one is missing. This skill's job is
Pass 2's *inputs* (target, class, focus) and its *outputs* (what to apply).

Then merge its verdict with your own Pass-1 list:

1. Read the tribunal's output. Cross-reference against your Pass-1 list:
   - **Tribunal flags something Pass 1 caught and you already fixed** → confirmation, no action.
   - **Tribunal flags something Pass 1 caught but you deferred as judgment-call** → the tribunal's vote breaks the tie; apply unless you have a clear reason.
   - **Tribunal-only finding** → evaluate; default to applying unless you have a clear reason.
   - **Pass-1-only finding it missed** → flag the disagreement explicitly; apply anyway if you still believe it.
2. **Apply** all scheduled fixes — both the tribunal's findings and the previously deferred Pass-1 judgment calls that its input has now resolved.
3. **Verify** per the gates section.

**Verdict mapping.** `tribunal-review` reports `APPROVE` or `CHANGES NEEDED`;
this cycle reports `SHIP` / `FIX-FIRST` / `NEEDS-REWORK`. They are not the same
scale and the tribunal's verdict is an input, not the answer — it has seen one
pass, you finish six:

| Tribunal said | After you apply its findings and the later passes |
|---|---|
| APPROVE | `SHIP`, unless a later pass finds something |
| CHANGES NEEDED, all findings applied and gates green | `SHIP` |
| CHANGES NEEDED, findings applied but a gate still fails or an assumption is unverified | `FIX-FIRST` |
| CHANGES NEEDED with a CRITICAL that invalidates the approach itself | `NEEDS-REWORK` |

<!-- rationale:begin — quotes the banned commands to explain why they are gone -->
**Why this pass is one skill call.** Measured across all 12 real invocations
of this cycle: 189 Bash calls touched `codex`/`gemini`, and **86 (46%) were
polling or status checks** babysitting a hand-rolled panel. Availability was
checked with `which` 15 times and with a real liveness probe 0 times — which is
how an installed-but-unlicensed Gemini passed as present. And `codex exec
review`, the command this file used to prescribe, ran **twice in 189 calls**,
both times as `--base <branch>` with no prompt, because the flag and a
positional prompt are mutually exclusive — silently dropping the user's focus
text. `tribunal-review` owns reviewer launch, liveness, waiting, focus
propagation, and PID-scoped cleanup, and fixes each of those once.
<!-- rationale:end -->

**Trade-off, stated plainly:** Pass 3 no longer runs concurrently with the
tribunal — the skill call blocks. The concurrency that mattered is still there
(the panel members run in parallel with each other and with the orchestrator's
own review, inside the skill). What is lost is overlapping Pass 3 with Pass 2,
worth roughly one adversarial pass of wall-clock. What is gained is the 46% of
external-CLI calls that existed only to babysit that overlap, plus a tribunal
that actually receives the focus parameter.

### Pass 3 — Adversarial review → apply → verify

Runs after the tribunal's findings have been applied, not alongside it.

1. Reframe per artifact type:

   | Type | Adversarial framing |
   |------|---------------------|
   | code | "How would I break this in production?" Try at minimum: concurrent writes, empty/null inputs, malformed user input, provider outage, partial migration state, retries on non-idempotent ops, races between scheduled jobs, secrets leaking into subprocess envs. |
   | plan | "Which step fails during execution, and where would two engineers implement this differently because it's underspecified?" |
   | prose | "What would a domain expert dispute? Which claims have no support, and which would a critical reader flag as wrong or overstated?" |

   Fold in the user's focus text as an explicit extra scenario if one was given.
2. **Apply** every new fix that survives a "would this actually happen?" sanity check.
3. **Verify** per the gates section.

### Pass 3b — Simplicity / optimality review (ponytail) → apply → verify

Is this fix/feature actually the **optimal** solution, or just a working one? Runs after Pass 3's apply+verify, before Pass 4. Skipped in `quick` mode.

**This is not a repeat of the tribunal's sweep.** Every `tribunal-review`
reviewer already runs a mandatory over-engineering sweep and must return either
findings or an explicit `OVER-ENGINEERING SWEEP: clean` line — so the original
artifact has been swept by the whole panel before you get here. What the panel
could not see is **what Passes 2 and 3 added afterwards**: every fix you applied
in response to the tribunal, and every guard, branch, or handler Pass 3's
adversarial framing talked you into. Adversarial passes add code by
construction; nothing has questioned that code yet. Scope this pass to the
cumulative diff *since* the tribunal ran, and say so if the answer is nothing.

1. If the `ponytail:ponytail-review` skill is available, invoke it via the Skill tool on the cumulative diff; otherwise apply the same lens manually. Per artifact type:

   | Type | Simplicity questions |
   |------|---------------------|
   | code | Does each added piece need to exist at all? Could stdlib / a native platform feature / an already-installed dependency replace it? Any abstraction with one implementation, config for a constant, scaffolding "for later", or a multi-line block that should be one line? Is there a materially simpler design that solves the same spec? |
   | plan | Is there a simpler approach reaching the same goal with fewer steps/components? Any step building infrastructure no later step consumes? |
   | prose | Any section that says nothing the brief needs? Redundant restatement across sections? |

2. **Apply** simplifications that preserve behavior and don't undo a fix from Passes 1–3. A simplification that would weaken correctness, validation at trust boundaries, or error handling is rejected — note it and move on.
3. **Verify** per the gates section — simplification is the pass most likely to break something, so gates are mandatory here, not optional.
4. Record what was cut (or "nothing to cut") in your task notes; report deliberate keep-it-anyway decisions with a one-line reason.

### Pass 4 — Final self-review of the cumulative diff

1. Re-read the **cumulative diff/artifact after Passes 1–3b** (not the original, not any single pass's slice). Confirm each fix landed where intended and no pass regressed an earlier one.
2. Re-check standing rules **from the target repo's own CLAUDE.md/AGENTS.md** — this skill does not hardcode any project's banned patterns or required tools. If the repo has none, note that explicitly rather than skipping silently.

### Pass 5 — Assumption verification (the gate)

Before declaring done, write out each assumption you've been carrying and the evidence that backs it. Examples:
- "Migration is idempotent" → ran the repo's migration script twice, second run was no-op ✅
- "API types match server" → ran the repo's type-gen command, diff is empty ✅
- "Worker picks up new code" → checked process etime; restarted if needed ✅
- "UI feature works" → opened in browser (or explicit "I cannot test UI" disclosure)
- "Chapter's claim is accurate" → checked against the cited source ✅

If any assumption is unverified, either verify it or surface it explicitly in the final report. Never paper over a gap. `quick` mode ends here.

### Pass 6 — Confidence calibration (the loop)

The intent: stop only when the **weakest link** is strong, not when the average looks fine.

1. **Enumerate components** — the natural units of the artifact type:
   - code → each touched module, migration, API contract, UI surface, and test file
   - plan → each requirement / step / milestone
   - prose → each chapter / section / major claim
2. **Rate each 0–10** with a one-line justification grounded in evidence from Passes 1–5 (not vibes). Examples:
   - `storage/trade_insights_ai.py` — **9/10** — covered by new unit tests + integration test hit it green
   - `worker claim-loop concurrency` — **5/10** — no test exercises two workers racing on the same row; relied on advisory lock by inspection only
   - `chapter 4, claim about X` — **6/10** — matches one source, couldn't cross-check a second
3. **Pick the lowest-rated component.** Patch it. A patch is one of:
   - Re-spec / tighten language (for plans/specs)
   - Add a targeted test that exercises the doubt (code)
   - Run a verification command and record the output (code)
   - Inspect the runtime path, or find a second corroborating source (prose)
   - Refactor away the fragility
4. **Re-rate** after the patch. If the lowest is now ≥ 8, move to the next-lowest; loop until `min(rating) ≥ 8`.
5. **Bail condition.** If a component cannot be pushed to ≥ 8 in this cycle (e.g. needs prod data, requires user decision, depends on external service or unreachable source), stop the loop and surface it explicitly in **What I did NOT verify** with the residual rating and the reason.
6. **Record final per-component ratings** in the report.

Guardrails for this pass:
- **Anchor on evidence, not optimism.** A "9/10" with no verifying action behind it is a 5.
- **Patching ≠ rewriting.** Each round targets the single weakest link; resist scope creep into adjacent components.
- **One loop, not infinite.** If you've made 3 patch rounds on the same component without crossing 8, that's the bail condition firing — disclose it.

## Final report format

**The ledger is not optional and no row may be deleted.** Measured across the 12
logged runs of this cycle: the verdict line was reported 12/12 times, but the
assumption check behind it appeared in only 6, a `min:` confidence rating in 8,
and the standing-rule check in 9. Nothing failed — the weaker runs simply
omitted the section and the verdict came out looking identical to a run that had
done the work. A verdict is a claim about evidence; a report that can drop the
evidence and keep the claim is the exact failure this cycle exists to prevent.

So every row below ships in every report, and a pass that did not run says so in
its own row. "Skipped (quick mode)" and "not applicable — plan target, no
runtime gates" are complete answers. Silence is not.

**SHIP requires a complete ledger.** Pass 5 and the standing-rule check must run
in every mode. Pass 6 must run in full mode; in quick mode, `skipped (quick mode)`
is complete evidence and does not cap `SHIP`. Any other missing required row caps
the best available verdict at FIX-FIRST — not because something is broken, but
because you do not know that nothing is.

```
## Review Cycle — <target> [quick|full]

### Verdict: SHIP / FIX-FIRST / NEEDS-REWORK

### Pass ledger
| Pass | Ran? | Evidence |
|---|---|---|
| 1 self-review | yes | N findings, M applied |
| 2 tribunal-review | yes | APPROVE / CHANGES NEEDED · panel that answered |
| 3 adversarial | yes / skipped (quick) | N scenarios tried, M found |
| 3b simplicity | yes / skipped (quick) | what was cut, or "nothing to cut" |
| 4 cumulative re-read | yes / skipped (quick) | — |
| 5 assumptions | yes | N verified, M disclosed |
| 6 confidence | yes / skipped (quick) | min N/10 |
| standing rules | yes / none found in repo | which file they came from |

### Findings applied (by pass)
- **Pass 1 (self-review):** [path:line] <one-line description>
- **Pass 2 (tribunal-review):** [path:line] <one-line description>
- **Pass 3 (adversarial):** [path:line] <one-line description>
- **Pass 3b (simplicity/ponytail):** [path:line] <what was cut, or "nothing to cut">

### Tribunal
- **Verdict:** APPROVE / CHANGES NEEDED — panel that ran, and any member that degraded
- <Pass-1 finding the tribunal didn't catch / contradicted>

### Standing-rule check (from target repo's CLAUDE.md/AGENTS.md)
- ✅ / ❌ per rule with evidence, or "no standing rules found" if none exist

### Assumptions verified
- ...

### Confidence (final ratings)
- <component> — **N/10** — <one-line justification> (full) / skipped (quick mode) — Pass 6 did not run
- ...
- **min:** N/10 — <which component> (full) / not rated — skipped (quick mode)

### What I did NOT verify
- ... (include any component that finished below the 8/10 threshold, with the reason)
```

## Stopping condition

- In full mode, all standing rules found in the repo pass, all verification commands are green, all assumptions are verified or disclosed, and **`min(confidence) ≥ 8` or every sub-8 component is disclosed in "What I did NOT verify"**.
- In quick mode, the same standing-rule, verification, and assumption gates pass; Pass 6 is recorded as `skipped (quick mode)` and no confidence minimum is required.
- **The pass ledger is complete** — every row present, every "no" carrying its reason. A missing row is not a passing run, it is an unreported one.
- `quick` mode stops after Pass 5 (it still ran the tribunal, in the tribunal's own `quick` mode).
- Or: user says stop / changes scope.

## Guardrails

- **Never commit, push, or open a PR from inside this skill.** Hand off to `/ship` or wait for explicit user instruction.
- **Never skip the tribunal pass.** Not even when Pass 1 looked clean, and not in `quick` mode either — `quick` makes the tribunal cheaper (no debate, no rebuttal), it does not remove it. It must run against the *cleaned* post-Pass-1 artifact to be worth the spend.
- **Never drive the external CLIs yourself.** No `codex exec`, no `gemini -p`, no `claude -p` from this skill — call `tribunal-review` and let it own them. In particular never poll a reviewer's output file in a `sleep`/`until` loop, never check availability with `which` or `command -v` (an installed binary can still be unlicensed or logged out — the skill probes for a live reply instead), and never `pkill -f "codex exec"`, which kills every unrelated Codex job on the machine. All three were real failure modes in this cycle's own logged history.
- **Never declare done with unverified assumptions** — surface them in the final report instead.
- **Never report a verdict richer than the ledger supports.** Dropping assumptions, or dropping confidence evidence in full mode, and still reporting SHIP is the most common way this cycle has degraded. Quick mode must carry the explicit skipped-confidence evidence instead. The ledger exists so the degrade is visible instead of silent.
- **Don't batch-apply.** If you find yourself collecting fixes across Passes 1–3b without applying, you've reverted to the old workflow. Stop, apply, verify, then continue.
- **Don't hardcode any project's stack or standing rules into this skill.** Discover them from the target repo every run — this skill is used across many unrelated projects.
