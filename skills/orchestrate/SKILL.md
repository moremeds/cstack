---
name: orchestrate
description: Coordinate independent subtasks with Astra when an agent team is requested or delegation improves delivery.
---

# Orchestrate

`$orchestrate <task or approved plan>`

Use native subagents for independent work that benefits the task. Simple tasks
can finish with Astra alone. This skill grants no extra scope or authority;
do not add a scheduler, direct completion API, or persistent agent files.

## 1. Lead and scope

- Astra (`gpt-6-astra`) owns scope, decisions, integration, and final acceptance.
  Lead here if already Astra; keep the current effort unless the host supports
  changing it. Read relevant guidance and artifacts to establish acceptance,
  dependencies, risk, and the bottleneck.
- If another model is running, delegate the complete orchestration assignment to
  an Astra lead, normally `medium`, using native tools. The outer agent relays the
  result without creating a second team. Check the lead's spawn tools and free
  depth/slots; if it cannot spawn, relay its assignments and integration decisions.
- If Astra or native subagents are unavailable, report that limitation. Do not
  call another model Astra, launch a CLI farm, or silently downgrade the lead.
  Continue independent read-only preparation; ask only if a substitute is needed.

## 2. Assign independent work

Choose roles from the actual deliverables. Before dispatch, state each worker's
scope, model/effort, ownership, dependencies, and acceptance briefly; use a table
only when it helps compare assignments. No explanation is needed for doing a
simple task directly.

Choose only models/efforts advertised by the runtime. These are starting points,
not a fixed team or measured performance claims:

| Work characteristics | Starting choice |
| --- | --- |
| Clear extraction, bounded documentation lookup, mechanical checks | `gpt-5.6-luna` / `low` |
| Read-heavy exploration, tracing an existing path | `gpt-5.6-terra` / `medium` |
| Scoped implementation with known acceptance | `gpt-5.6-sol` / `medium` |
| Ambiguous design, difficult diagnosis, security/money/data-loss review | `gpt-6-astra` / `medium` |

Adjust to uncertainty and impact; use stronger reasoning for difficult decisions
and lighter execution for routine work. User-selected pairs win. If unsupported,
disclose a supported alternative rather than silently substituting. Narrow or
escalate a reasoning-blocked assignment instead of repeating it unchanged.
Do not change global defaults or claim an unavailable model switch.

## 3. Dispatch

Use the actual tool schema, not assumed argument names:

- With `collaboration.spawn_agent`, pass `task_name`, `message`, `model`, and
  `reasoning_effort`. For overrides use `fork_turns="none"` (or a bounded numeric
  history window); full-history forks inherit the parent and reject overrides.
- On other native surfaces, use their documented parameters or existing compatible
  roles. Role configuration can override spawn settings: report requested settings
  as requested unless returned metadata establishes the effective model/effort.
- User-owned task creation (`create_thread`) is not a subagent substitute. Do
  not create sidebar tasks or fork user conversations just to emulate delegation.
- Give each worker its objective, project/worktree, relevant files, constraints,
  ownership, acceptance, and output requirements; include enough context for a
  no-history worker. Require concise changes/findings, evidence, blockers, and
  uncertainty. Nested delegation needs an explicit bounded assignment from the lead.

Start independent ready work within free slots, counting the lead/outer relay.
Use only useful workers; the lead does independent work while they run.

## 4. Ownership and steering

Read-only investigations may run together. Writers own disjoint files in the
task's isolated worktree. For shared files, use read-only help or transfer exclusive
ownership after the previous writer stops and returns changes. The lead integrates.
Serialize tests that need a stable tree or use separate worktrees when required.

The lead owns shared integration files, commits, PRs, and release actions.
Workers must preserve pre-existing changes and must not commit, merge, publish,
or change unrelated files. A prompt's read-only instruction is not a sandbox;
use an actual read-only capability when the host offers one and disclose when
access control is only by instruction.

Use native wait/status and messaging, not log polling. Relay corrections,
interrupt stale work before reassigning files, and keep still-valid evidence.
Timeout, silence, and unavailable models are not success. Retry after a meaningful
change; otherwise complete the subtask locally or report its blocker.

## 5. Acceptance and delivery

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
