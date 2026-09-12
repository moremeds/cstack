# Execution contract for a `herd` worker

Paste this block, with the `<slots>` filled, at the top of the plan or
assignment the worker receives. Lifted from the livewire notify-rewrite
plan of 2026-09-12, generalized.

```text
## Execution contract — read before Task 0

You are worker `<name>` (kind `<kind>`), working in `<worktree path>`.
The lead is herdr pane `LEAD_PANE=<pane id>`.

1. Scope. Implement only the tasks in this plan, in order. Anything the
   plan does not name is out of scope; report it, do not do it.
2. Files. You own: <globs>. You never write: <globs, e.g. data lake,
   ledgers, production config>. If your CLI runs in bypass mode nothing
   will stop a write outside this list; the lead's diff check will, and
   the task is rejected whole.
2b. Ground truth. Facts this task depends on and how to fetch them, not
   the lead's summary of them: <e.g. `ssh macmini ls ~/.claude/projects`,
   `git -C <repo> log -1`, a fixture path>. Fetch before designing.
3. Environment. Commands run only in <allowed dirs>; temp files under
   <temp dir>. No network calls except <list|none>.
4. Evidence. Every task leaves `<evidence dir>/t<n>.md`, or appends a
   `## Task <n>` section to the plan's own evidence file when the plan names
   one, with the exact commands run, exit codes, and pasted output the
   reviewer can re-run. A worker on another machine writes it to <remote
   path>; the lead copies it into the repo's evidence dir before accepting,
   and acceptance is not valid until that copy exists.
5. Commits. One commit per task, message `task <n>: <plan title>`. No
   attribution trailers: no `Co-Authored-By`, no `Generated with`. Workers
   add these by default, so this rule is repeated in every dispatch and
   the gate rejects a commit that carries one.
6. Review gate. Stop after every task. Report with exactly one line:
   herd-report <worker> task <n>: commit <sha>, evidence <path>, deviations: <text|none>
   sent as: herdr agent prompt $LEAD_PANE "<that line>"
   Do not start the next task until the lead replies `herd-continue <n+1>`.
7. Rejections. If the lead replies `herd-reject <n>: <reason>`, fix on top
   with a new commit and report again; never rewrite or amend the rejected
   commit.
8. Blocked. You were started with read-only commands pre-approved. For any
   other permission prompt, stop and wait; the lead answers only prompts
   listed here: <pre-approved prompts, e.g. "edit files under src/">, and
   everything else goes to the user.
9. Deviations. Any step you could not do as written is a deviation. Name it
   in the report line; do not silently substitute.
```

Reviewer checklist (the lead runs this on every `herd-report`):

- commit maps to the plan task, nothing more
- evidence file commands are real and re-runnable; re-run one
- forbidden paths untouched (`git show --stat <sha>`)
- deviations either accepted in the reply or the task is rejected
