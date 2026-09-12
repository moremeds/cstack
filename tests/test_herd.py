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


CLI_REF = HERD / "references" / "herdr-cli.md"
HERDR_VERBS = {
    "agent list", "agent get", "agent read", "agent send-keys", "agent prompt",
    "agent rename", "agent wait", "agent start", "agent explain",
    "pane split", "pane run", "pane wait-output", "pane read", "pane layout", "pane close",
    "workspace list", "machine list", "integration status", "integration install",
    "status",
}
VERB_RE = re.compile(r"herdr ((?:agent|pane|workspace|machine|integration) [a-z-]+|status)\b")


def cited_verbs(text):
    return set(VERB_RE.findall(text))


class TestCliReference(unittest.TestCase):
    def setUp(self):
        self.body = CLI_REF.read_text()

    def test_pinned_to_a_version(self):
        self.assertRegex(self.body, r"herdr 0\.9\.0")

    def test_every_cited_verb_exists(self):
        unknown = cited_verbs(self.body) - HERDR_VERBS
        self.assertEqual(unknown, set(), f"verbs not in herdr 0.9.0: {unknown}")

    def test_hyphenated_subcommands(self):
        for bad in ("send_keys", "wait_output", "sendkeys"):
            self.assertNotIn(bad, self.body)

    def test_reverse_channel_documented(self):
        """The worker prompts the lead's pane; herdr's own docs never say so."""
        self.assertIn("HERDR_PANE_ID", self.body)
        self.assertRegex(self.body, r"agent prompt \S*\$?\{?LEAD", )

    def test_waits_for_shell_prompt_before_start(self):
        self.assertIn("agent_pane_busy", self.body)
        self.assertLess(self.body.index("pane wait-output"), self.body.index("agent start implementer"))

    def test_restart_after_rule_change(self):
        self.assertIn("inject their rules at startup", self.body)

    def test_blocked_is_not_auto_answered(self):
        blocked = self.body[self.body.index("## blocked"):]
        self.assertNotIn("send-keys reviewer y", blocked)
        self.assertIn("ask the user", blocked)


CONTRACT = HERD / "references" / "execution-contract.md"
REPORT_LINE = "herd-report <worker> task <n>: commit <sha>, evidence <path>, deviations: <text|none>"


class TestContract(unittest.TestCase):
    def setUp(self):
        self.body = CONTRACT.read_text()

    def test_review_gate_rule_present(self):
        self.assertIn("Stop after every task", self.body)
        self.assertIn("Do not start the next task until", self.body)

    def test_report_format_is_exact(self):
        self.assertIn(REPORT_LINE, self.body)

    def test_rejected_work_fixed_on_top(self):
        self.assertIn("fix on top", self.body)
        self.assertIn("never rewrite", self.body)

    def test_lead_pane_slot(self):
        self.assertIn("LEAD_PANE", self.body)

    def test_preapproved_prompts_slot(self):
        self.assertIn("<pre-approved prompts", self.body)


SKILL = HERD / "SKILL.md"


class TestSkill(unittest.TestCase):
    def setUp(self):
        self.body = SKILL.read_text()

    def test_frontmatter(self):
        self.assertTrue(self.body.startswith("---\nname: herd\n"))

    def test_three_transports_in_decision_order(self):
        sec = self.body[self.body.index("## 2. Choose a transport"):]
        sec = sec[:sec.index("## 3.")]
        order = [sec.index(k) for k in ("peer session", "herdr agent", "native subagent")]
        self.assertEqual(order, sorted(order), "decision order is peer → herdr → native")

    def test_gate_falls_back_to_orchestrate(self):
        self.assertIn('test "${HERDR_ENV:-}" = 1', self.body)
        self.assertIn("`orchestrate`", self.body)

    def test_cites_only_real_herdr_verbs(self):
        unknown = cited_verbs(self.body) - HERDR_VERBS
        self.assertEqual(unknown, set())

    def test_uses_contract_report_line(self):
        self.assertIn("herd-report", self.body)
        self.assertIn("herd-continue", self.body)
        self.assertIn("herd-reject", self.body)

    def test_never_messages_working_session(self):
        self.assertIn("never message a session whose status is `working`", self.body)

    def test_blocked_surfaced_not_answered(self):
        self.assertIn("show the user the dialog", self.body)
        self.assertNotIn("send-keys reviewer y", self.body)

    def test_roster_args_and_restart_rule(self):
        self.assertIn("`args`", self.body)
        self.assertIn("restart", self.body)

    def test_same_setup_precondition(self):
        self.assertIn("same rules, skills, and memory", self.body)

    def test_links_orchestrate_team_design(self):
        self.assertIn("orchestrate/SKILL.md", self.body)

    def test_under_250_lines(self):
        self.assertLessEqual(self.body.count("\n"), 250)


if __name__ == "__main__":
    unittest.main()
