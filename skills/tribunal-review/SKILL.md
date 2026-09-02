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

| You are | Your peer (1.0) | Cross-lineage (0.90) | Advisor (0.5) |
| --- | --- | --- | --- |
| **Claude Code** | Codex — `codex exec -s read-only` | Cursor/Grok — `cursor-agent -p` | Gemini — `gemini -p` |
| **Codex** | Claude — `claude -p` | Cursor/Grok — `cursor-agent -p` | Gemini — `gemini -p` |
| **Gemini** | you do not orchestrate — stop and tell the user to run this from Claude or Codex | — | — |

**Cursor/Grok is a panelist in every runtime**, and that is the point. It runs
Grok 4.6 — a different model lineage from every other seat on the panel, which
is the whole premise of this skill: two instances of the same model share blind
spots. When Gemini is unavailable, Cursor/Grok still supplies an independent
cross-lineage vote; when Gemini answers, both seats participate.

**The launch is the probe.** A CLI can be installed and still unusable — logged
out, unlicensed, rate-limited, or blocked from the Keychain by the orchestrator's
own sandbox. `which gemini` succeeding proves nothing, and neither does the
orchestrator's name or an older measurement. So do not run a separate liveness
round: **launch every seat except your own CLI, and let the launch answer the
question.** It runs the exact command, prompt, sandbox and repo the review needs
— which a probe can only approximate — and it costs nothing extra, where a probe
round cost a full model call and 15–30s per seat before the panel even started.

A seat is **unavailable** when its `.txt` is empty or absent at collection. Read
its `.log` once, name the reason in the output header (`gemini: unlicensed`), and
carry on without it. Never retry a failed seat more than once, and never let one
block the review. Panel composition is therefore known at Step 4, not up front —
the weights are applied at merge time anyway.

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

Record the rest of the parse as shell variables too — Step 3's assembler reads
them, so parsing once here is what keeps the prompt text out of your context:
`TARGET_CLASS=code|plan|prose` (the class table below), `FOCUS` (the verbatim
focus text, empty when none was given), and `REVIEW_MODE` (a short label for the
prompt header, e.g. `branch diff vs main`, `PR 42`, `plan docs/plans/x.md`).

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

Source the direct transport and check its credentials now. Debate and rebuttal
run through it, and a credential that is missing there must kill the run before
the panel spends three CLI spawns discovering it.

```bash
for D in ~/.agents/skills ~/.claude/skills ~/.codex/skills; do
  [ -f "$D/tribunal-review/panel/direct.sh" ] && . "$D/tribunal-review/panel/direct.sh" && break
done
direct_preflight || exit 1   # a missing credential dies here, not mid-debate
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
while they run. Launch every peer seat — never the orchestrator's own CLI as a
duplicate reviewer, and never a preliminary liveness round: a seat that cannot
run fails here, and Step 4 classifies it. Append each captured PID to
`PANEL_PIDS`, and do not block the session waiting.

**Codex:** execute this entire block as one persistent exec session. Do not split
launch and collection across shell invocations: the PID array and `SECONDS`
deadline are shell state. While that session runs, perform your own review with
native tools, then return to the same session to collect it.

### Build the prompts with the assembler, never by hand

`prompts/assemble.py` substitutes the template and keeps only the review block
and severity scale matching `TARGET_CLASS`. Reading `review.md` and re-emitting
it in a heredoc puts ~10KB into your context that every later call re-reads, and
it drifts from the template. Call the script.

```bash
for D in ~/.agents/skills ~/.claude/skills ~/.codex/skills; do
  [ -f "$D/tribunal-review/prompts/assemble.py" ] && TR="$D/tribunal-review" && break
done
assemble() {   # assemble <reviewer> <specialty> <content-file> <out-file>
  python3 "$TR/prompts/assemble.py" --class "$TARGET_CLASS" --mode "$REVIEW_MODE" \
    --focus "$FOCUS" --reviewer "$1" --specialty "$2" --content "$3" > "$4"
}

# Specialty strings come from the "Reviewer specialties" table below, verbatim.
assemble Codex  "BUG DETECTION — …"  "$SP/target.diff"       "$SP/prompt-codex.md"
assemble Cursor "PREMISE ATTACK — …" "$SP/content-cursor.md" "$SP/prompt-cursor.md"
```

Extra context per the Step 2 table goes into the `--content` file
(`cat "$SP/target.diff" "$SP/paths.txt" > "$SP/content-cursor.md"`); project
context and standing rules go via `--context-file` / `--standards-file` — never
as text you retyped.

**Flag rationale lives in `references/panel-cli-notes.md`.** Read it only when a
seat fails to launch or you are about to change a flag below — every flag in the
block was measured, and the measurements are why they are not negotiable.

```bash
PANEL_PIDS=()
PANEL_DEADLINE=$((SECONDS + 900))

