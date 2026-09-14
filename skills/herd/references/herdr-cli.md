# herdr CLI for `herd` — verified against herdr 0.9.0 on 2026-09-12

The installed binary is the authority. Re-run `herdr agent` and `herdr pane`
(bare group, no subcommand) after any `herdr update` and re-verify this file.
Subcommands are hyphenated: `send-keys`, `wait-output`; never the
underscored spellings.

## Gate

```bash
test "${HERDR_ENV:-}" = 1 || { echo "not inside herdr"; exit 1; }
herdr status | grep -q 'endpoint_compatible: yes'
```

## Discover

```bash
herdr agent list                       # initial discovery; JSON: .result.agents[] {agent, agent_status, pane_id, cwd}
herdr agent get <name|pane>            # one agent
herdr agent explain <name|pane>        # why herdr thinks it is in that state
herdr integration status               # which kinds report lifecycle natively
herdr machine list --json              # saved SSH profiles; empty is normal
```

After discovery, use the known worker name. For routine status, project the
JSON locally instead of returning unrelated pane metadata to the model:

```bash
set -o pipefail
herdr agent get implementer | jq '{name: .result.agent.name, status: .result.agent.agent_status, seq: .result.agent.state_change_seq, error: .error}'
```

Keep stderr and failure status visible. Rediscover if the worker is missing or
the topology changed. The sequence is a lifecycle hint, not a terminal-output
cursor; an unchanged value does not prove there is no new output.

States: `idle` | `working` | `blocked` | `done` | `unknown`. `idle` and
`done` both accept input. `unknown` proves nothing.

## Adopt or start

Adopt an idle agent that already exists (keeps its context):

```bash
herdr agent rename w3:p2 reviewer
```

Before adding a worker, inspect `herdr pane layout --current`: consider pane
count and dimensions, and preserve a readable main pane. Split only when space
permits. Otherwise use `herdr tab create --cwd <worktree> --no-focus` or
`herdr workspace create --cwd <worktree> --no-focus`, and discover the new pane
with `herdr pane list --workspace <workspace_id>`. If readability is uncertain,
use a separate tab. Check the resulting layout; if a split cramped the main
pane, move the worker with `herdr pane move <pane_id> --new-tab --no-focus`.
Moving preserves the running session; closing and recreating it does not.

Start a missing one in the selected pane, keeping the user's focus and cwd. The
worker runs interactively in that persistent pane; do not launch it through a
one-shot/headless CLI command. This applies on remote hosts too. The
new shell needs a moment to reach its prompt; `agent start` on a pane that is
not yet an available shell fails with `agent_pane_busy`, so wait for the
prompt first. Native flags from the roster's `args` go after `--`. This split
example applies only when the main pane will remain readable:

```bash
P=$(herdr pane split --current --direction right --cwd "$PWD" --no-focus | jq -r .result.pane.pane_id)
herdr pane wait-output "$P" --regex '[$%❯>]( .*)?$' --timeout 15000
herdr agent start implementer --kind devin --pane "$P" --timeout 60000 -- --model swe-2-max --permission-mode accept-edits --sandbox
herdr agent wait implementer --until idle --timeout 60000
```

For restricted tribunal reviewers, append `--add-dir <seat-input-dir>` to the
roster args at `herdr agent start`. This directory is prepared per review;
its path does not belong in the static roster. See tribunal's herd-panel reference.

All CLIs inject their rules at startup. After a bootstrap or rules change,
an adopted worker is running on the old rules. Keep its pane and context and
start a fresh worker pane with the updated rules and the same layout rule;
restart the existing session only when the user explicitly authorizes
discarding its context.

Remote workers: `herdr machine add <ssh-target> --label <name>` once (it
installs or checks herdr there and starts its server). Control commands run
on that host over SSH, not through `herdr --remote`, which attaches the TUI:

```bash
ssh <machine> 'export PATH=$HOME/.local/bin:/opt/homebrew/bin:$PATH; herdr agent list'
```

IDs and names are per server, so rediscover them there.

## Dispatch and wait

```bash
herdr agent prompt implementer "$(cat "$SP/assign-implementer.md")" --wait --timeout 1800000 &
```

`--wait` returns on the first settled `idle`/`done`/`blocked`. It returns
`agent_prompt_stalled` if no `working` activity is seen within five seconds
of submission; that does not prove the prompt was lost. Inspect before
resending. One known loss: a CLI's first-run welcome screen (seen with
Devin) swallows the first prompt; if `agent read` shows the welcome and an
empty input line, resend once.

Prefer the reverse-channel report below while doing independent work. If the
host supports background tool execution, let the wait remain pending there;
do not use repeated one-second waits and status reads to simulate polling.
Use a bounded wait when a status is needed. A timeout while still `working`
is not failure or permission to resend. On `done`, still read a short tail to
check for a hidden approval menu before concluding completion.

## Collect

```bash
herdr agent read implementer --source recent-unwrapped --lines 20
```

Read only for a blocked/ambiguous state or completion check. Start short;
expand to enough lines to understand the error or full approval question.
Never truncate a permission question into an automatic approval. Terminal
chrome and repeated history are not progress evidence. Use reported artifact
paths and targeted file reads for detailed review; retain the raw originals.

If more `--lines` reveals nothing (alternate screen), ask the worker to write
its full reply to a file under `$SP/` and answer with the path only, then
read the file. Fallback only; never request file output up front. Read-only
reviewers must instead repeat the complete response for lead-side collection.

## Reverse channel (worker → lead)

Every managed pane has `$HERDR_PANE_ID`. Put the lead's id in the assignment
as `LEAD_PANE`, and the worker reports without being polled. Same server
only: a worker on another machine cannot reach the lead's pane, so its
contract says to write the report line to a file and the lead collects it
with `--wait` plus `ssh <machine> cat <file>`.

```bash
herdr agent prompt $LEAD_PANE "herd-report implementer task 3: commit abc123, evidence docs/evidence/t3.md, no deviations"
```

The lead sees it as an ordinary prompt in its own pane. Use it for
per-task reports under the execution contract.

## blocked

`agent prompt` refuses with `agent_blocked` while a dialog is open. Then:

```bash
herdr agent get implementer
herdr agent read implementer --source recent-unwrapped --lines 20
```

For a prompt outside the task's existing authorization, show the dialog and
ask the user what to answer. When the execution contract already authorizes
that prompt, the lead answers without asking again
with `herdr agent send-keys implementer <key>`. Devin's menus are numbered
(`1` = approve once), so a pre-approved answer is `send-keys implementer 1 enter`.
For writers, translate the task's existing authorization into scoped permission
rules or answer matching prompts without asking the user again. Use Devin's
`--permission-mode accept-edits` when workspace edits are authorized; it does
not preapprove every shell command. Keep `auto` for read-only work. Reviewers
use their own restrictive mode, never an implementation bypass flag.

## Teardown

Apply herd's teardown check: retain contexts needed by an outstanding task,
fix, review or handoff. Once the lead has all necessary information, accepts
the handoff, and saves needed evidence, close panes created for this task with
`herdr pane close <pane_id>` if no concrete follow-up needs their context. No extra confirmation
is needed for that cleanup. Inspect state, unsaved work and pending requests
first; idle/timeout alone is insufficient. Do not close pre-existing/adopted
panes without explicit authority. Never stop the server.

## Safety (from herdr's own skill file, verbatim in spirit)

- `--no-focus` for background work; `--current` or explicit ids, never the
  focused pane.
- Never close panes, tabs, or workspaces you did not create.
- Never `herdr server stop` from a live session.
- A timeout does not prove non-delivery; do not blindly resend.
