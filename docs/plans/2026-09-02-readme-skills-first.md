# Skills-first README Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `README.md` as a human, skills-first introduction to cstack's four-skill workflow.

**Architecture:** Replace the current repository-tour opening with a reader journey: recognizable agent failure modes, the four skills that address them, a fast installation path, and then the deeper evidence. Keep supporting rules, hooks, commands, and tests in one compact section so they establish trust without competing with the product.

**Tech Stack:** GitHub-flavored Markdown, Claude Code plugin manifest, Codex plugin manifest, existing Python `unittest` contract suite.

---

### Task 1: Rewrite the README around the four skills

**Files:**
- Modify: `README.md`

**Step 1: Replace the opening and first screenful**

Open with the idea that coding agents rarely fail by stopping; they fail by
continuing while losing the thread. State that cstack is four portable skills
for keeping a plan, implementation, review, and status readout tied to evidence.

**Step 2: Add the four recognizable moments**

Map each moment to one skill:

- "I approved the plan; now finish it" → `execute-plan`
- "Review this properly, and fix what you find" → `review-cycle`
- "I do not want one model grading its own homework" → `tribunal-review`
- "Stop narrating and tell me what is actually true" → `whatup`

**Step 3: Move the quickest supported install near the top**

Keep the current Claude Code marketplace commands unchanged and explain in one
sentence that all four skills install together. Keep checkout and symlink setup
later as the maintainer/power-user path.

**Step 4: Explain the workflow and each skill**

Use this order:

1. One compact workflow diagram.
2. `whatup`, because it is the most immediate recovery tool.
3. `execute-plan`, the straight-through implementation path.
4. `review-cycle`, the fix-and-verify loop.
5. `tribunal-review`, the cross-model engine behind Pass 2.

For each skill, include its invocation, the human situation it addresses, and
the concrete output or guarantee it provides. Retain only implementation detail
that earns trust, including liveness probing and evidence-beside-claim behavior.

**Step 5: Compress the supporting repository sections**

Replace the long standalone tours of `rules/`, `hooks/`, `commands/`, and
`tests/` with one "Inside the repo" section. Preserve these important facts:

- the four skill files are the plugin's core;
- shared skill sources are not duplicated between runtimes;
- hooks can block unsafe tool calls with exit 2;
- public-content and contract tests protect publication and workflow promises;
- private, machine-specific configuration stays outside this public repo.

**Step 6: Keep claims bounded**

Retain the measured lesson that text review does not replace running code, but
move detailed session timings out of the main path. Do not claim that cstack
eliminates agent failure; describe the evidence and verification it requires.

**Step 7: Review the diff for voice and scope**

Run:

```bash
git diff -- README.md
```

Expected: only `README.md` changes; the opening is skills-first, the install is
near the top, and supporting internals are shorter than the skill descriptions.

### Task 2: Verify the README against the repository

**Files:**
- Verify: `README.md`
- Verify: `.claude-plugin/plugin.json`
- Verify: `.codex-plugin/plugin.json`
- Verify: `skills/*/SKILL.md`

**Step 1: Check every documented skill and command**

Run:

```bash
rg -n '^name:|^description:' skills/*/SKILL.md
rg -n 'execute-plan|review-cycle|tribunal-review|whatup|plugin marketplace|plugin install' README.md
```

Expected: four skills are present and the documented names and installation
commands match the repository.

**Step 2: Run the existing contract suite**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: all tests pass. Add no new tests because this change does not alter
runtime behavior and the existing public-content test covers the publication
risk.

**Step 3: Check formatting and repository scope**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only the README and the two approved plan files
are tracked changes or commits. The pre-existing untracked `docs/notes/` content
remains untouched.

**Step 4: Commit**

```bash
git add README.md
git commit -m "README: put the four skills first"
```
