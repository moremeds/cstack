# RTK Single-Source Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make RTK guidance load in fresh Codex sessions while cstack remains the only source for every public RTK file.

**Architecture:** Codex receives the operative RTK rule directly from cstack's global `AGENTS.md`. `rules/RTK.md` remains checkout-only reference material; no live RTK file or import is created, so the existing `AGENTS.md` symlink remains the sole global-rules entry point.

**Tech Stack:** Markdown global instructions, Bash bootstrap, Python `unittest` contract tests and audit.

---

### Task 1: Specify the public RTK runtime contract

**Files:**
- Modify: `rules/AGENTS.md`
- Modify: `README.md`
- Test: `tests/test_no_private_content.py`

1. Add a failing contract assertion that the Codex rules contain an operative RTK prefix instruction and no machine-specific `@` path.
2. Run `python3 -m unittest discover -s tests` and confirm the new assertion fails for the missing operative rule.
3. Add the minimal RTK section to `rules/AGENTS.md` and document that `rules/RTK.md` stays checkout-only.
4. Run the cstack suite and `git diff --check`; expect 25 passing tests and no whitespace errors.
5. Commit the cstack rule and documentation change.

### Task 2: Prove stable runtime behavior

**Files:**
- No source changes expected.

1. Run the complete cstack suite and `git diff --check`.
2. Run the unchanged private bootstrap twice from stable paths; confirm the live `AGENTS.md` remains a symlink to cstack and no live `RTK.md` exists.
3. Run `scripts/audit-sharing.py`; require every managed public row to be `ok`.
4. Start a fresh read-only `codex exec` process that may not read files or call tools; require `RTK_RULE: PRESENT`.
5. Review the diff, open a PR, merge only with clean merge state, fast-forward the local default branch, rerun the full verification, and remove the temporary worktrees.
