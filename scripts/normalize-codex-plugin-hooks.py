#!/usr/bin/env python3
"""Normalize Codex plugin hook configs in the runtime cache.

Claude plugin hook files may include top-level metadata such as `description`.
Codex's hook loader currently accepts only a top-level `hooks` object, so this
script strips unsupported top-level metadata from cache copies while preserving
the hook definitions themselves.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


HOME = Path.home()


def normalize_hooks(root: Path, dry_run: bool = False) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if not root.exists():
        return rows
    for path in sorted(root.glob("**/hooks/hooks.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(data, dict) or "hooks" not in data:
            continue
        extra = sorted(set(data) - {"hooks"})
        if not extra:
            continue
        rows.append((str(path.relative_to(root)), ",".join(extra)))
        if dry_run:
            continue
        path.write_text(json.dumps({"hooks": data["hooks"]}, indent=2) + "\n")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=HOME / ".codex/plugins/cache",
        help="Codex plugin cache root",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = normalize_hooks(args.root, dry_run=args.dry_run)
    if not rows:
        print("No Codex plugin hook metadata to normalize.")
        return
    for rel, removed in rows:
        action = "would normalize" if args.dry_run else "normalized"
        print(f"{action}\t{rel}\tremoved={removed}")


if __name__ == "__main__":
    main()
