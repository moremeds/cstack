---
name: execute-plan
description: Execute an already-approved plan end-to-end without further questions — worktree → straight-through implementation → milestone commits → evidence-based verification → final what-was-verified summary. Optional --full-cycle wraps it with review-cycle before and after, plus plan-defined e2e validation. Use after a plan has been written and approved.
---

## Purpose

You repeatedly paste this 7-line invocation to kick off execution after a plan is approved:

```
create a worktree and branch if not created, to execute the plan
in line implementation straight through approach
commit when there is a milestone achieved
when the plan is fully executed,
ensure you have a clear evidence of verification
verify the evidence
last give me a guidance on what has been verified, what is the evidence.
```

This skill codifies that invocation so you can just type `/execute-plan` (optionally with a plan reference) and get the same behavior, with the right guardrails.

A longer variant of the same request shows up just as often: write the plan, review it, execute it, review the result, then run a real end-to-end check. `--full-cycle` codifies that longer chain; the bare command still does just execution.

## Runtime routing

Route by the capabilities actually available. Do not infer a runtime name:

| Capability | Use |
|---|---|
| `TaskCreate` / `TaskUpdate` / `TaskList` | Track milestones and review gates with those tools |
| `update_plan` | Track the same entries there, with at most one `in_progress` |
| neither tracker | Keep the milestone list in the reply; tracking is not an execution gate |
| structured question tool | Use it for the one permitted blocking decision |
| no structured question tool | Ask one bounded standalone question as the entire reply |

This routing remains in force inside skills this invocation calls, including
`review-cycle`. A nested instruction that names an unavailable tracker maps to
the tracker above; it is not a reason to improvise or skip the review.

## Argument (optional)

`/execute-plan [--full-cycle] [<plan-ref>]`

- `--full-cycle` (optional) → wraps execution with a review pass (see **Which reviewer** below): reviews the plan first (hard gate — must pass before any code is touched), executes as normal, then reviews the cumulative diff and runs any plan-defined end-to-end validation with real data. See Steps 0 and 7 below. The flag is also implied when the invocation asks in prose for a review afterwards ("then run /review-cycle", "之后跑一次 review") — treat that as `--full-cycle`.
- No arg → execute the most recently and explicitly approved plan in this conversation.
- `<plan-ref>` → a path like `docs/plans/2026-06-02-foo.md` or a task ID — read it as the plan to execute.

## What this means

- **Straight-through.** No mid-task confirmation questions. The plan is approved; the steps run.
- **Milestone commits.** Commit each meaningful chunk as it lands. Don't batch into one final commit; don't commit one tiny step at a time. Use the natural seams in the plan.
- **Evidence over assertion.** "Tests pass" is not evidence. The pytest output, the curl response, the screenshot, the schema dump — those are evidence. Capture them inline as the steps run.
- **Verify the evidence.** After collection, sanity-check: are the assertions in the evidence actually what the plan required? Look for shallow-pass traps (e.g., test count goes up but the new test name doesn't match the new code).

## Steps

0. **Full-cycle pre-review gate** (only with `--full-cycle`, and only if this exact plan version has not already passed review). Before touching code, review the plan itself — see **Which reviewer** below. If the approved plan exists only in conversation or behind a task ID, copy it verbatim to a scratch artifact **outside the repository** and pass that path to `review-cycle`; do not dirty the checkout just to create a review target. Proceed to Step 1 only on a passing verdict (`review-cycle`: SHIP; `tribunal-review`: APPROVE) **with zero unresolved findings**. `CHANGES NEEDED` is not passable by asserting you applied the findings — apply only scope-preserving corrections, re-run the reviewer on the edited plan, and carry its new verdict. A correction that changes business, scientific, or authorization assumptions requires the one blocking question instead. Findings the reviewer left unresolved or escalated go to the user, not into your own pass.

1. **Worktree setup + execution baseline.** If the work isn't already in a worktree, create one in `.worktrees/<branch-slug>/`. Use the existing branch if checked out, otherwise create `<scope>/<short-title>` from master. If the target branch is already checked out in the main tree (a branch can't be checked out twice), move it into `.worktrees/<branch-slug>/` or branch off it there — or state in one line that worktree creation is being skipped and why; never skip silently. Don't ask which branch — derive from the plan's title or context. If a reused branch contains unrelated commits that must not ship with this plan, create a fresh branch/worktree from the correct delivery base instead of merely excluding them from review; keep stacked commits only when the plan actually depends on them. Before the first plan-caused edit, record `EXEC_BASE=$(git rev-parse HEAD)` plus the current staged, unstaged, and untracked sets. Those are the boundary between pre-existing work and this execution; never reconstruct the boundary later from the default branch.

2. **Track the milestones.** Translate the plan into one entry per milestone using **Runtime routing**. With `--full-cycle`, add entries for the pre-review gate and the post-review + e2e gate so the tracker cannot show “complete” while review is still pending. Mark an entry `in_progress` before starting it, and `completed` only when its commit or gate lands **and** the evidence satisfies the plan's own stated acceptance condition for that milestone, on the host or environment the plan names. If the condition names one machine and the check ran on another, the entry is not complete — leave it open and record the gap.

