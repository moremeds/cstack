# GPT-6 Astra guidance audit

Reviewed against official documentation on 2026-09-05. Scope: cstack rules,
four SKILL.md entrypoints, review prompts, execution/review/status workflows,
branch-audit, and hooks. Existing user notes and external installed skills are
outside this repository change. Continues PR #16 from commit 8d49b40.

## Official sources and application

- [Astra model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra): clarify instruction priority, sustain authorized work through steering, calibrate verification, and specify delegation deliberately. Applied through short task boundaries, risk-based review, and relevant checks. No runtime/model settings changed.
- [AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md): global and project instructions are layered at session start. Keep the shared source; verify a new session after deployment rather than assuming an existing session reloads edits.
- [Skills authoring](https://learn.chatgpt.com/docs/build-skills): concise descriptions guide selection; full instructions load on use. Shortened all four descriptions and removed repeated narrative from execution and review. Retained detailed transport instructions where correctness depends on them.

These are cstack's applications of the guidance, not official guarantees about
latency, defect detection, or the correct number of review passes.

## Decisions

| Surface | Finding and resulting behavior |
| --- | --- |
| AGENTS.md | Skill priority and steering were implicit. State them directly; preserve authorization and dirty-work protection. Review by risk, including single-file security, money, data-loss, and contract changes. |
| execute-plan | Review-afterwards incorrectly implied pre-review. Run only requested gates; continue through delivery and preserve the current task when the user steers. Detect the delivery base instead of assuming master. |
| review-cycle | Fix-only diffs could narrow later review. Defect/adversarial passes cover the full task; fix diffs are only a secondary aid. Replace score-driven work with acceptance evidence. Reuse valid checks unless a relevant change or unresolved concern warrants another run. |
| tribunal + prompts | Consensus and intentional-shortcut comments could overrule evidence. Require a concrete failure; comments do not exempt current security/correctness defects. Keep transport, timeout, focus, dedup, and independent panel mechanics. A missing independent peer does not satisfy an independent-review gate. |
| whatup | Keep the corrected remote/task distinction and fresh-claim checks. Do not silently substitute another branch for an unresolved named task. |
| CLAUDE.md | Remove compulsory per-sentence tags and pseudo-precise confidence; retain factual boundaries. Remove stale machine-specific reviewer availability and needless ambiguity pauses. Keep model-specific Fable routing scoped to that model. |
| branch-audit | Fetch before dependent reads, avoid pruning in a read-only audit, and do not infer safe deletion or push history from missing upstream refs. |
| auto-commit | Stop hook no longer stages the whole worktree. Only the explicit staged selection is committed in opted-in projects. |
| CI hook | Query errors, invalid output, or missing gh block merge; a successfully queried empty check list remains allowed. |

## Preserved boundaries and limits

- No new dependencies, model migration, cache patch, or parallel implementation.
- Destructive confirmation, task ownership, PR-first delivery, and live-evidence
  distinctions remain. The existing test-on-edit marker remains opt-in; do not
  use its diagnostic output as proof of acceptance. Formatter/linter and RTK
  dispatch remain scoped helpers. Shell hooks do not parse every possible shell
  spelling and are not a substitute for host permissions or branch protection.
- Source symlinks still resolve to main until merge. This PR does not rewrite
  live links or claim deployment. External superpowers/other installed skills
  can still introduce conflicting rules and need their own separately scoped audit.
- Less prompt text is measurable. Faster or better task completion requires a
  controlled old/new model evaluation with the same model, effort, tasks, and
  acceptance criteria; instruction checks and unit tests do not establish it.

## Validation

Run `python3 -m unittest discover -s tests` and `git diff --check`.
Behavior checks exercise committed task changes plus review fixes, pushed branches
without tracking, preservation of unstaged/untracked data in auto-commit, and CI
query failure versus an empty check list. No benchmark or eval framework added.

A bounded fresh CLI policy-interpretation probe is recorded separately from tests;
it is not an end-to-end coding benchmark or a no-regression guarantee.

Results: 83 tests passed; diff whitespace and changed-hook shell syntax checks
passed. Replacing either changed hook with its main-branch version makes its
regression test fail. The earlier two Git range/state mutations also failed as
expected in the preceding PR validation.

Fresh-process probe: Codex CLI 0.151.0 requested `gpt-6-astra` with medium effort
in a read-only ephemeral run. The server rejected it with HTTP 400, requiring a
newer Codex version. No model answer was produced. No fallback model was used;
Astra behavioral/latency comparison remains unverified. Updating the host CLI is
outside this repository PR. The probe did not establish a performance gain.

Combined AGENTS.md + four SKILL.md entrypoint size: 97,867 to 90,381 bytes
(7.6% smaller than main). Byte size is not token usage or latency.
