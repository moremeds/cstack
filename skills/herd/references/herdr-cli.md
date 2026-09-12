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
herdr agent list                       # JSON: .result.agents[] {agent, agent_status, pane_id, cwd}
herdr agent get <name|pane>            # one agent
herdr agent explain <name|pane>        # why herdr thinks it is in that state
herdr integration status               # which kinds report lifecycle natively
herdr machine list --json              # saved SSH profiles; empty is normal
```

States: `idle` | `working` | `blocked` | `done` | `unknown`. `idle` and
`done` both accept input. `unknown` proves nothing.

## Adopt or start

Adopt an idle agent that already exists (keeps its context):

```bash
herdr agent rename w3:p2 reviewer
```

Start a missing one in a sibling pane, keeping the user's focus and cwd. The
new shell needs a moment to reach its prompt; `agent start` on a pane that is
not yet an available shell fails with `agent_pane_busy`, so wait for the
prompt first. Native flags from the roster's `args` go after `--`:

```bash
P=$(herdr pane split --current --direction right --cwd "$PWD" --no-focus | jq -r .result.pane.pane_id)
herdr pane wait-output "$P" --regex '[$%❯>] ?$' --timeout 15000
herdr agent start implementer --kind devin --pane "$P" --timeout 60000 -- --permission-mode auto
herdr agent wait implementer --until idle --timeout 60000
```

All CLIs inject their rules at startup. After a bootstrap or rules change,
an adopted worker is running on the old rules; restart it (close its pane
if you created it, or ask the user) rather than assuming it caught up.

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
resending.

## Collect

```bash
herdr agent read implementer --source recent-unwrapped --lines 200
```

If more `--lines` reveals nothing (alternate screen), ask the worker to write
its full reply to a file under `$SP/` and answer with the path only, then
read the file. Fallback only; never request file output up front.

## Reverse channel (worker → lead)

Every managed pane has `$HERDR_PANE_ID`. Put the lead's id in the assignment
as `LEAD_PANE`, and the worker reports without being polled:

```bash
herdr agent prompt $LEAD_PANE "herd-report implementer task 3: commit abc123, evidence docs/evidence/t3.md, no deviations"
```

The lead sees it as an ordinary prompt in its own pane. Use it for
per-task reports under the execution contract.

## blocked

`agent prompt` refuses with `agent_blocked` while a dialog is open. Then:

```bash
herdr agent get implementer
herdr agent read implementer --source recent-unwrapped --lines 80
```

Show the dialog to the user and ask the user what to answer. Only when the
execution contract pre-approves that exact prompt may the lead answer it
with `herdr agent send-keys implementer <key>`. Devin's menus are numbered
(`1` = approve once), so a pre-approved answer is `send-keys implementer 1 enter`.
Prefer starting the worker with the roster's approval flag so read-only
commands never block at all.

## Teardown

There is none. A worker pane holds context the next dispatch re-adopts by
name; the lead never runs `herdr pane close` on a worker. The verb exists
for the user's own tidying.

## Safety (from herdr's own skill file, verbatim in spirit)

- `--no-focus` for background work; `--current` or explicit ids, never the
  focused pane.
- Never close panes, tabs, or workspaces you did not create.
- Never `herdr server stop` from a live session.
- A timeout does not prove non-delivery; do not blindly resend.
