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

    def test_the_identity_line_is_present(self):
        """The OAuth path rejects a system prompt that omits it."""
        src = DIRECT.read_text()
        self.assertIn("You are Claude Code, Anthropic's official CLI for Claude.", src)

    def test_no_second_credential_source(self):
        """A chain can silently pick the revoked .credentials.json. One source only."""
        src = DIRECT.read_text()
        self.assertNotIn(".credentials.json", src)
        self.assertNotIn("find-generic-password", src)


if __name__ == "__main__":
    unittest.main()
