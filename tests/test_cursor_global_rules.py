import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CursorGlobalRulesTests(unittest.TestCase):
    def test_context_is_injected_only_when_not_loaded_from_ancestors(self):
        script = Path(__file__).resolve().parents[1] / "hooks/cursor-global-rules.py"
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            (home / "AGENTS.md").write_text("Shared instructions.\n")
            project = home / "project"
            project.mkdir()
            outside = Path(tmp) / "outside"
            outside.mkdir()
            for roots, expected in [
                ([str(project)], {}),
                ([str(outside)], {"additional_context": "Shared instructions.\n"}),
                ([str(outside), str(project)], {"additional_context": "Shared instructions.\n"}),
                ([], {"additional_context": "Shared instructions.\n"}),
            ]:
                with self.subTest(roots=roots):
                    result = subprocess.run(
                        [sys.executable, str(script)],
                        input=json.dumps({"workspace_roots": roots}),
                        env={**os.environ, "HOME": str(home)},
                        capture_output=True, text=True, check=True,
                    )
                    self.assertEqual(json.loads(result.stdout), expected)
