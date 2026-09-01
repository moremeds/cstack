"""The review chain's failure mode is a stale reference, not a crash.

Every assertion here is mutation-checked: it must fail on a tree where the
contract it protects has been broken. An assertion that passes either way is
worse than no test — it certifies nothing while reading as coverage.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CYCLE = ROOT / "skills" / "review-cycle" / "SKILL.md"
TRIBUNAL = ROOT / "skills" / "tribunal-review" / "SKILL.md"
REVIEW_PROMPT = ROOT / "skills" / "tribunal-review" / "prompts" / "review.md"
EXECUTE = ROOT / "skills" / "execute-plan" / "SKILL.md"


class TestReviewCycleDelegates(unittest.TestCase):
    def setUp(self):
        self.body = CYCLE.read_text()

    def pass2(self):
        """Pass 2's operative text: the section, minus the delimited rationale.

        The rationale paragraph quotes the banned commands to explain why they
        are gone, and must stay able to. It is fenced off with an HTML comment
        so this test excludes exactly that and nothing else — scoping to code
        blocks instead (the previous approach) left an operative bullet like
        "Run `codex exec review --base main`" completely untested.
        """
        s = self.body[self.body.index("### Pass 2"):]
        s = s[:s.index("### Pass 3")]
        i, j = s.find("<!-- rationale:begin"), s.find("<!-- rationale:end -->")
        return s[:i] + s[j:] if i != -1 else s

    def test_pass2_invokes_tribunal_review_as_a_skill(self):
        """Not `assertIn("tribunal-review", body)` — that word appears in the
        description and the guardrails, so it stayed green with the actual
        invocation reverted to `codex-review <target>`."""
        p2 = self.pass2()
        self.assertRegex(p2, r"\n\s*tribunal-review <target-flag>",
                         "Pass 2 has no literal tribunal-review invocation line")
        for legacy in ("codex-review", "/tribunal-review "):
            self.assertNotIn(legacy, p2, f"{legacy!r} is a stale invocation")

    def test_focus_is_passed_through(self):
        """Measured cause of the original bug: the reviewer ran without focus."""
        self.assertIn("focus:", self.pass2(), "Pass 2 drops the user's focus text")

    def test_no_hand_rolled_cli_calls_in_operative_text(self):
        """review-cycle must not drive the reviewer CLIs itself.

        Each was a real logged failure: `codex exec review` dropped the focus
        parameter, `pkill -f` killed unrelated jobs, `which` reported an
        unlicensed Gemini as present. tribunal-review owns them now.
        """
        for pattern, why in [
            ("codex exec", "flag/prompt exclusivity drops the focus text"),
            ("gemini -p", "tribunal-review owns reviewer launch"),
            ("claude -p", "tribunal-review owns reviewer launch"),
            ("pkill", "kills unrelated Codex jobs on the machine"),
            ("which codex", "an installed binary can still be unlicensed"),
            ("command -v codex", "an installed binary can still be unlicensed"),
        ]:
            self.assertNotIn(pattern, self.pass2(),
                             f"{pattern!r} prescribed here — {why}")


class TestReviewClassesAgree(unittest.TestCase):
    """review-cycle routes three artifact types into tribunal-review's classes.

    If tribunal-review ever loses one, review-cycle silently sends prose into
    the plan class, whose DO-NOT-FLAG list suppresses prose findings — the
    review would come back clean for the wrong reason.
    """

    def test_each_type_routes_to_its_own_flag(self):
        """Checking that the words `prose` and `--prose` both appear left the
        route `| prose | --plan <path> |` green — the exact silent misrouting
        this class exists to catch. Assert the pairing."""
        cycle = CYCLE.read_text()
        rows = [r for r in cycle.splitlines() if r.startswith("| ")]
        for typ, flag in (("code, no arg", "--diff"), ("code, `pr", "--pr"),
                          ("plan", "--plan"), ("prose", "--prose")):
            hit = [r for r in rows if r.lstrip("| ").startswith(typ)]
            self.assertTrue(hit, f"no routing row for {typ!r}")
            # \b after `--pr` would match inside `--prose`; require the flag
            # to end at a non-flag character instead.
            def named(f, row):
                return re.search(re.escape(f) + r"(?![-\w])", row) is not None
            self.assertTrue(named(flag, hit[0]), f"{typ!r} does not route to {flag}")
            for other in ("--diff", "--pr", "--plan", "--prose"):
                if other != flag:
                    self.assertFalse(named(other, hit[0]),
                                     f"{typ!r} also routes to {other}")

    def test_every_class_has_a_prompt_block_and_severity_scale(self):
        skill, prompt = TRIBUNAL.read_text(), REVIEW_PROMPT.read_text()
        flat = prompt.replace("plan/spec", "plan")
        for cls in ("code", "plan", "prose"):
            self.assertIn(f"HOW TO REVIEW ({cls}", flat, f"no {cls} review block")
            self.assertIn(f"SEVERITY ({cls}", flat, f"no {cls} severity scale")
            self.assertIn(f"--{cls}" if cls != "code" else "--diff", skill,
                          f"tribunal-review cannot be targeted at {cls}")

    def test_prose_sweep_is_not_both_skipped_and_mandatory(self):
        """The sweep says "NOT optional, on any class" and demands a verdict
        line; the prose block used to say "do not run the sweep on prose"."""
        prompt = REVIEW_PROMPT.read_text()
        self.assertIn("OVER-ENGINEERING SWEEP: clean", prompt)
        self.assertNotIn("Do not run the over-engineering sweep below on prose",
                         prompt, "prose is told to skip a sweep it must report")


class TestFullCycleIsPortable(unittest.TestCase):
    def test_execute_plan_does_not_assume_review_cycle_exists(self):
        """execute-plan is portable; /review-cycle is a Claude-only command.

        Under Codex the slash command is invisible, so --full-cycle must name
        the portable fallback rather than gate on something unreachable.
        """
        body = EXECUTE.read_text()
        self.assertIn("tribunal-review", body,
                      "--full-cycle has no reviewer Codex can reach")
        # Match the SECTION, not the phrase — Step 0 cross-references it by
        # name, so a bare `assertIn("Which reviewer")` passes even with the
        # section deleted, leaving a dangling pointer and no fallback.
        self.assertIn("### Which reviewer", body,
                      "the runtime split section is gone")
        section = body[body.index("### Which reviewer"):]
        section = section[:section.index("\n7. ")]
        self.assertIn("Codex", section, "the section names no Codex-reachable reviewer")
        self.assertIn("tribunal-review", section)

    def test_runtime_specific_tools_are_routed_by_capability(self):
        """The shared skill must not require one runtime's tracker or question tool."""
        body = EXECUTE.read_text()
        self.assertIn("TaskCreate", body, "Claude Code lost its milestone tracker")
        self.assertIn("update_plan", body, "Codex has no milestone tracker it can call")
        frontmatter = body.split("---", 2)[1]
        self.assertNotIn("allowed-tools:", frontmatter,
                         "Claude-only tool names in shared frontmatter constrain portability")

    def test_execution_base_is_captured_and_reused_for_post_review(self):
        """A reused worktree may contain commits that predate this execution."""
        body = EXECUTE.read_text()
        setup = body[body.index("1. **Worktree setup"):body.index("2. **")]
        post = body[body.index("7. **Full-cycle post-review") : body.index("8. **")]
        self.assertIn("git rev-parse HEAD", setup,
                      "the execution range has no recorded starting SHA")
        self.assertIn("EXEC_BASE", setup)
        self.assertIn("EXEC_BASE", post,
                      "post-review can silently include pre-existing commits")
        self.assertIn("tribunal-review --base", post,
                      "there is no exact-range fallback when review-cycle cannot target EXEC_BASE")

    def test_exact_range_fallback_reviews_a_clean_committed_tree(self):
        """tribunal-review's base payload does not enumerate staged or untracked files."""
        body = EXECUTE.read_text()
        post = body[body.index("7. **Full-cycle post-review") : body.index("8. **")]
        self.assertIn("clean worktree", post.lower())
        self.assertIn("review-fix commit", post.lower())

    def test_unrelated_branch_history_is_not_carried_into_delivery(self):
        body = EXECUTE.read_text()
        setup = body[body.index("1. **Worktree setup"):body.index("2. **")]
        self.assertIn("unrelated commits", setup.lower())
        self.assertIn("fresh", setup.lower())

    def test_conversation_plan_uses_a_repo_external_scratch_artifact(self):
        """Pre-review must not dirty the checkout before worktree setup."""
        body = EXECUTE.read_text()
        pre = body[body.index("0. **Full-cycle pre-review gate") : body.index("1. **")]
        self.assertIn("scratch", pre.lower())
        self.assertIn("outside the repository", pre.lower())


