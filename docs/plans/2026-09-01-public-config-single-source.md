# Public Config Single Source Implementation Plan

> **For Codex and Claude:** REQUIRED SUB-SKILL: Use `execute-plan` to implement this plan task-by-task.

**Goal:** Make `cstack` the sole source of public rules, hooks, commands, and shared skills while the private bootstrap repository only links those files.

**Architecture:** The private bootstrap resolves one required `CSTACK_REPO` and uses it for every public live link. Duplicate public files are removed from the private repository, and contract tests reject either a returned duplicate or a bootstrap route that bypasses `cstack`.

**Tech Stack:** Bash symlink bootstrap, Python `unittest`, Markdown documentation, Git worktrees.

---

### Task 1: Add failing ownership-contract tests

**Files:**

- Modify: private bootstrap repo `tests/test_skill_links.py`

**Step 1: Replace the skill-only migration assertions**

Expand the existing migrated-skill contract into two focused tests. Use an
explicit allowlist for private-owned config paths and private skill directories,
so any new private ownership requires a deliberate contract update:

```python
def test_no_local_public_copies(self):
    config_files = {
        str(path.relative_to(ROOT))
        for root in (ROOT / "claude", ROOT / "codex")
        if root.exists()
        for path in root.rglob("*")
        if path.is_file()
    }
    self.assertEqual(PRIVATE_CONFIG_FILES, config_files)

    skills = {
        str(path.relative_to(ROOT))
        for root in (ROOT / "agents-skills", ROOT / "claude-skills")
        for path in root.iterdir()
        if path.is_dir()
    }
    self.assertEqual(PRIVATE_SKILLS, skills)
    for name in FORBIDDEN_PUBLIC_NODES:
        path = ROOT / name
        self.assertFalse(path.is_symlink())
        if path.is_dir():
            self.assertFalse(any(path.iterdir()))
        else:
            self.assertFalse(path.exists())

def test_bootstrap_sources_every_public_surface_from_cstack(self):
    body = (ROOT / "bootstrap.sh").read_text()
    for source in (
        'link "$CSTACK_REPO/rules/CLAUDE.md" "$HOME/.claude/CLAUDE.md"',
        'link "$CSTACK_REPO/rules/AGENTS.md" "$HOME/.codex/AGENTS.md"',
        'for h in "$CSTACK_REPO"/hooks/*.sh; do',
        'for c in "$CSTACK_REPO"/commands/*.md; do',
        'for s in "$CSTACK_REPO"/skills/*/; do',
    ):
        self.assertIn(source, body)

    require = body.index('if [[ ! -d "$CSTACK_REPO" ]]')
    require_end = body.index("\nfi", require)
    required_surfaces = body.index(
        "for required in rules/CLAUDE.md rules/AGENTS.md hooks commands skills; do"
    )
    required_surfaces_end = body.index("\ndone", required_surfaces)
    first_public_link = body.index('link "$CSTACK_REPO')
    self.assertLess(require, first_public_link)
    self.assertIn("exit 1", body[require:require_end])
    self.assertIn("exit 1", body[required_surfaces:required_surfaces_end])

    for call in (
        'assert_no_name_collision command "$CSTACK_REPO/commands" "$REPO/claude/commands"',
        'assert_no_name_collision skill "$CSTACK_REPO/skills" "$REPO/agents-skills"',
        'assert_no_name_collision skill "$CSTACK_REPO/skills" "$REPO/claude-skills"',
    ):
        self.assertLess(body.index(call), first_public_link)

    for stale_source in (
        '$REPO/claude/CLAUDE.md',
        '$REPO/codex/AGENTS.md',
        '"$REPO"/claude/hooks/*.sh',
    ):
        self.assertNotIn(stale_source, body)
```

Scope the fan-out assertion to the `for s in "$CSTACK_REPO"/skills/*/` loop
itself, not a larger block that also contains private skill loops. Keep the
required-project manifest assertion.

**Step 2: Run the focused tests and verify failure**

Run: `python3 -m unittest discover -s tests -p 'test_skill_links.py'`

Expected: FAIL because duplicate public files remain and rules/hooks/commands still source from the private repository.

**Step 3: Commit the failing contract**

Run:

```bash
git add tests/test_skill_links.py
git commit -m "test: enforce cstack public config ownership"
```

### Task 2: Cut the bootstrap over to `cstack`

**Files:**

- Modify: private bootstrap repo `bootstrap.sh`
- Modify: private bootstrap repo `README.md`
- Modify: private bootstrap repo `scripts/audit-sharing.py`
- Delete: private bootstrap repo `claude/CLAUDE.md`
- Delete: private bootstrap repo `claude/RTK.md`
- Delete: private bootstrap repo `codex/AGENTS.md`
- Delete: private bootstrap repo `claude/hooks/*.sh`
- Delete: private bootstrap repo `claude/commands/branch-audit.md`

**Step 1: Resolve and validate the public repository before mutation**

Add beside `CLAUDED_REPO`:

```bash
CSTACK_REPO="${CSTACK_REPO:-$HOME/projects/cstack}"
```

