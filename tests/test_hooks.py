import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HookContractTests(unittest.TestCase):
    def test_rtk_rewrite_updated_input_allows_permission(self):
        hook = ROOT / "hooks" / "rtk-rewrite.sh"
        payload = {
            "tool_input": {"command": "ls -la"},
            "cwd": str(ROOT),
        }

        result = subprocess.run(
            ["bash", str(hook)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        response = json.loads(result.stdout)
        output = response["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertIn("updatedInput", output)
        self.assertEqual(output["permissionDecision"], "allow")


if __name__ == "__main__":
    unittest.main()