class TestReviewCycleIsPortable(unittest.TestCase):
    """review-cycle must be reachable from Codex, not just Claude Code.

    Measured, not assumed: Codex scans ~/.agents/skills/ and Claude Code scans
    ~/.claude/skills/ — neither reads the other, and ~/.claude/commands/ is
    Claude-only. A slash command is therefore invisible to Codex. Skills live
    in skills/ so an installer can fan one directory into both runtimes; a
    Claude-only location would silently halve the audience.
    """

    def test_lives_in_the_portable_tree(self):
        self.assertTrue(CYCLE.exists(), f"{CYCLE} missing — did it move back?")
        self.assertEqual(CYCLE.parent.parent.name, "skills",
                         "review-cycle is not in the portable tree")

    def test_has_skill_frontmatter(self):
        body = CYCLE.read_text()
        head = body[:1200]
        self.assertTrue(head.startswith("---\n"), "no frontmatter block")
        self.assertIn("name: review-cycle", head)
        self.assertIn("description:", head)

    def test_codex_tracker_and_quick_verdict_are_operable(self):
        """Codex must be able to run the cycle, and quick must be a real mode."""
        body = CYCLE.read_text()
        frontmatter = body.split("---", 2)[1]
        self.assertNotIn("allowed-tools:", frontmatter,
                         "shared frontmatter still constrains the skill to Claude tools")

        tracker = body[body.index("### Task tracking"):body.index("## Pass 1")]
        self.assertIn("TaskCreate", tracker, "Claude Code lost its native tracker")
        self.assertIn("update_plan", tracker, "Codex has no tracker it can call")
        self.assertIn("parent tracker", tracker.lower(),
                      "nested review can replace the execution plan that invoked it")
        self.assertIn("one `in_progress`", tracker,
                      "Codex may leave multiple current passes in its shared tracker")

        verdict = body[body.index("**SHIP requires a complete ledger.**"):]
        verdict = verdict[:verdict.index("```", 1)]
        self.assertIn("skipped (quick mode)", verdict,
                      "quick mode has no explicit evidence state for Pass 6")
        self.assertRegex(verdict, r"(?is)quick mode.*does not cap.*`SHIP`",
                         "quick mode still cannot emit SHIP after clean required passes")

        ledger = body[body.index("### Pass ledger"):body.index("### Findings applied")]
        for pass_name in ("3 adversarial", "4 cumulative re-read"):
            row = next(line for line in ledger.splitlines() if f"| {pass_name} |" in line)
            self.assertIn("skipped (quick)", row,
                          f"quick mode must not falsely report that {pass_name} ran")

        stopping = body[body.index("## Stopping condition"):body.index("## Guardrails")]
        self.assertRegex(stopping, r"(?is)full mode.*min\(confidence\).*quick mode.*Pass 6",
                         "the stopping rule still demands confidence ratings in quick mode")

        critique = body[body.index("| Type | Critique sections |"):body.index("If a focus was given")]
        for artifact_type in ("code", "plan", "prose"):
            row = next(line for line in critique.splitlines()
                       if line.startswith(f"   | {artifact_type} |"))
            self.assertIn("Standing-rule", row,
                          f"quick {artifact_type} review cannot fill its mandatory rules row")

