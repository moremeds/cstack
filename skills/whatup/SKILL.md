---
name: whatup
description: Plain-language status readout — what this work is for, what is happening right now, what actually got done, what failed, what breaks if we stop here, and what decision is waiting on you. Every claim carries the evidence it came from, or is marked unverified. Use when the user asks "status", "什么状态", "说人话现在是什么状态", "现在在做什么/什么还没做", or says the work feels out of control / off track.
---

## Runtime

Portable. The skill lives in the shared skills tree, so Claude Code and Codex
both see it; ask for it by name in either. It needs `git` and, when the work has
a PR, `gh` — a missing or failing `gh` is reported, never silently skipped.

## Why this exists

The user asks this by hand across every project, always at the same moment: the
agent has been running a while, the user has lost the thread, and they need to
know whether the work still serves the goal. (The frontmatter lists the phrasings
it is actually asked in.)

The trap: **a drifted agent narrates drift-free progress from memory**, and a
status ritual it performs privately does not stop that. So the rule here is not
"run some commands first" — it is that **every line of the readout carries the
evidence it came from, in the readout, where the user can see it.** A claim with
no evidence beside it is written as unverified. That is the whole mechanism; the
section list is just packaging.

## Argument (optional)

`whatup [scope]` — no arg → the current branch and the task in play.

| Scope                                 | Resolve it as                                                                                           |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `PR 92` / `#92`                       | that PR: `gh pr view 92 …` plus its branch                                                              |
| a path                                | that path's history, its dirty state, and the artifact it produces                                      |
| a phrase (`the gap autoheal feature`) | the plan/branch of that name; if you cannot map it to one, say so and report the current branch instead |

Answer in the language of the **conversation**, not of the invocation token —
`/whatup` typed in a Chinese session gets a Chinese answer.

## Step 1 — Ground yourself (before writing one word)

```bash
git status --short                        # every dirty file — do not truncate
git status -sb | head -1                  # branch, and [ahead N] when an upstream exists
git rev-parse --abbrev-ref '@{upstream}'  # fails ⇒ never pushed anywhere
git log --oneline -10
git diff --stat '@{upstream}...HEAD'      # what this work changed; drop the arg if there is no upstream
gh pr view --json number,state,statusCheckRollup,headRefName,url   # the PR for THIS branch
```

Three traps, all the same failure shape — **a command that reports "clean" when
it actually reported nothing**:

- **No `2>/dev/null` on `gh`.** Suppressed stderr makes "not logged in",
  "no network", and "no PR" identical — and they are not. Read the error:
  _no pull requests found for branch_ is a **fact**, report it as "no PR yet".
  Anything else (auth, network, `gh` missing) is **unverified — gh failed:
  <reason>**. Never let the second case print as the first.
- **`git status -sb` alone is not push state.** On a branch with no upstream it
  prints bare `## main` — no warning, no ahead count. Verified. That is why
  `@{upstream}` is queried separately: it failing _is_ the finding ("this work
  has never left the machine"). `origin/HEAD..HEAD` is not a substitute — that
  range means "not in the default branch", which is a different question.
- **Never pipe `git status --short` through `head`.** It silently drops files,
  and the readout has to name everything uncommitted.

Then, for whatever the readout will claim:

- the plan/spec this work follows — reread its **goal** and **acceptance
  criteria**, not your summary of them
- the artifact the work produces: does it exist on disk, non-empty, in the path
  the consumer actually reads?
- the test: quote the command and its exit code **from this session**, or from a
  log file on disk. Remembering a green run is not test evidence — the code may
  have changed since. No quote → `[unverified]`.
- anything the user already declared out of scope earlier in the session

**No repo, no plan, no PR** (ad-hoc task, scratch dir, conversation-only work):
the pass still runs — ground on the files actually written this session, real
command output, and the user's own words, and open by saying the state lives
only in this conversation. A missing repo never turns the answer back into memory.

**Evidence classes are not interchangeable.** A merged PR proves _merged_, not
deployed and not working. A passing test proves _the scenario that test covers_.
Only a real run in the real environment proves it works. Say which one you have.

## Step 1.5 — Check for narrative drift

Grounding fixes hallucination going forward; it says nothing about whether what
you (or the user) already believe about this work still matches. Before
writing the readout, scan back over this conversation for claims made earlier
— "done", "passing", "merged", a plan step marked complete — and compare each
against what Step 1 just verified.

Agreement needs no comment. A mismatch is the finding: state plainly what was
claimed, what the fresh evidence actually shows, and since when the two have
disagreed if that's determinable (a commit that reverted it, a test that
started failing). Put it in its own line — do not fold it quietly into section
3 or 4 as if it were just another status. A readout that silently reports the
corrected state without flagging that it _is_ a correction lets the earlier
false claim stand uncontested in the transcript.