3. **Run each milestone straight through.**
   - Write the code / edit files.
   - Run the tests the plan calls for. Capture output.
   - If a test fails, fix it before moving on (don't carry a red bar into the next milestone).
   - On green, commit with a focused message. Stage explicit paths, listing files individually (never `git add -A`/`--all`, even scoped to paths — `git add -A <dir>` still stages untracked files under that dir; ignoring the git-guard warning is not an option).
   - Commit messages: `<type>(<scope>): <subject>` matching repo style. No Claude trailers (per global CLAUDE.md).

4. **Collect evidence as you go.** Don't wait for the end. For each milestone, note the verification artifact and where it lives:
   - Test runs → command + exit code + tail of output
   - Browser checks → screenshot path or curl response
   - Schema changes → `\d <table>` output or alembic upgrade log
   - Performance claims → before/after timings

5. **Verify the evidence.** Before declaring done, re-read your collected artifacts critically:
   - Does each "verified" claim have a concrete artifact backing it?
   - Are any claims based on inference (e.g., "the build passed so the change is correct")?
   - Are there assertions in the plan that _don't_ yet have evidence? Surface them.
   - Adversarial edge-case pass: before writing the table, probe the cases the plan's tests don't cover — empty inputs, duplicate/overlapping inputs, unknown enum values, zero denominators. "Tests green + 100% coverage" alone is not verification; missing tests pass trivially.

6. **Final summary table.** Present a table the user can scan:

   | Claim                         | Evidence            | How to re-verify          |
   | ----------------------------- | ------------------- | ------------------------- |
   | <what was supposed to happen> | <concrete artifact> | <one-line command or URL> |

   All three columns are required; a claim without a re-verify command is an unverified row and must be labeled as such.

   Include a row for any unverified item (state explicitly that it's unverified and why).

   The table must reflect the run's **actual** end: if more milestones land after a table was issued, reissue the full table before ending the run. Also refresh it right before any pause or context compaction — a table that covers only the first half of the work is the most common historical failure.

   If `--full-cycle` was **not** passed, end here with one declarative line: `Next step (not run): <reviewer> on this diff`, plus any plan-defined e2e check. State it; never phrase it as a question and never run it.

### Which reviewer

Both are portable skills now — `review-cycle` and `tribunal-review` each live in
`~/.agents/skills/` and are visible to Claude Code and Codex alike. Prefer
`review-cycle`: it is the full cycle, and it calls `tribunal-review` as its own
Pass 2. Fall back to `tribunal-review` alone only if `review-cycle` is not
installed in the runtime you are in — that is the cross-model panel without the
surrounding apply-and-verify passes, a real review but a smaller one.

Say which of the two ran in the summary table; never report a `--full-cycle`
gate as satisfied by a reviewer that never ran.

7. **Full-cycle post-review + e2e** (only with `--full-cycle`). Review exactly the committed cumulative delta since `EXEC_BASE`. Before each post-review, verify every plan-created file and pending fix, make the corresponding focused milestone or review-fix commit, and confirm a clean worktree; never rely on a reviewer to discover staged or untracked files implicitly. Use `review-cycle` when the branch diff equals that execution delta — the normal case for the fresh worktree created in Step 1. Otherwise the range is wrong: fall back to `tribunal-review --base <EXEC_BASE>` and disclose the downgrade. If a review applies further fixes, verify them, create a focused review-fix commit, and re-run the same reviewer before reporting done. If the plan defines an end-to-end validation (a smoke test, a real API call, a real query), run it now against real data — never synthetic values or placeholder tickers, per the no-synthetic-data rule. Add the reviewer, verdict, `EXEC_BASE`, and e2e result as rows in the summary table from Step 6. The verdict is a gate, not a note: `APPROVE`/`SHIP` completes the run; `CHANGES NEEDED`/`FIX-FIRST` means apply the findings, re-verify, commit, and re-review; a finding that invalidates the approach stops the run and goes to the user.

8. **Remote delivery.** Delivery is part of the run, not a follow-up question. Unless the invocation said otherwise, the run ends with the branch pushed and a PR opened — or the existing PR updated — even when the plan omits that mechanical step, and the PR URL goes into the summary table as a row. Before any push/PR, verify the current repo is the plan's target repo (`git remote -v` / cwd) and the branch diff contains only the intended delivery — a mismatch is a hard stop. Never push directly to `master`/`main`.

## Guardrails

- **Don't ask "should I continue?"** The plan was approved before this skill ran. Never end a turn with "want me to…?", "should I…?", "要不要…?", "需要我…?" — make the call yourself and record the decision + rationale as a row in the evidence table. The one exception is a fork that changes scientific/business assumptions or authorization scope, not implementation mechanics. Ask exactly one question through **Runtime routing**; without a structured question tool, make it one bounded standalone question with the decision, options, and impacts.
- **If a milestone blows up the scope.** Stop, surface what you found, ask. Don't silently expand the plan. Likewise, a materially new user ask mid-run is a **new plan and a new invocation** — don't fold it into this run as open-ended continuation (historical worst case: one invocation absorbed 4 unplanned branches and 3.6k turns).
- **Don't skip the verification step.** "Tests pass" without an artifact is not done. The user will ask "what's the evidence?" — pre-empt that.
- **No `--no-verify` on commits.** If a hook fails, fix the underlying issue. Per global CLAUDE.md.
- **Pre-existing untracked files.** Before staging, check `git status -s` for `??` entries that weren't created by this plan. List them explicitly and exclude them. Never `git add -A` or `git add .`.
- **Final "guidance on what has been verified."** This is the user's deliverable — make it concrete, with paths and commands, not prose summaries.

## When NOT to use this skill

- Plan hasn't been written yet → write the plan first (plan mode / brainstorming).
- Plan hasn't been approved → present it for approval first.
- The task is a single small edit → just do it directly; this skill's ceremony is overkill.