class TestPeerClaudeIsSandboxed(unittest.TestCase):
    """Measured: --allowedTools and --disallowedTools do not stop a write.

    allowedTools only auto-approves, and a deny list is routed around by an MCP
    server's shell tool. --permission-mode plan blocks writes but persists a
    file into ~/.claude/plans/ and can return "Approve the plan..." in place of
    the review. Only --restricted --strict-mcp-config held.
    """

    def test_claude_peer_launch_contract(self):
        body = TRIBUNAL.read_text()
        launch = body[body.index("--- Claude (when Codex is the orchestrator)"):]
        launch = launch[:launch.index("CLAUDE_PID=$!")]
        # Strip the comment block: it documents what was REJECTED and why, so
        # asserting on raw text would fail on its own explanation.
        cmd = "\n".join(l for l in launch.splitlines() if not l.lstrip().startswith("#"))
        for frag, why in [
            ("--restricted", "the only flag measured to actually block writes"),
            ("--strict-mcp-config", "without it an MCP shell tool routes around the deny list"),
            ("-u ANTHROPIC_API_KEY", "the key outranks the login and fails on low balance"),
            ("--add-dir", "the peer cannot read the repo it is reviewing"),
            ('< "$SP/prompt-claude.md"', "no stdin prompt: --allowedTools is variadic and eats a positional one"),
            ('> "$SP/claude.txt"', "the review is not captured anywhere"),
            ("&", "not backgrounded — it serializes the panel"),
        ]:
            self.assertIn(frag, cmd, f"peer launch is missing {frag!r} — {why}")
        self.assertNotIn("--permission-mode plan", cmd,
                         "plan mode leaks a file into ~/.claude/plans/ and can swallow the report")

    def test_step0_probe_uses_the_same_sandbox_flags(self):
        """A probe run under different flags proves the peer is alive under
        flags the peer will not actually use."""
        body = TRIBUNAL.read_text()
        probe = [l for l in body.splitlines() if "Reply with exactly: OK" in l and "claude" in l]
        self.assertTrue(probe, "no Claude liveness probe in Step 0")
        for flag in ("--restricted", "--strict-mcp-config", "-u ANTHROPIC_API_KEY"):
            self.assertIn(flag, probe[0], f"probe omits {flag}, so it tests a different command")


