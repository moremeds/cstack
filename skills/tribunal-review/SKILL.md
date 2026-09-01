---
name: tribunal-review
description: Cross-runtime adversarial review. Whichever agent runs this skill orchestrates; the other frontier CLIs (Codex, Claude, Cursor/Grok, Gemini) review independently, findings merge by weighted consensus, contested items go through debate + rebuttal. Accepts a focus parameter to steer emphasis. Use when the user asks for a tribunal review, a cross-model second opinion, or invokes /tribunal-review. Also the tribunal engine behind /review-cycle Pass 2.
---

# Tribunal Review

Four seats, one verdict. You are the orchestrator **and** a voting reviewer.

**Why cross-runtime:** two instances of the same model share the same blind spots.
A finding that survives independent Codex, Claude, Cursor/Grok, and Gemini seats
is real. A finding only one raises is a hypothesis that must survive debate.

## Step 0 — Identify yourself and build the panel

Determine which runtime you are, then the panel is everyone else:

| You are | Your peer (1.0) | Cross-lineage (0.95) | Advisor (0.5) |
| --- | --- | --- | --- |
| **Claude Code** | Codex — `codex exec -s read-only` | Cursor/Grok — `cursor-agent -p` | Gemini — `gemini -p` |
| **Codex** | Claude — `claude -p` | Cursor/Grok — `cursor-agent -p` | Gemini — `gemini -p` |
| **Gemini** | you do not orchestrate — stop and tell the user to run this from Claude or Codex | — | — |

**Cursor/Grok is a panelist in every runtime**, and that is the point. It runs
Grok 4.6 — a different model lineage from every other seat on the panel, which
is the whole premise of this skill: two instances of the same model share blind
spots. When Gemini's probe fails, Cursor/Grok still supplies an independent
cross-lineage vote; when Gemini answers, both seats participate.

**The probe result is the source of truth.** A restrictive Codex seatbelt can
block the macOS Keychain and make Claude and Cursor/Grok fail together, while a
Codex runtime without that seatbelt can run both. Do not infer availability from
the orchestrator name or an older measurement: probe the exact launch command,
then include or drop each seat from that result.

**Probe, don't just `which`.** A CLI can be installed and still unusable —
logged out, unlicensed, or rate-limited. `which gemini` succeeding proves
nothing. Send each peer a one-token liveness prompt and check the _reply_:

```bash
gemini --skip-trust --approval-mode plan -o text -p "Reply with exactly: OK"
codex exec -s read-only --skip-git-repo-check "Reply with exactly: OK"
env -u ANTHROPIC_API_KEY claude -p --restricted --strict-mcp-config "Reply with exactly: OK"
cursor-agent -p --trust --mode ask --model cursor-grok-4.6-high --output-format text "Reply with exactly: OK"
```

Non-zero exit or no `OK` → that reviewer is unavailable. Read its stderr once and
say which reason in the output header (`gemini: unlicensed`), so the user can fix
it if they want to; then carry on without it. Never retry a failed probe more than
once, and never let one block the review.

| Panel available | Mode                                                                      |
| --------------- | ------------------------------------------------------------------------- |
| peer + Cursor + Gemini | full tribunal (4-way weighted)                                     |
| any two of the three   | weighted panel at whatever weights answered                        |
| exactly one            | bilateral (you + it); if it is Gemini alone, promote it to 1.0      |
| none                   | solo review — say so loudly in the output header, do not silently pretend |

**No panelist is required.** An absence changes the weights, never the output shape,
and never blocks the run. Name every seat that did not answer, and why, in the
output header — a 2-way panel reported as a tribunal is the failure this skill
exists to prevent.

## Step 1 — Parse arguments

```
/tribunal-review [target] [quick|deep|solo] [focus: <free text>]
```