Before creating or replacing live links, require these directories:

```bash
if [[ ! -d "$CSTACK_REPO" ]]; then
  echo "ERROR: public config repo not found at $CSTACK_REPO" >&2
  echo "Set CSTACK_REPO=/path/to/cstack and rerun." >&2
  exit 1
fi
```

Also reject public/private command or skill basename collisions before the
first live link is changed.

**Step 2: Route every public surface through `CSTACK_REPO`**

Use these sources:

```bash
link "$CSTACK_REPO/rules/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
link "$CSTACK_REPO/rules/AGENTS.md" "$HOME/.codex/AGENTS.md"

for h in "$CSTACK_REPO"/hooks/*.sh; do
  [[ -e "$h" ]] || continue
  link "$h" "$HOME/.claude/hooks/$(basename "$h")"
done

for c in "$CSTACK_REPO"/commands/*.md; do
  link "$c" "$HOME/.claude/commands/$(basename "$c")"
done

for s in "$CSTACK_REPO"/skills/*/; do
  name="$(basename "$s")"
  link "$s" "$HOME/.agents/skills/$name"
  link "$s" "$HOME/.claude/skills/$name"
done
```

Keep a separate loop for private commands such as `boot-local.md`. Remove the old warning-only cstack skill block because `cstack` is now required and resolved once.

Update `scripts/audit-sharing.py` so its managed-file checks compare live global
rules, hooks, commands, and both runtime skill links to their corresponding
`CSTACK_REPO` sources; remove the obsolete live `RTK.md` check.

**Step 3: Remove duplicate public files**

Delete the files listed above. Do not replace them with wrappers, generated copies, or repository-relative symlinks.

**Step 4: Update private bootstrap documentation**

Document that the private repository owns only machine/account state and consumes public configuration from `CSTACK_REPO`. Remove instructions that tell users to edit public rules or hooks through the private tree.

**Step 5: Run the focused and full test suites**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_skill_links.py'
python3 -m unittest discover -s tests
```

Expected: all tests PASS.

**Step 6: Commit the cutover**

Run:

```bash
git add bootstrap.sh README.md tests/test_skill_links.py
git add -u claude codex
git commit -m "refactor: source public config from cstack"
```

### Task 3: Complete the public installation contract

**Files:**

- Modify: `README.md`
- Create: `docs/plans/2026-09-01-public-config-single-source-design.md`
- Create: `docs/plans/2026-09-01-public-config-single-source.md`

**Step 1: Correct the install matrix**

State explicitly:

- `rules/CLAUDE.md` links to `~/.claude/CLAUDE.md`;
- `rules/AGENTS.md` links to `~/.codex/AGENTS.md`;
- public hooks link individually into `~/.claude/hooks/`;
- public commands link individually into `~/.claude/commands/`;
- shared skills link into both runtime skill directories;
- machine-private bootstrap/config stays outside this public repository.

**Step 2: Run public contract tests**

Run: `python3 -m unittest discover -s tests`

Expected: 24 tests PASS, including the private-content scan.

**Step 3: Commit the public documentation**

Run:

```bash
git add README.md docs/plans
git commit -m "docs: define complete public install surface"
```

### Task 4: Apply and verify the live cutover

**Files:**

- Live symlinks under `~/.codex/`, `~/.claude/`, and `~/.agents/skills/`

**Step 1: Run bootstrap twice**

Run the private bootstrap with `CSTACK_REPO` pointing at the cstack feature worktree and `CLAUDED_REPO` pointing at the private feature worktree. Run the identical command twice.

Expected: both runs succeed; the second run preserves the same targets and does
not create new public-symlink recovery records. Its rendered-settings backup is
expected private-state behavior.

**Step 2: Audit resolved targets**

Verify that live public rules, hooks, public commands, and the three shared skills all resolve beneath the cstack worktree. Verify private settings, commands, skills, plugins, and memory still resolve from the private repository where applicable.

**Step 3: Compare live public content**

Run byte comparisons for every linked public file.

Expected: no mismatch.

**Step 4: Probe a fresh Codex run**

Run a read-only Codex command from the cstack repository asking it to name the active global instruction themes and whether the three shared skills are discoverable.

Expected: the global instruction themes are present and all three skills are discoverable. Do not claim prompt/reference files are preloaded; they remain on-demand.

### Task 5: Review and deliver both branches

**Files:**

- Both repositories' complete branch diffs

**Step 1: Run `review-cycle`**

Review each branch against this design, with focus on stale duplicate paths, bootstrap idempotence, public/private boundary leakage, and live-link safety. Apply accepted findings and rerun the affected tests.

**Step 2: Confirm clean final state**

Run both full test suites, `git diff --check`, and `git status --short` in each worktree.

Expected: tests pass, no whitespace errors, and only committed intended changes remain.

**Step 3: Push and open one PR per repository**

Push `fix/public-config-single-source` in each repository and open linked PRs. Wait for fresh completed remote checks before merging.

**Step 4: Merge and synchronize local default branches**

Merge only when both PRs are mergeable and checks are green. Fetch each repository and fast-forward the local default branch to the remote merge commit.
