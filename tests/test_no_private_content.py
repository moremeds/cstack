"""This repo is public. A private marker reaching a commit is unfixable.

Deleting the file later does not help: the blob stays reachable in history and
GitHub indexes a public repo within minutes. So the check runs here, before the
commit, rather than as a review habit.

Extracted from a private config repo where exactly one line — a parenthetical
listing four project names — was the only thing standing between the ruleset and
publication. The rules themselves were always generic; the objects they applied
to were not. That distinction is what this test enforces.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Add your own before publishing: employer, private orgs, internal hostnames.
FORBIDDEN = [
    (r"/Users/(?!\$|<)[a-z]", "an absolute home path leaks the local username"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "a bare IP address may be internal infrastructure"),
    (r"[\w.+-]+@[\w-]+\.[\w.]+", "an email address"),
    (r"git@github\.com:[\w-]+/", "an SSH remote names the org and repo"),
]
ALLOW = {"127.0.0.1", "0.0.0.0", "255.255.255.255", "8.8.8.8"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".worktrees"}


def tracked_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            yield p


class TestNoPrivateContent(unittest.TestCase):
    def test_no_forbidden_patterns(self):
        hits = []
        for p in tracked_files():
            if p.name == Path(__file__).name:
                continue  # this file names the patterns it bans
            try:
                text = p.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                for pat, why in FORBIDDEN:
                    for m in re.finditer(pat, line):
                        if m.group(0) in ALLOW:
                            continue
                        rel = p.relative_to(ROOT)
                        hits.append(f"{rel}:{n}: {m.group(0)!r} — {why}")
        self.assertEqual([], hits, "private content would be published:\n" + "\n".join(hits))


class TestCodexGlobalRules(unittest.TestCase):
    def test_rtk_rule_is_an_explicit_bullet_without_import(self):
        agents = (ROOT / "rules" / "AGENTS.md").read_text()
        rule = (
            r"(?m)^- shell 命令始终使用 `rtk` 前缀，减少无关输出；"
            r"遇到不支持或必须保留原始输出的命令，使用 `rtk proxy <command>`。$"
        )
        self.assertRegex(agents, rule)
        self.assertNotRegex(agents, r"(?m)^\s*@")


if __name__ == "__main__":
    unittest.main()
