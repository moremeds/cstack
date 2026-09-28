---
name: orchestrate
description: Coordinate independent subtasks when an agent team is requested or delegation improves delivery.
---

# Orchestrate

`$orchestrate <task or approved plan>`

Use native subagents for independent work that benefits the task. Simple tasks
can finish with the lead alone. This skill grants no extra scope or authority;
do not add a scheduler, direct completion API, or persistent agent files.

## 1. Lead and scope

- The operational lead owns scope, decisions, integration, and final acceptance
  of every deliverable and the cumulative result. Use GPT-6 Sol in Codex or
  Opus 5.5 in Claude Code by default, unless the user chooses another capable
  lead. Worker and adviser reports are inputs, never acceptance on the lead's
  behalf. Read relevant guidance and artifacts to establish acceptance,
  dependencies, risk, and the bottleneck.
- If this invocation starts on Astra or Fable and the user did not choose that
  model as lead, hand the complete assignment to an eligible Sol or Opus peer or
  native agent: scope, worker dispatch, integration, review, acceptance and
  delivery. The outer model relays concise progress and results; consult it
  only for a bounded hard or risky question or required independent review.
- If the requested lead or native subagents are unavailable, report the exact
  limitation and actual model. Do not claim a Sol/Opus lead or silently
  substitute one; continue authorized work as needed without a CLI farm.

## 2. Assign independent work

Choose roles from the actual deliverables. Before dispatch, state each worker's
scope, model/effort, ownership, dependencies, and acceptance briefly; use a table
only when it helps compare assignments. No explanation is needed for doing a
simple task directly.

Choose only models/efforts advertised by the runtime. These are starting points,
not a fixed team or measured performance claims:

| Work characteristics | Starting choice |
| --- | --- |
| Clear extraction, bounded lookup or search, mechanical checks | `gpt-6-luna` / `low` |
| Scoped implementation with known acceptance, tracing an existing path | `gpt-6-sol` / `medium` |
| Ambiguous design, difficult diagnosis, security/money/data-loss review | bounded `gpt-6-astra` / `medium` advice or required independent review |

Adjust to uncertainty and impact; use stronger reasoning for difficult decisions
and lighter execution for routine work. User-selected pairs win. If unsupported,
disclose a supported alternative rather than silently substituting. Narrow or
escalate a reasoning-blocked assignment instead of repeating it unchanged.
For GPT-6 Sol, start at `medium` for bounded implementation and ordinary lead
work; use `high` for difficult multi-step planning, debugging or integration.
Reserve `xhigh`/`max` for the hardest tasks when task evidence justifies the
extra time and tokens. `ultra` adds subagents and is not a reasoning effort.
Do not change global defaults or claim an unavailable model switch.
For cross-provider routing, use the user's approximate tiers in
`skills/herd/SKILL.md` §2; they are a heuristic, not measured quality or price.

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

The operational lead, including a delegated Sol or Opus lead, owns shared
integration files, commits, PRs, and release actions. The
one exception is a `herd` execution contract that names explicit
caller-authorized release steps; the lead still approves and reviews them.
Workers must preserve pre-existing changes and must not change unrelated files.
Commits, merges and publishing are forbidden except for the explicit herd
contract steps above. A prompt's read-only instruction is not a sandbox;
use an actual read-only capability when the host offers one and disclose when
access control is only by instruction.

Use native wait/status and messaging, not log polling. Relay corrections,
interrupt stale work before reassigning files, and keep still-valid evidence.
Timeout, silence, and unavailable models are not success. Retry after a meaningful
change; otherwise complete the subtask locally or report its blocker. An explicit herd
request forbids taking over bulk work locally unless the user changes that requirement;
small integration fixes stay with the lead. Follow herd's escalation instead.

## 5. Acceptance and delivery

Wait for every required deliverable. Inspect worker changes and evidence against
the original acceptance criteria; a worker's "done" is not verification. Resolve
conflicts, then run the smallest relevant integration check on the combined result.
For plans/research, check evidence and consistency instead of inventing code tests.
An author may test, diagnose and fix their own work but cannot serve as its
independent reviewer. Match reviewers by canonical model, not provider, session,
version or effort: Opus cannot review Opus. Independent review is required
whenever lead and worker share a canonical model. When review is required,
each substantive part of mixed-model work needs coverage by a different model
from its author; lead-authored changes need it too. Record each author's and reviewer's canonical model
and requested/observed identity. Unknown or conflicting canonical routing
identity leaves required independence unverified. A host-controlled selection
record plus runtime label where exposed is configured routing evidence, not
provider-serving attestation (see `skills/herd/references/herdr-cli.md`).
Keep any caller's required review seats unchanged.

End with the outcome, actual agent/model/effort selections supported by tool
results (label requested-only settings), verification, and unresolved items.
Stop/close unused workers with the host's supported controls. If called inside
`execute-plan`, return to its delivery steps; standalone orchestration inherits
the user's task and does not grant separate merge or deployment authority.

## Sources

Checked 2026-09-28: [official subagents guide](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Codex model and effort guidance](https://learn.chatgpt.com/docs/models), and
[GPT-6 Sol model page](https://developers.openai.com/api/docs/models/gpt-6-sol).
The role suggestions above are cstack policy; validate speed/quality on real tasks.