No earlier claims in scope (cold start, first message) → skip this, say nothing.

## Step 2 — The readout

Write in the user's language. **Functional detail, not technical detail** — what
the system can and cannot do now, not which module was refactored. Name a file,
branch, or PR only where the user needs it to act. Aim for one screen.

**If the last few steps do not serve the goal, or Step 1.5 found a drift, that
is the opening sentence** — before section 1, not buried. Scope creep, a
detour into a bug that was not the task, a fourth detector where the goal was
consolidation, work on something the user deferred, or a claim that no longer
matches the fresh evidence: name it plainly, without defending it. A `whatup`
that always answers "on track" is worthless.

| #   | Section                     | Contents                                                                                                                                                                                                                                                                                                                                     |
| --- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **一句话 / One line**       | What this work is for, and what you are doing right now. If you cannot say the purpose in one sentence, that is the finding.                                                                                                                                                                                                                 |
| 2   | **为什么做**                | What is broken or missing without it — **quote the goal verbatim** from the user's own message or the plan, in one line. The quote is what lets the user catch a right-evidence-wrong-work answer without taking your word for anything. If neither source states a goal, write "the user has not said". Never invent a motivating incident. |
| 3   | **做完了什么**              | As capability, not commits: "the scan now sees symbols that never landed on disk", not "added a 65-line module". **One evidence phrase per row** — the test that covers it, the run that proved it, or `[unverified]`. Shipped-but-never-run belongs in row 4.                                                                               |
| 4   | **没做 / 失败了什么**       | What was attempted and did not work, and why, functionally. Code that exists but has never run in the real environment lives here — written ≠ done. Include the ugly numbers ("501 findings, 497 false positives, because …").                                                                                                               |
| 5   | **不做的代价 / 做完的收益** | Stop right here — what stays broken? Finish — what does the user get? Two or three lines. This is the section that lets the user kill the work, which is a legitimate outcome.                                                                                                                                                               |
| 6   | **需要你决定什么**          | At most two decisions, each with your recommendation and its reason. Nothing blocked → name the next step. State it; do not execute it in this invocation.                                                                                                                                                                                   |
| 7   | **分支 / PR 现状**          | Branch · pushed or never pushed · PR number and CI state (or _unverified — gh failed_) · what is uncommitted. The user has lost track of where the work physically lives.                                                                                                                                                                    |

## Rules

- **Evidence beside the claim, not behind it.** Every row in 3 and 4 carries the
  command, test, run, or PR it rests on. Anything else is `[unverified]`, and
  `[unverified]` is a normal thing to write, not a failure.
- **Failures are not footnotes.** If the main result of the last hour was a
  false-positive rate that invalidates the approach, that leads row 4.
- **Read-only.** `whatup` reports; it never fixes, commits, or pushes. If the
  user then says "ok, fix it", that is a new instruction.
- **Plain words, full rigor.** The standing rules require every claim to carry
  its basis. This readout satisfies that with something stronger than notation:
  the actual evidence sits beside the claim, and "verified / unverified / I don't
  know" replaces the tag vocabulary because the reader is a human who has lost the
  thread. Substituting the form, never dropping the requirement — a claim with no
  evidence and no `[unverified]` marker violates the same rule a missing tag would.
- **No praise, no reassurance.** The user invokes this precisely when they
  suspect a reassuring answer would be false.
- **A correction is not a status update.** If Step 1.5 found this session's
  own earlier claim disagreeing with the fresh evidence, say so explicitly —
  don't just print the corrected fact and let the earlier one quietly stand
  uncontested in the transcript.
