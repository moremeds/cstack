"""herd's failure mode is a stale verb or a dropped rule, not a crash.

Every assertion is mutation-checked: it must fail on a tree where the
contract it protects has been broken.
"""

import re
import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
HERD = ROOT / "skills" / "herd"
ROSTER = HERD / "herd.example.toml"

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")  # herdr live-agent name rule
KINDS = {
    "pi",
    "claude",
    "codex",
    "gemini",
    "cursor",
    "devin",
    "agy",
    "cline",
    "omp",
    "mastracode",
    "opencode",
    "copilot",
    "kimi",
    "kiro",
    "droid",
    "amp",
    "grok",
    "hermes",
    "kilo",
    "qodercli",
    "qwen",
    "maki",
    "muse",
}  # `herdr agent` help, 0.9.0


class TestRoster(unittest.TestCase):
    def setUp(self):
        self.doc = tomllib.loads(ROSTER.read_text())

    def test_workers_have_required_keys(self):
        for w in self.doc["worker"]:
            for key in ("name", "kind", "role", "machine"):
                self.assertIn(key, w, f"worker {w} lacks {key}")

    def test_names_are_valid_and_unique(self):
        names = [w["name"] for w in self.doc["worker"]]
        for n in names:
            self.assertRegex(n, NAME_RE)
        self.assertEqual(len(names), len(set(names)))

    def test_kinds_are_real_herdr_kinds(self):
        for w in self.doc["worker"]:
            self.assertIn(w["kind"], KINDS)

    def test_args_are_lists(self):
        for w in self.doc["worker"]:
            if "args" in w:
                self.assertIsInstance(w["args"], list, w["name"])

    def test_interactive_kinds_preapprove_reads(self):
        """Devin blocks on read-only `ls` without this; Cursor on any command."""
        flags = {"devin": "--permission-mode", "cursor": "--force"}
        for w in self.doc["worker"]:
            if w["kind"] in flags:
                self.assertIn(flags[w["kind"]], w.get("args", []), w["name"])

    def test_no_peer_whitelist(self):
        """Spec: peers are the whole ecosystem, discovered live, never listed."""
        self.assertNotIn("peer", self.doc)


if __name__ == "__main__":
    unittest.main()