**Target** (first tokens; if omitted, auto-detect in this order — uncommitted changes → open PR → today's plan file → ask):

| Form              | Meaning                       |
| ----------------- | ----------------------------- |
| `--diff`          | staged + unstaged + untracked |
| `--base <branch>` | changes vs. a base branch     |
| `--pr [N]`        | current or numbered PR        |
| `--plan <path>`   | review a plan/design doc      |
| `--prose <path>`  | review docs/book/article prose |
| `<path> [path…]`  | review specific files         |

For code targets, record this parse as `TARGET_KIND=diff|base|pr`, plus
`BASE_REF` or `PR_NUMBER` when applicable. Step 2 uses those values to choose
exactly one payload path.

Every target resolves to one of **three review classes**, and the class decides
which question set, severity scale, and sweep the reviewers get
(`prompts/review.md` carries one block per class — include only the matching one):

| Class | Targets | Reviewing for |
| --- | --- | --- |
| **code** | `--diff`, `--pr`, `--base`, code paths | defects in what was built |
| **plan** | `--plan`, doc/spec paths (`.md` and friends) | defects in what is ABOUT to be built — reality mismatches, contradictions, ambiguity, missing risks, unverifiable acceptance criteria, speculative scope |
| **prose** | `--prose`, or a doc that no code is built from (book chapter, article, reference page) | defects in what a reader will believe — false claims, unsupported assertions, contradictions, missing steps in an argument |

Pick the class by what the document is FOR, not by its extension. **plan** =
it directs implementation that has not happened yet; **prose** = it is
reader-facing material whose defect is a false belief, not a wrong build. A
`README.md` is prose; a design doc is plan. Folding prose into `plan` is the
costly mistake: the plan class puts prose style on its DO-NOT-FLAG list, so it
suppresses the findings a prose review exists to produce. A target that is
genuinely both (a PR touching code and reader docs) is two reviews, not one
blended class.

A plan's defects are cheaper to fix than the same defects after they become
code — so a plan review that only polishes prose is a wasted tribunal. The
grounding rule still applies: reviewers open every file the plan references and
check the plan's assumptions against the real code.

**Modifiers:**

| Token   | Effect                                                                                             |
| ------- | -------------------------------------------------------------------------------------------------- |
| `quick` | Phase 1 + merge only. No debate, no rebuttal. For small diffs and doc touch-ups                    |
| `deep`  | raise reasoning budget: `-c model_reasoning_effort=high` for Codex; for Gemini pass `-m` ONLY with a model id confirmed on this machine — an unknown id does not error, it silently degrades to weaker output |
| `solo`  | skip external CLIs entirely, orchestrator-only review (still uses the output format)               |

**`focus:` — everything after the literal token `focus:` is user emphasis.**
Also accept bare trailing prose as focus when it clearly isn't a path.

Focus semantics — get these exactly right, they are the point of the parameter:

1. **Inject verbatim** into every reviewer prompt inside the `=== FOCUS ===` block. Do not paraphrase it, do not translate it, do not "improve" it.
2. Reviewers **lead** with focus-area findings, then report everything else.
3. Focus **raises attention, never suppresses**. A CRITICAL outside the focus area is still reported at CRITICAL. Focus is a sort order and an attention budget, not a filter.
4. In the final output, focus findings come first under a `Focus: <text>` sub-heading.
5. No focus given → omit the `=== FOCUS ===` block entirely rather than sending an empty one.

Examples:

```
/tribunal-review focus: the ndx/rut fallback path
/tribunal-review --pr 42 deep focus: 并发安全和资金计算精度
/tribunal-review --plan docs/plans/2026-09-01-x.md quick focus: is the migration reversible
/tribunal-review src/pipeline.py src/loader.py focus: error handling on partial reads
```

## Step 2 — Prepare the workspace

```bash
SP="${CLAUDE_SCRATCHPAD:-$(mktemp -d)}/tribunal"   # never /tmp/*.txt globs
mkdir -p "$SP"
```

Write every prompt to a file under `$SP` and feed it on **stdin** (`… - < "$SP/prompt.md"`).
Never interpolate a prompt through `$(cat …)` — shell escaping mangles code blocks.

Build the target payload once, into `$SP/target.diff` or `$SP/target.md`. Resolve
the checkout once, then choose exactly one tracked-file path. The merge-base
path keeps base-only commits out while still folding committed, staged, and
unstaged branch changes into one coherent patch:

```bash
REPO_OR_WORKTREE="${REPO_OR_WORKTREE:-$(git rev-parse --show-toplevel)}"
case "$TARGET_KIND" in
  diff)
    git -C "$REPO_OR_WORKTREE" --no-pager diff HEAD > "$SP/target.diff"
    ;;
  base)
    MERGE_BASE=$(git -C "$REPO_OR_WORKTREE" merge-base "$BASE_REF" HEAD)
    git -C "$REPO_OR_WORKTREE" --no-pager diff "$MERGE_BASE" > "$SP/target.diff"
    ;;
  pr)
    (cd "$REPO_OR_WORKTREE" && gh pr diff "$PR_NUMBER") > "$SP/target.diff"
    ;;
esac

# Local targets also include untracked contents. Never append them to --pr.
if [ "$TARGET_KIND" != "pr" ]; then
  git -C "$REPO_OR_WORKTREE" ls-files --others --exclude-standard -z \
    > "$SP/untracked.zlist"
  while IFS= read -r -d '' UNTRACKED_FILE; do
    git -C "$REPO_OR_WORKTREE" --no-pager diff --no-index -- \
      /dev/null "$UNTRACKED_FILE" >> "$SP/target.diff" || {
        DIFF_STATUS=$?
        [ "$DIFF_STATUS" -eq 1 ] || exit "$DIFF_STATUS"
      }
  done < "$SP/untracked.zlist"
fi
wc -l "$SP/target.diff"
```

### Context per reviewer

| Reviewer           | Give it                                                                                                                                                              |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Codex              | the diff + the enclosing functions of every hunk. Top 20 files by change size                                                                                        |
| Gemini             | the diff + **complete** contents of every touched file + their imports + the tests + CLAUDE.md/AGENTS.md. Up to 50 files — its value is seeing more, so feed it more |
| Claude             | the diff; it reads the rest itself via Read/Grep/Glob                                                                                                                |
| Cursor/Grok        | the diff + the touched paths; `--workspace` lets it open the real files itself (measured: it read a named file and counted matches in it correctly)                  |
| Plan targets (all reviewers) | the full plan + a list of every path it references, with the instruction to open them and verify the plan's assumptions |
| You (orchestrator) | full repo access via your own tools                                                                                                                                  |

Never send a bare 3-line hunk with no surrounding function. That is the single
biggest source of false positives. And the diff is the *anchor*, not the whole
story: Codex and Claude both run read-only **inside the repo**, so their prompts
list the touched file paths and tell them to open the real files — grounding
findings in actual signatures and tests instead of the diff's claims about
itself is the single biggest quality lever.

Diffs beyond ~500 changed lines degrade every reviewer sharply — models fall
back to surface pattern-matching. Split by subsystem and run the tribunal per
chunk (or prioritize and say in the header what was excluded).

## Step 3 — Launch the panel in parallel, in the background

All panelists are independent. Launch them **backgrounded** and do your own review
while they run. Launch only peer seats whose Step 0 probe passed — never launch
the orchestrator's own CLI as a duplicate reviewer — append each captured PID
to `PANEL_PIDS`, and do not block the session waiting.

**Codex:** execute this entire block as one persistent exec session. Do not split
launch and collection across shell invocations: the PID array and `SECONDS`
deadline are shell state. While that session runs, perform your own review with
native tools, then return to the same session to collect it.

```bash
PANEL_PIDS=()
PANEL_DEADLINE=$((SECONDS + 900))

# --- Codex ---------------------------------------------------------------
# Use `codex exec`, NOT `codex exec review`. See the note below — `review`
# cannot take your prompt, so it cannot carry the focus or the output format.
# Embed the diff in the prompt file; `-` reads it from stdin.
env -u ALL_PROXY -u HTTP_PROXY -u HTTPS_PROXY \
    -u all_proxy -u http_proxy -u https_proxy \
  codex exec -s read-only -C "$REPO_OR_WORKTREE" --skip-git-repo-check \
    -o "$SP/codex.txt" - < "$SP/prompt-codex.md" > "$SP/codex.log" 2>&1 &
CODEX_PID=$!
PANEL_PIDS+=("$CODEX_PID")

# --- Gemini --------------------------------------------------------------
# --skip-trust is REQUIRED headless; without it every run dies on the trust dialog.
# -p is what selects headless mode; per `gemini --help` it is APPENDED to stdin,
# so send the bulk (diff + files) on stdin and keep -p short. That avoids the
# $(cat …) escaping trap. Unverified on this machine — Gemini is unlicensed here;
# if stdin turns out to be ignored, fall back to -p "$(cat "$SP/prompt-gemini.md")".
gemini --skip-trust --approval-mode plan -o text \
  -p "Review the material above per the instructions it contains." \
  < "$SP/prompt-gemini.md" > "$SP/gemini.txt" 2>"$SP/gemini.log" &
GEMINI_PID=$!
PANEL_PIDS+=("$GEMINI_PID")

# --- Cursor / Grok 4.6 ---------------------------------------------------
# Measured on cursor-agent 2026.08.11, prompt "create /tmp/x then say DONE":
#   (no mode flag)      → file CREATED. `-p`'s own --help says it "has access to
#     all tools, including write and shell". The published docs claim that
#     without --force "changes are only proposed, not applied" — that is FALSE
#     for file creation. Do not rely on it.
#   --sandbox enabled   → file CREATED. Not a write guard for paths like /tmp.
#   --mode ask          → file NOT created; it answered that it can only give
#     guidance in this mode. This is the one that holds. `--mode plan` is also
#     read-only if you want planning-shaped output instead of Q&A.
# --trust is REQUIRED headless, exactly like Gemini's --skip-trust: without it
# every run dies on the workspace-trust dialog with exit 1 and no output.
# stdin works (verified), so the diff goes on stdin like everyone else's.
cursor-agent -p --trust --mode ask --model cursor-grok-4.6-high \
    --output-format text --workspace "$REPO_OR_WORKTREE" \
    < "$SP/prompt-cursor.md" > "$SP/cursor.txt" 2>"$SP/cursor.log" &
CURSOR_PID=$!
PANEL_PIDS+=("$CURSOR_PID")

# --- Claude (when Codex is the orchestrator) -----------------------------
# Two traps, both verified:
#  1. --allowedTools is VARIADIC and swallows a trailing positional prompt
#     ("Input must be provided either through stdin or as a prompt argument").
#     Always pipe the prompt on stdin.
#  2. ANTHROPIC_API_KEY takes precedence over the claude.ai login and can fail
#     with "Credit balance is too low". Unset it so the subscription login wins.
#  3. A restrictive Codex seatbelt can block the macOS Keychain, while other
#     Codex permission profiles allow this command. The exact Step 0 probe is
#     authoritative; never predict availability from the orchestrator name.
#  4. NOT --permission-mode plan, and NOT --allowedTools as a guard. Measured on
#     claude 2.1.252, prompt "create /tmp/x then say DONE":
#       --allowedTools Read,Grep,Glob            → file CREATED. allowedTools is
#         an auto-approve list, not a deny list.
#       --disallowedTools Write,Edit,Bash        → file CREATED. The peer routed
#         around it through an MCP server's execute_shell_command, and
#         registered a new project as a further side effect.
#       --permission-mode plan                   → blocked, but wrote a plan file
#         into ~/.claude/plans/ and returned "Approve the plan…" instead of the
#         review. On a review-shaped prompt it usually answers normally; on an
#         analysis-shaped one it does not, and the report is lost.
#       --restricted --strict-mcp-config         → blocked, no plan file, review
#         returned intact. This is the one that holds.
#     --restricted also drops Bash and ignores user/project settings, so the peer
#     gets no hooks and no shell. That is why Step 2 embeds the diff in the
#     prompt: Read/Grep/Glob plus --add-dir is the whole context budget.
#     ("MultiEdit" is not a known tool name — naming it only prints a warning.)
env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
  claude -p --restricted --strict-mcp-config \
    --disallowedTools "Write,Edit,NotebookEdit" \
    --allowedTools Read,Grep,Glob \
    --add-dir "$REPO_OR_WORKTREE" \
    < "$SP/prompt-claude.md" > "$SP/claude.txt" 2>"$SP/claude.log" &
CLAUDE_PID=$!
PANEL_PIDS+=("$CLAUDE_PID")

# --- then do YOUR OWN review, and only afterwards collect ------------------
# … your own review happens here …

# Enforce the launch-time deadline across the panel. Poll only the captured
# PIDs; never poll output files and never use a process-name pattern.
while :; do
  LIVE_PIDS=()
  for PANEL_PID in "${PANEL_PIDS[@]}"; do
    kill -0 "$PANEL_PID" 2>/dev/null && LIVE_PIDS+=("$PANEL_PID")
  done
  ((${#LIVE_PIDS[@]} == 0)) && break
  if ((SECONDS >= PANEL_DEADLINE)); then
    kill "${LIVE_PIDS[@]}" 2>/dev/null || true
    sleep 2
    for PANEL_PID in "${LIVE_PIDS[@]}"; do
      kill -0 "$PANEL_PID" 2>/dev/null && kill -KILL "$PANEL_PID" 2>/dev/null || true
    done
    break
  fi
  sleep 5
done
for PANEL_PID in "${PANEL_PIDS[@]}"; do
  wait "$PANEL_PID" || true
done
```

**The trailing `&` is not decorative.** Without it the block runs serially: Codex
blocks Gemini, which blocks Claude, which blocks your own review — and the whole
point of the panel is that its members are independent. Keep each PID; you need
them to stop a stalled run without killing anything else.

If your harness gives you a background-task primitive (Claude Code's
`run_in_background`), use that instead of `&`, track only its task IDs, and
cancel unfinished tasks at the same 15-minute deadline — same rule, same reason.

Add `deep` flags when requested: `-c model_reasoning_effort=high` (Codex),
`--model cursor-grok-4.6-xhigh` (Cursor), `-m gemini-2.5-pro` (Gemini).
Verify a Cursor model id against `cursor-agent --list-models` before using it —
`cursor-grok-4.6-high` and `-xhigh` were confirmed present on this machine.

### Why not `codex exec review`

`codex exec review`'s scope flags are **mutually exclusive with a custom prompt**:

```
$ codex exec review --base master "my instructions"
error: the argument '--base <BRANCH>' cannot be used with '[PROMPT]'
```

Same for `--uncommitted` and `--commit`, and stdin (`-`) counts as a prompt. So
`codex exec review --base X` runs Codex's own built-in review prompt and nothing
else — it cannot carry the focus text, the specialty preamble, or the `ISSUE-N`
output format this skill merges on. It also has no `-C/--cd` and no `-s/--sandbox`.

Use `codex exec -s read-only` and put the diff in your prompt. `codex exec review`
is only useful as a standalone one-shot outside this skill.

**While they run:** do your own review with your native tools. You are a voting
reviewer, not just a judge — produce your own issue list in the same format
before you look at anyone else's. Reading theirs first anchors you.

Prompt template: `prompts/review.md`.

### Reviewer specialties

Each reviewer reports **all** issues; the specialty only directs attention.

**Every reviewer additionally runs the over-engineering sweep** — a mandatory,
explicit hunt for what to DELETE (speculative abstractions, one-implementation
interfaces, config for constants, dependencies replacing a few plain lines,
layers that only forward). The review prompt forces a verdict either way: an
`OVER-ENGINEERING SWEEP: clean` line, or findings tagged
`Category: over-engineering`. Silence is scored as "did not check". This exists
because reviewers are structurally biased toward addition — a missed bug looks
like reviewer failure, a missed deletion looks like nothing.

For **plan-class** targets the same specialties re-aim: Codex → can each step
actually be implemented as written; Gemini → cross-section consistency and
contradictions across the whole document; Claude/orchestrator → does the repo's
reality match the plan's assumptions. The sweep re-aims too: deletion means
cutting speculative scope from the plan.

| Reviewer | Lead with                                                                                      |
| -------- | ---------------------------------------------------------------------------------------------- |
| Codex    | BUG DETECTION — edge cases, off-by-one, null/undefined, races, boundary failures               |
| Gemini   | CROSS-FILE CONSISTENCY — API contract drift, import graph, dead code, pattern violations       |
| Claude   | INTEGRATION CORRECTNESS — call-site impact, test coverage gaps, CLAUDE.md/AGENTS.md compliance |
| Cursor/Grok | PREMISE ATTACK — is the approach itself wrong? What did everyone accept without checking: the assumption the change is built on, the requirement nobody questioned, the simpler design that was never considered |

## Step 4 — Merge

Deduplicate by `file:line + intent`, not by wording. Same root cause surfaced two
ways = one issue citing both. Severity disagreement = take the highest, note it.

| Agreement                 | Weight         | Route                  |
| ------------------------- | -------------- | ---------------------- |
| all four                     | 3.45 UNANIMOUS | consensus              |
| both trusted (you + peer)    | 2.0 STRONG     | consensus              |
| one trusted + Cursor/Grok    | 1.95 STRONG    | consensus              |
| one trusted + Gemini         | 1.5 SUFFICIENT | consensus              |
| Cursor/Grok + Gemini         | 1.45 SUFFICIENT| consensus              |
| one trusted alone            | 1.0            | **contested** → debate |
| Cursor/Grok alone            | 0.95           | **contested** → debate |
| Gemini alone                 | 0.5            | **contested** → debate |

Cursor/Grok sits at **0.95 deliberately**, not 1.0: near-peer, but never able to
do alone what a trusted reviewer does alone. Pair it with anyone and the pair
clears consensus; leave it alone and it argues its case like any single voice.

Confidence filter, applied **after** dedup and **before** debate:

- any reporter scored ≥70 → keep, use the highest score
- all reporters <70 → auto-dismiss into the Low Confidence list
- weight **≥1.95** bypasses this filter — agreement between two near-full-weight
  reviewers is itself the evidence. One trusted + Gemini (1.5) does not bypass.

Weight measures trust in the reviewer; confidence measures certainty about the
issue. They are independent. A Gemini-only issue at confidence 95 still goes to
debate; a unanimous issue at confidence 40 skips the filter.

**Verify before you promote anything to consensus.** Open the file and read the
cited lines. Models hallucinate paths and line numbers. An issue whose cited code
does not exist is dismissed as HALLUCINATED, no debate.

Two more triage rules, both from measured failure modes:

- **Minimal-fix bias.** A useful finding names a small flaw in an otherwise sound
  artifact; a harmful one amounts to "rewrite this working thing my way" — in a
  controlled Claude/Codex experiment (arXiv 2607.21656), rewrite-scale review
  suggestions were what turned passing drafts into failing ones. A finding whose
  resolution is a rework of working code needs the strongest evidence, not the
  usual bar. **Deletion is exempt**: removing unused flexibility is the smallest
  possible diff, not a rewrite — minimal-fix bias must never shield bloat.
  **And the bar is class-asymmetric**: it protects working CODE, where a rewrite
  risks breaking what runs. A plan is the cheapest place it will ever be to
  change the approach — structural findings against a plan get the normal
  evidence bar, not the elevated one. Do not import code-review caution into
  plan review; that is how a wrong approach survives to become working code
  nobody dares restructure.
- **Inverted burden for over-engineering.** In debate, added structure must
  justify itself by naming a concrete current caller or requirement;
  "might need it later" / "more flexible" / "best practice" score as conceding
  the deletion. Symmetrically, a deletion claim must name nothing that breaks
  today — if something does, the structure stands.
- **Boundary owner.** If the correct fix lives outside the reviewed code (the
  server API this client consumes, another service's schema), record the finding
  under its own `Out of scope — owner: <where>` heading and exclude it from the
  verdict. Do not let reviewers push client-side workarounds for server-side
  defects into consensus.

## Step 5 — Debate, then rebuttal (skip on `quick`)

Two structurally different exchanges. One without the other is theatre.

**A. Debate — attack.** Send each contested issue with all positions to every panelist.
Ask for counter-evidence and an attack vector, not a vote. (`prompts/debate.md`)

**B. Rebuttal — defend or concede.** Send the challenges back to the original
position holder. New evidence, or concession. (`prompts/rebuttal.md`)

**C. Judge.** Repeating the original argument **is** a concession — score it as one.
A concession removes that reviewer's weight from their side. Recompute:
final weight ≥1.5 → consensus (note the debate trail); below → unresolved, escalate
to the user with the transcript.

Run debate and rebuttal for all contested items in one batched call each — not one
call per issue.

## Step 6 — Output

```markdown
## Tribunal Review — <target>

**Verdict:** APPROVE | CHANGES NEEDED (N consensus findings, worst: SEVERITY)
**Panel:** <answered seats and weights, including Cursor/Grok when it answered> · Missing: <seat: reason, or none> · <mode>
**Focus:** <verbatim focus text, or "none">

### Consensus (N)

#### Focus: <focus text> ← omit this sub-heading when no focus given

- **[CRITICAL]** `file:line` — Title
  Category: bug | Agreement: unanimous (3.45) | Confidence: 92
  Raised by: Codex, Claude, Cursor/Grok, Gemini
  Evidence: <the actual code, verified by you>
  Resolution: <concrete fix>

#### Simplification — delete list
Over-engineering consensus items, grouped so the deletions are visible as a
set, not scattered among bugs:
- **[IMPORTANT]** `file:line` — interface with one implementation; inline it
  …

#### Other findings

- **[IMPORTANT]** `file:line` — Title
  …

### Unresolved (N) — your call

- **Issue:** …
  - Opening positions: Peer (1.0) … | Cursor/Grok (0.95) … | Gemini (0.5) … | You (1.0) …
  - Challenges that landed: …
  - Rebuttal outcome: who conceded, who defended, on what new evidence
  - **Recommendation:** <your own call, stated plainly>

### Dismissed

- Low confidence (N): `file:line` — … (raised by X, max conf 55)
- Refuted in debate (N): `file:line` — … (conceded by X)
- Hallucinated (N): `file:line` — cited code does not exist (raised by X)

### Stats

Raised: N (<answered reviewer counts only: Codex a / Claude b / Cursor/Grok c / Gemini d / You e>) · Unanimous U · Strong S · Sufficient M
Unresolved Y · Dismissed F+G+H · Debate: <ran | skipped (quick) | skipped (all consensus)>
Over-engineering sweep: <per reviewer — findings | clean | MISSING (did not check)>
```

## Failure handling

Degrade, never block. 4-way → 3-way → 2-way → solo, always with a header saying which.

| Failure                             | Do                                                                                                         |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| a CLI is missing                    | drop it from the panel, note it in the header                                                              |
| Gemini dies on trust                | you forgot `--skip-trust`. Retry once with it                                                              |
| Gemini: "no valid license"          | installed but not entitled. Drop it, note `gemini: unlicensed` in the header, move on                      |
| Cursor: `ERROR: SecItemCopyMatching failed -50` | The active sandbox blocked the Keychain. `CURSOR_API_KEY` may sidestep it (unverified — probe it, do not assume). Otherwise drop the seat and name it in the header; do not generalize the result to every Codex runtime |
| Cursor: "⚠ Workspace Trust Required", exit 1, no output | `--trust` is missing. Headless runs cannot answer the dialog. Same class as Gemini's `--skip-trust` |
| Cursor wrote a file during review | `--mode ask` (or `--mode plan`) was missing. `-p` alone has write and shell access — its own `--help` says so, and the published docs' "without `--force` changes are only proposed" is false for file creation. `--sandbox enabled` does not stop it either |
| Cursor: unknown model id | it does not error usefully — check `cursor-agent --list-models` first. An id that looks right but is not present degrades the review silently, exactly like Gemini's `-m` |
| Codex hangs on network              | retry once with the `env -u *_PROXY` prefix                                                                |
| Claude: "Credit balance is too low" | `ANTHROPIC_API_KEY` is overriding the claude.ai login. Retry with `env -u ANTHROPIC_API_KEY`               |
| Claude: "Not logged in · Please run /login" | The active sandbox may be blocking the Keychain. Do not retry the same command repeatedly; drop the seat and report the probe result. Changing sandbox or credentials requires the user's explicit choice |
| Claude: "Input must be provided…"   | `--allowedTools` ate your positional prompt. Pipe it on stdin instead                                      |
| Claude returns "Approve the plan…" instead of a review, and a file appears in `~/.claude/plans/` | You used `--permission-mode plan`. It is a real read-only guard but it persists a plan and can swallow the report. Use `--restricted --strict-mcp-config` (Step 3, note 4) |
| Claude wrote a file despite `--allowedTools` / `--disallowedTools` | Neither flag is a sandbox — `--allowedTools` only auto-approves, and an MCP server's shell tool routes around a deny list. Only `--restricted --strict-mcp-config` held in testing |
| a run reaches the 15-minute deadline | The Step 3 deadline kills only captured live PIDs. Keep partial output, mark the seat missing, and continue. **Never `pkill -f 'codex exec'`**: it matches the user's other Codex jobs |
| non-zero exit                       | keep the `.log`, parse whatever landed in the `.txt`, continue                                             |
| unparseable output                  | flag the unparseable section, do not silently drop it                                                      |
| >50 changed files                   | prioritize by change size; say in the header what was excluded                                             |

## Cleanup

```bash
rm -rf "$SP"        # scoped to this run's dir — never a /tmp/*.txt glob
```

## Red flags — you're doing it wrong

- Blocking the session waiting on a CLI instead of backgrounding it and reviewing in parallel
- Skipping your own review and acting only as a judge — you are a voting reviewer
- Promoting a finding to consensus without opening the file and reading the cited lines
- Sending a bare hunk with no enclosing function, then believing the false positives
- Giving Gemini the same slim context as Codex — its whole value is seeing more
- Accepting a rebuttal that restates the original argument — that is a concession
- Debating issues that the confidence filter should already have dismissed
- Treating a focus parameter as a filter and hiding a CRITICAL because it was off-topic
- Paraphrasing the user's focus text instead of passing it through verbatim
- Promoting a "rewrite it this way" finding on the same evidence bar as a small-flaw finding
- Treating a reviewer's silence on over-engineering as a clean sweep — the explicit verdict line is required
- Letting "might need it later" survive debate as a defense of added structure
- Letting a cross-boundary finding (fix belongs to another service) drive the verdict
- Running the full tribunal on this skill's own files — use one plain `codex exec review` pass
