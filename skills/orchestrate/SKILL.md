---
name: orchestrate
description: Astra-led subagent orchestration for project work. Design task-specific roles, choose each worker's model and reasoning effort, delegate independent work, and integrate verified results. Use when asked for an agent team or adaptive multi-model execution.
---

# Orchestrate

`$orchestrate <task or approved plan>`

Use the host's native subagent tools. This skill requests delegation when it
helps the current task; it does not authorize unrelated actions or global config
changes. No separate scheduler, direct completion API, or persistent agent files
are needed. Simple tasks can finish with Astra alone.

## 1. Establish the lead and the task

- Astra (`gpt-6-astra`) owns scope, decomposition, integration, and final acceptance.
  If this session is already Astra, lead here without another manager agent.
  Keep its current effort unless the host exposes a supported way to change it.
- If another model is running, delegate the complete orchestration assignment to
  an Astra lead, normally `high`, using native tools. The outer agent relays the
  result without creating a second worker team. If workers are needed, check
  that the lead has spawn tools and available depth/slots. If it cannot spawn,
  let Astra design assignments and approve integration while the outer agent
  executes those exact dispatches as a relay. Simple tasks need no nested tools.
- If Astra or native subagents are unavailable, report that limitation. Do not
  call another model Astra, launch a CLI farm, or silently downgrade the lead.
  Continue independent read-only preparation; ask only if a substitute is needed.
- Read project guidance and relevant code/artifacts. Determine acceptance, risk,
  dependencies, and the actual bottleneck. Preserve the user's approved scope.

## 2. Design the smallest useful team

Invent roles from this task's deliverables, not from a fixed roster. For example,
a market-data bug may need a provenance investigator and a provider implementer;
a UI change may need a component implementer and an accessibility verifier.
Do not create every example role. If no independent subtask saves time or improves
quality, execute locally and state why delegation was unnecessary.

Before launching, state one compact assignment table:

| Role and deliverable | Model / effort | File ownership or read-only scope | Dependencies and acceptance |
| --- | --- | --- | --- |
| task-specific assignment | selected pair | exact scope | prerequisite and check |

Choose only models/efforts advertised by this runtime. These are starting points,
not promises of availability or measured superiority:

| Work characteristics | Starting choice |
| --- | --- |
| Clear extraction, bounded documentation lookup, mechanical checks | `gpt-5.6-luna` / `low` |
| Read-heavy exploration, tracing an existing path | `gpt-5.6-terra` / `medium` |
| Scoped implementation with known acceptance | `gpt-5.6-sol` / `medium` |
| Ambiguous design, difficult diagnosis, security/money/data-loss review | `gpt-6-astra` / `high` |

Adjust roles and effort to task uncertainty and impact. Do not use high effort
for every worker or assign a cheaper model to critical work just to fill the
table. When blocked by reasoning complexity, narrow the assignment or escalate
that worker; do not repeat an identical failed request. User-selected pairs win.
Unsupported worker choices require a disclosed supported alternative; no silent
model substitution. Do not change the user's global defaults.

## 3. Spawn with explicit settings and bounded context

Use the actual tool schema, not assumed argument names:

- With `collaboration.spawn_agent`, pass `task_name`, `message`, `model`, and
  `reasoning_effort`. For overrides use `fork_turns="none"` (or a bounded numeric
  history window); full-history forks inherit the parent and reject overrides.
- With another native spawn surface, use its documented model/effort parameters.
  If only custom roles are supported, use existing compatible roles; custom role
  TOML settings can override spawn values. Verify the effective selection rather
  than claiming that passing a model name guarantees it took effect.
- User-owned task creation (`create_thread`) is not a subagent substitute. Do
  not create sidebar tasks or fork user conversations just to emulate delegation.
- Put the objective, project/worktree path, relevant files, constraints, ownership,
  acceptance check, and requested output into every assignment. A no-history
  worker must receive the context necessary to complete that assignment.
- Workers return changes/findings, evidence (files and commands/results), blockers,
  and remaining uncertainty. Summaries replace raw logs. Workers do not spawn
  more agents unless the lead explicitly grants a bounded nested assignment.

Start only independent ready work; respect the host's free slots and count the
lead/outer relay when applicable. Prefer a small team; do not fill slots merely
because they exist. The lead does useful independent work while workers run.

## 4. Preserve ownership and steer the team

Read-only investigations may run together. Writers must own disjoint files in
the task's isolated worktree. Shared state does not become isolated just because
agents have different names. For a shared file, make one worker read-only or
transfer exclusive ownership after the previous writer has stopped and returned
its changes. The lead integrates the final edit. Serialize tests needing a stable
tree, or use separate existing worktrees when the task requires them.

The lead owns shared integration files, commits, PRs, and release actions.
Workers must preserve pre-existing changes and must not commit, merge, publish,
or change unrelated files. A prompt's read-only instruction is not a sandbox;
use an actual read-only capability when the host offers one and disclose when
access control is only by instruction.

Use native wait/status and messaging tools; avoid polling logs. Relay user
corrections to affected workers, interrupt stale work before reassigning its
files, and retain completed evidence that still applies. Do not treat timeout,
silence, or an unavailable model as successful completion. Retry only after a
meaningful change; otherwise finish the subtask locally or expose its blocker.

## 5. Integrate and verify

Wait for every required deliverable. Inspect worker changes and evidence against
the original acceptance criteria; a worker's "done" is not verification. Resolve
conflicts, then run the smallest relevant integration check on the combined result.
For plans/research, check evidence and consistency instead of inventing code tests.

End with the outcome, actual agent/model/effort selections supported by tool
results (label requested-only settings), verification, and unresolved items.
Stop/close unused workers with the host's supported controls. If called inside
`execute-plan`, return to its delivery steps; standalone orchestration inherits
the user's task and does not grant separate merge or deployment authority.

## Sources

Checked 2026-09-07: [official subagents guide](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [Astra guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra).
The role suggestions above are cstack policy; validate speed/quality on real tasks.
