#!/usr/bin/env python3
"""Supply shared global rules when Cursor cannot load them from ancestors."""

import json
import sys
from pathlib import Path

request = json.load(sys.stdin)
roots = request.get("workspace_roots", [])
if not isinstance(roots, list) or any(not isinstance(root, str) for root in roots):
    raise ValueError("workspace_roots must be a list of paths")

rules = Path.home() / "AGENTS.md"
# ponytail: mixed roots can repeat context; replace with native global loading if supported.
loaded = bool(roots) and all(
    any(
        (parent / "AGENTS.md").resolve() == rules.resolve()
        for parent in (root.absolute(), *root.absolute().parents)
    )
    for root in map(Path, roots)
)
print(json.dumps({} if loaded else {"additional_context": rules.read_text()}))