class TestCursorPeerIsSandboxed(unittest.TestCase):
    """Measured on cursor-agent 2026.08.11, "create /tmp/x then say DONE":

    bare `-p` CREATED the file, and so did `--sandbox enabled`. Only
    `--mode ask` refused. The published docs say that without `--force`
    "changes are only proposed, not applied" — measured false for file
    creation, which is why this contract is pinned by a test.
    """

    def setUp(self):
        body = TRIBUNAL.read_text()
        launch = body[body.index("--- Cursor / Grok 4.6"):]
        launch = launch[:launch.index("CURSOR_PID=$!")]
        self.cmd = "\n".join(l for l in launch.splitlines()
                             if not l.lstrip().startswith("#"))

    def test_launch_contract(self):
        for frag, why in [
            ("--mode ask", "the ONLY measured write guard; -p alone writes files"),
            ("--trust", "headless runs die on the workspace-trust dialog without it"),
            ("--model cursor-grok-4.6", "the cross-lineage vote is the reason this seat exists"),
            ("--workspace", "it cannot open the files it is reviewing"),
            ('< "$SP/prompt-cursor.md"', "no stdin prompt"),
            ('> "$SP/cursor.txt"', "the review is not captured anywhere"),
            ("&", "not backgrounded — it serializes the panel"),
        ]:
            self.assertIn(frag, self.cmd, f"Cursor launch missing {frag!r} — {why}")

    def test_no_write_enabling_flags(self):
        for bad in ("--force", "--yolo", "--sandbox enabled"):
            self.assertNotIn(bad, self.cmd, f"{bad} lets the reviewer edit the code")

    def test_cursor_pid_is_waited_on(self):
        body = TRIBUNAL.read_text()
        self.assertIn('PANEL_PIDS+=("$CURSOR_PID")', body,
                      "Cursor is launched but omitted from the bounded wait set")
        self.assertRegex(body, r'wait "\$PANEL_PID"',
                         "captured panel PIDs are never collected")

    def test_probe_matches_the_launch(self):
        body = TRIBUNAL.read_text()
        probe = [l for l in body.splitlines()
                 if "Reply with exactly: OK" in l and "cursor-agent" in l]
        self.assertTrue(probe, "no Cursor liveness probe in Step 0")
        for flag in ("--trust", "--mode ask", "--model cursor-grok-4.6"):
            self.assertIn(flag, probe[0], f"probe omits {flag}, so it tests a different command")


