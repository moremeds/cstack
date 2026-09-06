"""Contract tests for the tribunal's direct API transport.

The suite never makes a network call: every seat is exercised against a stubbed
`curl` on PATH. Liveness was verified by hand during design and is recorded in
the plan's Verification section; CI has no credentials.
"""

import base64
import json
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
    e["CLAUDE_CODE_OAUTH_TOKEN"] = "test-token-not-a-credential"
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
        self.home = self._fixture_home()

    def _fixture_home(self):
        """A fake $HOME so the suite never reads the developer's credentials.

        direct_codex parses ~/.codex/auth.json for a bearer token and digs the
        account id out of that JWT's payload. Run against a real HOME the tests
        pass only on a machine that happens to be logged in — which is how a
        suite that must never need credentials came to need them.
        """
        home = pathlib.Path(self.tmp) / "home"
        (home / ".codex").mkdir(parents=True)
        claims = {"https://api.openai.com/auth": {"chatgpt_account_id": "acct-test"}}
        payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
        jwt = b"header." + payload + b".signature"
        (home / ".codex" / "auth.json").write_text(
            json.dumps({"tokens": {"access_token": jwt.decode()}}))
        return home

    def _stub(self, name, body):
        p = self.bin / name
        p.write_text("#!/usr/bin/env bash\n" + body)
        p.chmod(0o755)

    def _prompt(self, text):
        p = pathlib.Path(self.tmp) / "p.md"
        p.write_text(text)
        return str(p)


class TestCredentialsStayOffTheCommandLine(unittest.TestCase):
    """argv is world-readable on this machine.

    `ps` shows every argument of every process, so a bearer token passed as
    -H "authorization: Bearer $tok" and a prompt passed as -d "$body" are
    visible to any other local process for as long as curl runs. The body is
    the whole diff under review.
    """

    def test_no_header_or_body_is_passed_as_an_argument(self):
        src = DIRECT.read_text()
        for bad in ('-H "authorization:', "-H 'authorization:", '-d "$body"'):
            self.assertNotIn(bad, src, f"credential or payload in argv: {bad}")

    def test_headers_and_body_come_from_files(self):
        src = DIRECT.read_text()
        self.assertIn("--config", src, "headers must come from a curl config file")
        self.assertIn("--data-binary @", src, "body must be read from a file")