# --- Codex ---------------------------------------------------------------
env -u ALL_PROXY -u HTTP_PROXY -u HTTPS_PROXY \
    -u all_proxy -u http_proxy -u https_proxy \
  codex exec -s read-only -C "$REPO_OR_WORKTREE" --skip-git-repo-check \
    -o "$SP/codex.txt" - < "$SP/prompt-codex.md" > "$SP/codex.log" 2>&1 &
CODEX_PID=$!
PANEL_PIDS+=("$CODEX_PID")

# --- Gemini --------------------------------------------------------------
gemini --skip-trust --approval-mode plan -o text \
  -p "Review the material above per the instructions it contains." \
  < "$SP/prompt-gemini.md" > "$SP/gemini.txt" 2>"$SP/gemini.log" &
GEMINI_PID=$!
PANEL_PIDS+=("$GEMINI_PID")

# --- Cursor / Grok 4.6 ---------------------------------------------------
# One chat for the whole panel. Later rounds resume it instead of resending
# the diff. --workspace must repeat on every turn: dropping it forks the
# session silently and the seat answers from an empty context.
CURSOR_CHAT=$(cursor-agent create-chat 2>/dev/null | tr -d '[:space:]')
cursor-agent -p --trust --mode ask --model cursor-grok-4.6-high \
    --resume "$CURSOR_CHAT" --workspace "$REPO_OR_WORKTREE" \
    --output-format text \
    < "$SP/prompt-cursor.md" > "$SP/cursor.txt" 2>"$SP/cursor.log" &
CURSOR_PID=$!
PANEL_PIDS+=("$CURSOR_PID")

# --- Claude (when Codex is the orchestrator) -----------------------------
env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
  claude -p --restricted --strict-mcp-config \
    --disallowedTools "Write,Edit,NotebookEdit" \
    --allowedTools Read,Grep,Glob \
    --add-dir "$REPO_OR_WORKTREE" \
    < "$SP/prompt-claude.md" > "$SP/claude.txt" 2>"$SP/claude.log" &
CLAUDE_PID=$!
PANEL_PIDS+=("$CLAUDE_PID")

# --- then do YOUR OWN review, and only afterwards collect ------------------

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

### Waiting without blocking the session

Measured: the panel takes 9–10 minutes and the orchestrator's own review takes
2–3. **The remaining ~7 minutes must not be spent in a foreground poll.** A
`until kill -0 …; do sleep 10; done` call run in the foreground pins the session
doing nothing and buys nothing — the panel is not faster for being watched.

- **Claude Code:** issue the wait as **`Bash` with `run_in_background: true`** —
  one `until` loop that exits when the last PID is gone. The harness re-invokes
  you when it exits, so you get exactly one notification and the session stays
  free. (`Monitor` is for many events; a single "panel finished" is not that.)
  If you launched the seats with a background-task primitive instead of `&`,
  track those task IDs and cancel the unfinished ones at the same deadline.
- **Codex:** no such primitive — keep the shell loop above, inside the one
  persistent exec session that owns the PIDs.

**Do not touch the working tree while the panel is running.** Every peer opens
the real files (Step 2), and the diff it was handed is a frozen snapshot. Edit
underneath it and its findings cite lines that have moved — you will spend the
merge dismissing your own edits as hallucinations. Fixes wait for Step 4.

Spend the gap on work the merge needs anyway, in this order:

1. Your own full review in the panel's output format (you are a voting seat).
2. Ground *your* findings: open each file you cited and confirm the line — Step 4
   requires this for every promoted finding, so it is pure critical-path pull-forward.
3. Run the repo's build/test/lint gates, so their result is ready when fixes land.
4. Re-read the target's spec or plan for the standing-rule check.

Add `deep` flags when requested: `-c model_reasoning_effort=high` (Codex),
`--model cursor-grok-4.6-xhigh` (Cursor), `-m gemini-2.5-pro` (Gemini).
Verify a Cursor model id against `cursor-agent --list-models` before using it —
`cursor-grok-4.6-high` and `-xhigh` were confirmed present on this machine.

**While they run:** do your own review with your native tools. You are a voting
reviewer, not just a judge — produce your own issue list in the same format
before you look at anyone else's. Reading theirs first anchors you.

Prompt template: `prompts/review.md`, assembled by `prompts/assemble.py` (Step 3).

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

**Collect the panel in one call, and never `cat` a reviewer's file.** A panel
report is mostly prose around its `ISSUE-N` blocks; pulling all of it in — worse,
`head -c` then `tail -c` the same file — is the single largest avoidable context
cost of the run, and every byte is re-read as cache on every later call.

```bash
for R in codex cursor claude gemini; do
  [ -s "$SP/$R.txt" ] || continue
  echo "=== $R ($(wc -c < "$SP/$R.txt") bytes) ==="
  awk '/^ *(ISSUE-|OVER-ENGINEERING SWEEP)/,/^ *$/' "$SP/$R.txt"
done
```

