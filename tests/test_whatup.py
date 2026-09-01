"""whatup's failure mode is a command that reports nothing and reads as clean.

Both assertions are mutation-checked: each must fail on a tree where the
contract it protects has been broken. The skill exists to catch false-clean
status reports, so a grounding block that can itself produce one is the one
defect that makes the whole skill lie confidently.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WHATUP = ROOT / "skills" / "whatup" / "SKILL.md"


class TestWhatupGroundingCannotReportFalseClean(unittest.TestCase):
    def setUp(self):
        self.body = WHATUP.read_text()
        start = self.body.index("## Step 1")
        self.step1 = self.body[start:self.body.index("## Step 2")]
        # The commands, without the prose explaining the traps. Scoping to the
        # whole section instead flags the sentence "Never pipe `git status
        # --short` through `head`" as the very defect it warns against.
        block = self.step1.split("```bash", 1)[1]
        self.commands = block.split("```", 1)[0]

    def test_gh_failure_is_never_suppressed(self):
        """`gh ... 2>/dev/null` makes "not logged in" and "no PR" identical."""
        for line in self.commands.splitlines():
            if line.strip().startswith("gh "):
                self.assertNotIn("2>/dev/null", line,
                                 f"a suppressed stderr turns a gh failure into a silent 'no PR': {line.strip()}")
        self.assertIn("unverified", self.step1.lower(),
                      "nothing tells the readout to mark PR/CI unverified on failure")

    def test_dirty_file_list_is_not_truncated(self):
        """`git status --short | head` drops files section 7 must report."""
        for line in self.commands.splitlines():
            if line.strip().startswith("git status --short"):
                self.assertNotIn("head", line,
                                 f"dirty-file list is truncated: {line.strip()}")

    def test_push_state_does_not_rest_on_status_alone(self):
        """`git status -sb` prints bare `## main` with no upstream — verified."""
        self.assertIn("rev-parse --abbrev-ref '@{upstream}'", self.commands,
                      "push state inferred from status alone reports a false clean "
                      "for work that never left the machine")
        for line in self.commands.splitlines():
            self.assertNotIn("origin/HEAD..", line,
                             f"that range means 'not in the default branch', "
                             f"not 'not pushed': {line.strip()}")


class TestWhatupIsPortable(unittest.TestCase):
    """Codex scans ~/.agents/skills/ and Claude Code ~/.claude/skills/; skills/
    is the one tree an installer fans into both. A Claude-only surface, or
    frontmatter naming Claude tools, silently halves the audience."""

    def test_lives_in_the_portable_tree(self):
        self.assertTrue(WHATUP.exists(), f"{WHATUP} missing — did it move?")
        self.assertEqual(WHATUP.parent.parent.name, "skills")

    def test_frontmatter_is_runtime_neutral(self):
        head = WHATUP.read_text()[:1400]
        self.assertTrue(head.startswith("---\n"), "no frontmatter block")
        self.assertIn("name: whatup", head)
        self.assertIn("description:", head)
        frontmatter = WHATUP.read_text().split("---", 2)[1]
        self.assertNotIn("allowed-tools:", frontmatter,
                         "frontmatter constrains the skill to Claude Code tools")


if __name__ == "__main__":
    unittest.main()