class TestCurlIsBounded(unittest.TestCase):
    """Without a deadline a black-holed connection never reaches the fallback.

    The fallback is guarded on curl returning; a stalled TLS handshake keeps
    command substitution open indefinitely, so the seat neither answers nor
    degrades — the whole panel waits on it.
    """

    def test_both_calls_set_connect_and_total_timeouts(self):
        src = DIRECT.read_text()
        self.assertEqual(src.count("--connect-timeout"), 2)
        self.assertEqual(src.count("--max-time"), 2)


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
        self._stub("codex", 'echo "codex-cli 0.153.4"\n')
        self._stub("curl", f"""
for a in "$@"; do
  [ "$prev" = "-o" ] && out=$a
  [ "$prev" = "--data-binary" ] && cp "${{a#@}}" "{self.tmp}/request.json"
  [ "$prev" = "--config" ] && cp "$a" "{self.tmp}/headers.txt"
  prev=$a
done
cat > "$out" <<'SSE'
{sse}
SSE
printf 200
""")
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", self._prompt("review this"), str(out),
                   env={"HOME": str(self.home), "TRIBUNAL_CODEX_MODEL": ""}, path_prefix=str(self.bin))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out.read_text(), "ISSUE-1 real bug")

        request = json.loads((pathlib.Path(self.tmp) / "request.json").read_text())
        self.assertEqual(request["model"], "gpt-6-astra")
        self.assertEqual(request["reasoning"], {"effort": "low"})
        self.assertIn("codex_cli_rs/0.153.4", (pathlib.Path(self.tmp) / "headers.txt").read_text())

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
               env={"HOME": str(self.home)}, path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "fresh")

    def test_an_incomplete_stream_falls_back_instead_of_truncating(self):
        """A truncated report is non-empty, so emptiness cannot detect it.

        The stream can end in response.incomplete (max output tokens) after
        emitting real deltas. Those deltas are a partial review: the first few
        ISSUE blocks present, the rest simply gone. Accepting it counts the seat
        as having reported, so the missing findings never reach the merge and
        nobody can tell a short review from a clean one.
        """
        sse = (
            'data: {"type":"response.output_text.delta","delta":"ISSUE-1 first"}\n'
            'data: {"type":"response.incomplete"}\n'
        )
        self._stub("curl", f"""
for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done
cat > "$out" <<'SSE'
{sse}
SSE
printf 200
""")
        self._stub("codex", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\necho "from the cli" > "$out"\n')
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", self._prompt("review this"), str(out),
                   env={"HOME": str(self.home)}, path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "from the cli")
        self.assertIn("incomplete", r.stderr)

    def test_a_completed_stream_is_accepted(self):
        """The guard must not reject the normal case."""
        sse = ('data: {"type":"response.output_text.delta","delta":"ISSUE-1 ok"}\n'
               'data: {"type":"response.completed"}\n')
        self._stub("curl", f"""
for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done
cat > "$out" <<'SSE'
{sse}
SSE
printf 200
""")
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", self._prompt("review this"), str(out),
                   env={"HOME": str(self.home)}, path_prefix=str(self.bin))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out.read_text(), "ISSUE-1 ok")

    def test_unreadable_auth_falls_back_instead_of_returning(self):
        """An auth failure is a dead seat, and a dead seat must degrade.

        `tok=$(_codex_token) || return 1` returned before the fallback could
        run, so a machine with no ~/.codex/auth.json lost the seat entirely
        rather than spending a CLI spawn. Raised by both panel seats.

        This also runs the seat with HOME pointed at an empty directory, which
        is how the suite proves it needs no real credentials.
        """
        home = pathlib.Path(self.tmp) / "empty-home"
        home.mkdir()
        self._stub("codex", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\necho "from the cli" > "$out"\n')
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", self._prompt("review this"), str(out),
                   env={"HOME": str(home)}, path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "from the cli")
        self.assertIn("auth", r.stderr.lower())

    def test_non_200_falls_back_to_the_cli(self):
        """A dead seat silently changes the consensus arithmetic. It must not."""
        self._stub("curl", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\n: > "$out"\nprintf 429\n')
        self._stub("codex", f'''if [ "$1" = "--version" ]; then echo "codex-cli 0.153.4"; exit; fi
printf '%s\\n' "$@" > "{self.tmp}/cli-args.txt"
for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done
echo "from the cli" > "$out"
''')
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", self._prompt("review this"), str(out),
                   env={"HOME": str(self.home), "TRIBUNAL_CODEX_MODEL": "gpt-6-astra"}, path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "from the cli")
        self.assertIn("429", r.stderr)

        args = (pathlib.Path(self.tmp) / "cli-args.txt").read_text().splitlines()
        self.assertEqual(args[args.index("-m") + 1], "gpt-6-astra")
        self.assertEqual(args[args.index("-c") + 1], 'model_reasoning_effort="low"')


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

    def test_a_max_tokens_stop_reason_falls_back(self):
        """Anthropic reports truncation in stop_reason, not in the HTTP status."""
        self._stub("curl", """
for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done
cat > "$out" <<'JSON'
{"stop_reason":"max_tokens","content":[{"type":"text","text":"ISSUE-1 first"}]}
JSON
printf 200
""")
        self._stub("claude", 'cat > /dev/null; echo "from the cli"\n')
        out = pathlib.Path(self.tmp) / "claude.txt"
        r = run_fn("direct_claude", self._prompt("debate this"), str(out),
                   env={"CLAUDE_CODE_OAUTH_TOKEN": "stub"}, path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "from the cli")
        self.assertIn("max_tokens", r.stderr)

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

    def test_step5_seats_one_peer_not_both(self):
        """Step 0: the panel is everyone else, so exactly one peer is yours.

        Dispatching direct_codex and direct_claude together seats a panelist of
        the orchestrator's own lineage. It never reviewed in Step 3, so it
        debates findings it never made, and its weight double-counts the
        lineage the 1.0/0.90 split exists to keep independent.
        """
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        # Invocations only: the comment above the call names both functions on
        # purpose, because the orchestrator has to know which one is theirs.
        # Per round there is one peer call, and across rounds it must stay the
        # same function: mixing them seats two lineages on one panel.
        fns = {ln.split()[0] for ln in step5.splitlines()
               if ln.lstrip().startswith(("direct_codex ", "direct_claude "))}
        self.assertEqual(len(fns), 1, f"expected one peer lineage, got {sorted(fns)}")

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
        for path, flag in (("$SP/contested.md", "--contested"),
                           ("$SP/challenges.md", "--challenges")):
            self.assertLess(step5.index(f'> "{path}"'), step5.index(f'{flag} "{path}"'),
                            f"{path} is read before anything writes it")

    def test_step5_waits_before_reading_backgrounded_output(self):
        """Both rounds background their seats; unwaited files are empty.

        Reading debate output to build the rebuttal without waiting produces an
        empty challenges list, and the rebuttal round then asks every seat to
        answer nothing — which looks exactly like a round where no one had
        anything to say.
        """
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        self.assertGreaterEqual(step5.count('wait "$P"'), 2,
                                "each round must wait for its seats")
        self.assertLess(step5.index('wait "$P"'), step5.index("challenges.md"),
                        "challenges are collected before the debate seats finish")

    def test_the_review_round_never_adopts_the_direct_transport(self):
        """The one invariant the whole design exists to protect.

        Asserting Step 3 still *has* the CLI is not enough: an edit that adds
        direct_codex beside it — "use the direct transport everywhere" — passes
        every other test while removing the repo access that grounds review.md's
        "a wrong file path or line number discredits every other finding you
        make". Debate and rebuttal go direct because they read no files. Review
        does, and that is the difference the round split is made of.
        """
        step3 = self._step("## Step 3 — Launch the panel in parallel")
        for fn in ("direct_codex", "direct_claude"):
            self.assertNotIn(fn, step3)

    def test_preflight_never_aborts_the_run(self):
        """quick and solo never call the transport, and nothing here is fatal.

        `exit 1` on a debate-only credential killed a quick review that would
        have completed — the panel's own CRITICAL against this PR. And since
        every seat falls back to its CLI, even a deep run degrades rather than
        dies, so aborting is wrong in every mode.
        """
        text = SKILL.read_text()
        line = [l for l in text.splitlines() if "direct_preflight" in l and "||" in l]
        self.assertTrue(line, "preflight is not invoked with a failure branch")
        self.assertNotIn("exit 1", line[0])

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
        # review, debate, rebuttal — every one of them, because the fork needs
        # only a single turn to miss the flag.
        self.assertGreaterEqual(len(offsets), 3,
                                f"expected a cursor turn per round, got {len(offsets)}")
        for start, ln in offsets:
            block = body[start:start + 400]
            self.assertIn("--resume", block, f"no --resume near: {ln}")
            self.assertIn("--workspace", block, f"no --workspace near: {ln}")


if __name__ == "__main__":
    unittest.main()