Classify every seat from that loop, and never confuse the two silent cases:

- **empty or absent `.txt`** → the seat never answered. Read its `.log` once,
  name it and the reason in the header. It is **not** a clean review, and it
  carries no weight.
- **non-empty `.txt`, empty extraction** → the reviewer ignored the output
  format. Only then read its raw text (`sed -n 1,80p`) and say so in the report.

Open a raw file otherwise only for a specific finding whose text got cut.

Deduplicate by `file:line + intent`, not by wording. Same root cause surfaced two
ways = one issue citing both. Severity disagreement = take the highest, note it.

| Agreement                 | Weight         | Route                  |
| ------------------------- | -------------- | ---------------------- |
| all four                     | 3.40 UNANIMOUS | consensus              |
| both trusted (you + peer)    | 2.0 STRONG     | consensus              |
| one trusted + Cursor/Grok    | 1.90 STRONG    | consensus              |
| one trusted + Gemini         | 1.5 SUFFICIENT | consensus              |
| Cursor/Grok + Gemini         | 1.40 SUFFICIENT| consensus              |
| one trusted alone            | 1.0            | **contested** → debate |
| Cursor/Grok alone            | 0.90           | **contested** → debate |
| Gemini alone                 | 0.5            | **contested** → debate |

Cursor/Grok sits at **0.90 deliberately**, not 1.0: near-peer, but never able to
do alone what a trusted reviewer does alone. Pair it with anyone and the pair
clears consensus; leave it alone and it argues its case like any single voice.

The 0.05 below a plain near-peer discount is the seat's session reuse. Cursor is
the one panelist whose rounds share a conversation, so by the time it rebuts it
remembers the position it took in review — it defends its own finding rather
than re-deriving it. That is right for a rebuttal and wrong for an independent
vote, and the weight carries the difference.

Confidence filter, applied **after** dedup and **before** debate:

- any reporter scored ≥70 → keep, use the highest score
- all reporters <70 → auto-dismiss into the Low Confidence list
- weight **≥1.90** bypasses this filter — agreement between two near-full-weight
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

Both rounds reason over findings already merged in Step 4. Neither reads the
repository, so neither pays for a coding-agent CLI: `panel/direct.sh`, sourced
in Step 2, sends them straight to the model APIs.

```bash
python3 "$TR/prompts/assemble.py" --template debate --class "$TARGET_CLASS" \
  --focus "$FOCUS" --contested "$SP/contested.md" --code-context "$SP/target.diff" \
  > "$SP/prompt-debate-codex.md"
direct_codex "$SP/prompt-debate-codex.md" "$SP/debate-codex.txt" &
PANEL_PIDS+=("$!")
direct_claude "$SP/prompt-debate-codex.md" "$SP/debate-claude.txt" &
PANEL_PIDS+=("$!")
# Cursor has no direct path. It resumes the chat Step 3 opened, so it still
# remembers the diff it read; --workspace must repeat or the session forks.
cursor-agent -p --trust --mode ask --model cursor-grok-4.6-high \
    --resume "$CURSOR_CHAT" --workspace "$REPO_OR_WORKTREE" \
    --output-format text \
    < "$SP/prompt-debate-codex.md" > "$SP/debate-cursor.txt" 2>&1 &
PANEL_PIDS+=("$!")
```

Rebuttal repeats the same shape with `--template rebuttal --challenges`. A seat
that fell back to its CLI says so on stderr; name it in the Step 6 header.

## Step 6 — Output

```markdown
## Tribunal Review — <target>

**Verdict:** APPROVE | CHANGES NEEDED (N consensus findings, worst: SEVERITY)
**Panel:** <answered seats and weights, including Cursor/Grok when it answered> · Missing: <seat: reason, or none> · <mode>
**Focus:** <verbatim focus text, or "none">

### Consensus (N)

#### Focus: <focus text> ← omit this sub-heading when no focus given

- **[CRITICAL]** `file:line` — Title
  Category: bug | Agreement: unanimous (3.40) | Confidence: 92
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
  - Opening positions: Peer (1.0) … | Cursor/Grok (0.90) … | Gemini (0.5) … | You (1.0) …
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
| a run reaches the 15-minute deadline | The Step 3 deadline kills only captured live PIDs. Keep partial output, mark the seat missing, and continue. **Never `pkill -f 'codex exec'`**: it matches the user's other Codex jobs |
| non-zero exit                       | keep the `.log`, parse whatever landed in the `.txt`, continue                                             |
| unparseable output                  | flag the unparseable section, do not silently drop it                                                      |
| >50 changed files                   | prioritize by change size; say in the header what was excluded                                             |

**A named CLI error** (trust dialog, license, Keychain, credit balance, a
peer that wrote a file or returned a plan instead of a review) is diagnosed
row by row in `references/panel-cli-notes.md`. Look it up when you see one;
do not retry the same command hoping for a different result.

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
