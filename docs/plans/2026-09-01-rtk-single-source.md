# RTK Single-Source Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make RTK guidance load in fresh Codex sessions while cstack remains the only source for every public RTK file.

**Architecture:** Codex receives the operative RTK rule directly from cstack's global `AGENTS.md`. The private bootstrap creates and audits a single live `~/.codex/RTK.md` symlink to cstack's canonical reference; it never vendors or renders public RTK content.

**Tech Stack:** Markdown global instructions, Bash bootstrap, Python `unittest` contract tests and audit.

---

### Task 1: Specify the public RTK runtime contract

**Files:**
- Modify: `rules/AGENTS.md`
- Modify: `README.md`
- Test: `tests/test_no_private_content.py`

1. Add a failing contract assertion that the Codex rules contain an operative RTK prefix instruction and no machine-specific `@` path.
2. Run `python3 -m unittest discover -s tests` and confirm the new assertion fails for the missing operative rule.
3. Add the minimal RTK section to `rules/AGENTS.md` and list `rules/RTK.md → ~/.codex/RTK.md` in the install surface.
4. Run the cstack suite and `git diff --check`; expect 25 passing tests and no whitespace errors.
5. Commit the cstack rule and documentation change.

### Task 2: Install and audit the RTK link

**Files:**
- Modify: `bootstrap.sh`
- Modify: `scripts/audit-sharing.py`
- Modify: `tests/test_skill_links.py`

1. Extend the existing bootstrap contract test to require `rules/RTK.md` before mutation and link it to `~/.codex/RTK.md`; extend the audit contract with a temporary-home test that rejects a regular-file copy.
2. Run `python3 -m unittest discover -s tests` and confirm the new assertions fail because RTK is not yet managed.
3. Add `rules/RTK.md` to the required-source list, create its link beside `AGENTS.md`, and add the same source/target pair to `managed_files()`.
4. Run the clauded suite and `bash -n bootstrap.sh`; expect all tests to pass.
5. Commit the clauded bootstrap, audit, and test change.

### Task 3: Prove stable runtime behavior

**Files:**
- No source changes expected.

1. Run both complete repository test suites and `git diff --check`.
2. Run the private bootstrap twice from stable paths; confirm `~/.codex/RTK.md` is a symlink to cstack and no public copy is produced.
3. Run `scripts/audit-sharing.py`; require every managed public row, including RTK, to be `ok`.
4. Start a fresh read-only `codex exec` process that may not read files or call tools; require `RTK_RULE: PRESENT`.
5. Review both diffs, open PRs, merge only with clean merge state, fast-forward local default branches, rerun the full verification, and remove the temporary worktrees.
