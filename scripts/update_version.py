#!/usr/bin/env python3
"""Synchronize project version metadata for semantic-release."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def update_pyproject(version: str) -> None:
    """Update the version field inside pyproject.toml."""
    pyproject_path = ROOT / "pyproject.toml"
    contents = pyproject_path.read_text(encoding="utf-8")
    pattern = re.compile(r'^(version\s*=\s*")(?P<ver>[^"\\]+)("\s*)$', re.MULTILINE)

    def _replace(match: re.Match[str]) -> str:
        return f"{match.group(1)}{version}{match.group(3)}"

    updated, count = pattern.subn(_replace, contents, count=1)
    if count != 1:
        raise RuntimeError("Unable to locate version field in pyproject.toml")

    pyproject_path.write_text(updated, encoding="utf-8")


def update_frontend_package(version: str) -> bool:
    """Optionally update frontend/package.json if it exists."""
    package_path = ROOT / "frontend" / "package.json"
    if not package_path.exists():
        return False

    data = json.loads(package_path.read_text(encoding="utf-8"))
    data["version"] = version
    package_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: update_version.py <version>")

    version = sys.argv[1]
    update_pyproject(version)
    frontend_updated = update_frontend_package(version)

    updated_targets = ["pyproject.toml"]
    if frontend_updated:
        updated_targets.append("frontend/package.json")

    print("Updated versions:", ", ".join(updated_targets))


if __name__ == "__main__":
    main()