class TestPanelWeights(unittest.TestCase):
    def test_cursor_alone_cannot_reach_consensus(self):
        """0.95 is deliberate: near-peer, but never decisive alone."""
        body = TRIBUNAL.read_text()
        row = [r for r in body.splitlines() if r.startswith("| Cursor/Grok alone")]
        self.assertTrue(row, "no weight row for a lone Cursor finding")
        self.assertIn("contested", row[0], "a lone Cursor finding skips debate")
        self.assertIn("0.95", row[0])

    def test_payload_wait_and_panel_cover_the_real_review(self):
        """The panel must see every worktree state and terminate predictably."""
        body = TRIBUNAL.read_text()
        payload = body[body.index("## Step 2"):body.index("## Step 3")]
        self.assertIn('REPO_OR_WORKTREE="${REPO_OR_WORKTREE:-$(git rev-parse --show-toplevel)}"',
                      payload, "payload commands can silently run in the wrong checkout")
        for pattern, why in [
            (r'git -C "\$REPO_OR_WORKTREE" .*diff HEAD',
             "tracked staged and unstaged changes are not one coherent patch"),
            (r'git -C "\$REPO_OR_WORKTREE" ls-files --others --exclude-standard',
             "untracked paths are absent or read from the wrong checkout"),
            (r'git -C "\$REPO_OR_WORKTREE" .*diff --no-index',
             "untracked file contents are absent or read from the wrong checkout"),
        ]:
            self.assertRegex(payload, pattern, why)
        self.assertNotIn("diff --cached", payload,
                         "separate index and worktree patches expose a phantom intermediate state")
        self.assertIn("merge-base", payload,
                      "base-tip-only commits leak into the branch review as reversed hunks")
        self.assertRegex(payload, r'if \[ "\$TARGET_KIND" != "pr" \]',
                         "remote PR review still appends unrelated local untracked files")

        launch = body[body.index("## Step 3"):body.index("## Step 4")]
        self.assertIn("one persistent", launch.lower(),
                      "launch and collection can run in different shells and lose PID state")
        self.assertIn("PANEL_DEADLINE", launch, "the documented 15-minute limit is not enforced")
        self.assertLess(launch.index("PANEL_DEADLINE"), launch.index("# --- Codex"),
                        "the deadline starts after peers have already been running")
        self.assertIn("kill -0", launch, "the wait does not poll only captured peer PIDs")
        self.assertIn("kill -KILL", launch,
                      "a peer that ignores SIGTERM can still make collection wait forever")
        self.assertNotIn("BLOCKER when Codex orchestrates", launch,
                         "the launch notes override the new probe-first rule")

        output = body[body.index("## Step 6"):body.index("## Failure handling")]
        self.assertIn("Cursor/Grok", output, "Grok can vote but is omitted from the report")
        self.assertIn("Missing", output, "unavailable seats are not disclosed")
        self.assertIn("answered", output.lower(), "panel membership is still a static list")
        self.assertNotIn("unanimous (2.5)", output,
                         "the example still reports a three-seat total in a four-seat panel")
        step0 = body[body.index("## Step 0"):body.index("## Step 1")]
        self.assertNotIn("unlicensed on this machine", step0,
                         "probe-first routing is overridden by a dated Gemini assumption")


if __name__ == "__main__":
    unittest.main()
