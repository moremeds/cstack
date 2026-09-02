"""Contract tests for the tribunal's direct API transport.

The suite never makes a network call: every seat is exercised against a stubbed
`curl` on PATH. Liveness was verified by hand during design and is recorded in
the plan's Verification section; CI has no credentials.
"""

import os
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRECT = ROOT / "skills" / "tribunal-review" / "panel" / "direct.sh"
SKILL = ROOT / "skills" / "tribunal-review" / "SKILL.md"


def run_fn(fn, *args, env=None, path_prefix=None):
    """Source direct.sh and call one function, with a stubbed PATH if given."""
    e = dict(os.environ)
    if env is not None:
        e.update(env)
    if path_prefix:
        e["PATH"] = f"{path_prefix}:{e['PATH']}"
    quoted = " ".join(f"'{a}'" for a in args)
    return subprocess.run(
        ["bash", "-c", f". '{DIRECT}'; {fn} {quoted}"],
        capture_output=True, text=True, env=e,
    )


class StubbedPath(unittest.TestCase):
    """Base for seat tests: a scratch dir plus a bin/ that shadows real tools."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tribunal-")
        self.bin = pathlib.Path(self.tmp) / "bin"
        self.bin.mkdir()
        # Poison pills. Every seat falls back to its CLI when the direct path
        # fails, so an unstubbed CLI turns a *failing* test into a live spawn
        # that hangs for minutes. A test that wants the fallback overrides these.
        for cli in ("codex", "claude", "cursor-agent"):
            self._stub(cli, 'echo "UNEXPECTED CLI FALLBACK: %s" >&2; exit 3\n' % cli)

    def _stub(self, name, body):
        p = self.bin / name
        p.write_text("#!/usr/bin/env bash\n" + body)
        p.chmod(0o755)

    def _prompt(self, text):
        p = pathlib.Path(self.tmp) / "p.md"
        p.write_text(text)
        return str(p)


class TestNoSecretsInSource(unittest.TestCase):
    """A public repo cannot carry a credential or a personal path."""

    def test_no_literal_credentials_or_home_paths(self):
        src = DIRECT.read_text()
        self.assertNotRegex(src, r"sk-[A-Za-z0-9_-]{10}")
        self.assertNotRegex(src, r"/Users/[a-z]")
        # the account id is derived from the JWT, never pasted
        self.assertIn("chatgpt_account_id", src)


class TestPreflight(unittest.TestCase):
    """A missing credential must die before the panel launches, not mid-round."""

    def test_unset_token_fails_and_names_the_variable(self):
        r = run_fn("direct_preflight", env={"CLAUDE_CODE_OAUTH_TOKEN": ""})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", r.stderr)


class TestCodexSeat(StubbedPath):
    def test_sse_deltas_are_concatenated_into_the_output_file(self):
        """The reply is assembled from response.output_text.delta events."""
        sse = (
            'data: {"type":"response.created"}\n'
            'data: {"type":"response.output_text.delta","delta":"ISSUE-1 "}\n'
            'data: {"type":"response.output_text.delta","delta":"real bug"}\n'
            'data: {"type":"response.completed"}\n'
        )
        self._stub("curl", f"""
for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done
cat > "$out" <<'SSE'
{sse}
SSE
printf 200
""")
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", self._prompt("review this"), str(out),
                   path_prefix=str(self.bin))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out.read_text(), "ISSUE-1 real bug")

    def test_a_stale_output_file_is_not_mistaken_for_this_run(self):
        """$SP persists across runs when CLAUDE_SCRATCHPAD is set.

        The fallback is guarded by [ ! -s "$out" ]. If a previous run left an
        answer there, a failed call reads as a successful one: no fallback, no
        error, and the seat votes with a stale opinion about a different diff.
        """
        self._stub("curl", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\n: > "$out"\nprintf 500\n')
        self._stub("codex", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\necho "fresh" > "$out"\n')
        out = pathlib.Path(self.tmp) / "codex.txt"
        out.write_text("STALE ANSWER FROM A PREVIOUS RUN")
        run_fn("direct_codex", self._prompt("review this"), str(out),
               path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "fresh")

    def test_non_200_falls_back_to_the_cli(self):
        """A dead seat silently changes the consensus arithmetic. It must not."""
        self._stub("curl", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\n: > "$out"\nprintf 429\n')
        self._stub("codex", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\necho "from the cli" > "$out"\n')
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", self._prompt("review this"), str(out),
                   path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "from the cli")
        self.assertIn("429", r.stderr)


class TestClaudeSeat(StubbedPath):
    def test_text_blocks_are_joined_into_the_output_file(self):
        self._stub("curl", """
for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done
cat > "$out" <<'JSON'
{"content":[{"type":"text","text":"ISSUE-1 "},{"type":"text","text":"real bug"}]}
JSON
printf 200
""")
        out = pathlib.Path(self.tmp) / "claude.txt"
        r = run_fn("direct_claude", self._prompt("debate this"), str(out),
                   env={"CLAUDE_CODE_OAUTH_TOKEN": "stub"}, path_prefix=str(self.bin))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out.read_text(), "ISSUE-1 real bug")

    def test_non_200_falls_back_to_the_cli(self):
        self._stub("curl", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\n: > "$out"\nprintf 401\n')
        self._stub("claude", 'cat > /dev/null; echo "from the cli"\n')
        out = pathlib.Path(self.tmp) / "claude.txt"
        r = run_fn("direct_claude", self._prompt("debate this"), str(out),
                   env={"CLAUDE_CODE_OAUTH_TOKEN": "stub"}, path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "from the cli")
        self.assertIn("401", r.stderr)

    def test_a_stale_output_file_is_not_mistaken_for_this_run(self):
        """Same trap as the Codex seat; the guard is per-function, so test both."""
        self._stub("curl", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\n: > "$out"\nprintf 500\n')
        self._stub("claude", 'cat > /dev/null; echo "fresh"\n')
        out = pathlib.Path(self.tmp) / "claude.txt"
        out.write_text("STALE ANSWER FROM A PREVIOUS RUN")
        run_fn("direct_claude", self._prompt("debate this"), str(out),
               env={"CLAUDE_CODE_OAUTH_TOKEN": "stub"}, path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "fresh")

    def test_the_identity_line_is_present(self):
        """The OAuth path rejects a system prompt that omits it."""
        src = DIRECT.read_text()
        self.assertIn("You are Claude Code, Anthropic's official CLI for Claude.", src)

    def test_no_second_credential_source(self):
        """A chain can silently pick the revoked .credentials.json. One source only."""
        src = DIRECT.read_text()
        self.assertNotIn(".credentials.json", src)
        self.assertNotIn("find-generic-password", src)


ASSEMBLE = ROOT / "skills" / "tribunal-review" / "prompts" / "assemble.py"


class TestAssemblerTemplates(unittest.TestCase):
    def _write(self, name, text):
        p = pathlib.Path(tempfile.mkdtemp(prefix="tribunal-")) / name
        p.write_text(text)
        return str(p)

    def _run(self, *args):
        return subprocess.run(["python3", str(ASSEMBLE), *args],
                              capture_output=True, text=True)

    def test_debate_template_substitutes_its_own_placeholders(self):
        r = self._run("--template", "debate", "--class", "code",
                      "--contested", self._write("c.md", "ISSUE-3 disputed"),
                      "--code-context", self._write("d.diff", "--- a/x.py"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ISSUE-3 disputed", r.stdout)
        self.assertIn("--- a/x.py", r.stdout)
        self.assertNotIn("{contested_items}", r.stdout)
        self.assertNotIn("{code_context}", r.stdout)

    def test_rebuttal_template_substitutes_challenges(self):
        r = self._run("--template", "rebuttal", "--class", "code",
                      "--challenges", self._write("h.md", "you ignored the null case"),
                      "--code-context", self._write("d.diff", "--- a/x.py"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("you ignored the null case", r.stdout)
        self.assertNotIn("{challenges}", r.stdout)

    def test_review_template_is_still_the_default(self):
        """Task 1-3 must not change what Step 3 already sends."""
        r = self._run("--class", "code", "--reviewer", "Codex",
                      "--specialty", "BUG DETECTION",
                      "--content", self._write("t.diff", "--- a/x.py"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("HOW TO REVIEW (code targets", r.stdout)

    def test_a_template_without_a_focus_block_does_not_crash(self):
        """drop_block() indexes blindly; rebuttal.md has no FOCUS block."""
        r = self._run("--template", "rebuttal", "--class", "code",
                      "--challenges", self._write("h.md", "x"),
                      "--code-context", self._write("d.diff", "y"),
                      "--focus", "")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_review_without_content_is_an_error_not_an_empty_prompt(self):
        """--content was required=True before this change.

        Making it optional for debate/rebuttal must not let a review assemble
        with an empty target: the panel would return findings about nothing and
        the orchestrator could not tell that from a clean diff.
        """
        r = self._run("--class", "code", "--reviewer", "Codex",
                      "--specialty", "BUG DETECTION")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--content", r.stderr)

    def test_an_unsupplied_placeholder_does_not_leak_braces(self):
        """debate.md has no {challenges}; rebuttal.md has no {contested_items}.

        One substitution map serves all three templates, so every key is applied
        to every template. A key whose file was not given must vanish, not stay
        behind as a literal brace for the panelist to read as an instruction.
        """
        r = self._run("--template", "debate", "--class", "code",
                      "--contested", self._write("c.md", "ISSUE-3"),
                      "--code-context", self._write("d.diff", "z"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotRegex(r.stdout, r"\{[a-z_]+\}")


class TestSkillWiring(unittest.TestCase):
    def _step(self, heading):
        text = SKILL.read_text()
        start = text.index(heading)
        rest = text[start + len(heading):]
        nxt = re.search(r"\n## ", rest)
        return rest[: nxt.start()] if nxt else rest

    def test_step5_dispatches_through_direct_sh(self):
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        self.assertIn("direct.sh", step5)
        self.assertIn("direct_codex", step5)

    def test_step5_does_not_spawn_a_codex_cli(self):
        """The whole point: debate and rebuttal stop paying the CLI floor."""
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        self.assertNotIn("codex exec", step5)

    def test_step5_cursor_resumes_rather_than_starting_over(self):
        """Cursor cannot go direct, so it must at least not re-read the diff."""
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        self.assertIn('--resume "$CURSOR_CHAT"', step5)

    def test_review_round_still_gets_the_repository(self):
        """Mutation guard: this is the regression the whole design avoids."""
        step3 = self._step("## Step 3 — Launch the panel in parallel")
        self.assertIn('-C "$REPO_OR_WORKTREE"', step3)
        self.assertIn("codex exec -s read-only", step3)

    def test_every_file_step5_reads_is_written_first(self):
        """assemble.py reads --contested from disk and raises if it is absent.

        Step 4 merges findings into the orchestrator's own context, not into a
        file, so nothing produces contested.md unless Step 5 says to. A dangling
        path here does not degrade the debate round — it aborts it.
        """
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        for path in ("$SP/contested.md",):
            self.assertLess(step5.index(f'> "{path}"'), step5.index(f'--contested "{path}"'),
                            f"{path} is read before anything writes it")

    def test_preflight_runs_before_the_panel(self):
        text = SKILL.read_text()
        self.assertLess(text.index("direct_preflight"),
                        text.index("## Step 5 — Debate, then rebuttal"))


class TestCursorSession(unittest.TestCase):
    def test_step3_opens_one_chat(self):
        """One chat for the run; without it there is nothing to resume."""
        body = SKILL.read_text()
        start = body.index("## Step 3 — Launch the panel in parallel")
        step3 = body[start:body.index("\n## ", start + 1)]
        self.assertIn("create-chat", step3)
        self.assertIn("CURSOR_CHAT=", step3)

    def test_every_cursor_call_carries_resume_and_workspace(self):
        """A resumed turn with a different effective workspace forks the chat.

        --workspace defaults to cwd, so omitting it is harmless *when run from
        inside the workspace* — which is why the trap survives casual testing.
        The orchestrator's cwd is not $REPO_OR_WORKTREE, so here the default is
        wrong, the session forks with no error, and the panelist answers from an
        empty context: the confident fabricated file path review.md calls
        disqualifying. Measured 2026-09-02. Every call is checked, because the
        trap needs only one to miss it.
        """
        body = SKILL.read_text()
        # Scan by offset, not by str.index(line): the two invocations are
        # byte-identical, so index() would resolve both to the first and leave
        # the second — the one this trap actually bites — unchecked. And the
        # seat table names `cursor-agent -p` in a cell without invoking it.
        offsets, pos = [], 0
        for ln in body.splitlines(True):
            if ln.lstrip().startswith("cursor-agent -p"):
                offsets.append((pos, ln.strip()))
            pos += len(ln)
        self.assertEqual(len(offsets), 2,
                         f"expected review + debate invocations, got {len(offsets)}")
        for start, ln in offsets:
            block = body[start:start + 400]
            self.assertIn("--resume", block, f"no --resume near: {ln}")
            self.assertIn("--workspace", block, f"no --workspace near: {ln}")


if __name__ == "__main__":
    unittest.main()
