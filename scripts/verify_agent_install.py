#!/usr/bin/env python3
"""Verify a clean installed wheel can install its self-contained agent skills."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

SKILLS = ("google-tasks-setup", "google-tasks")


def run(*command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    command = args.command.absolute()
    with tempfile.TemporaryDirectory(prefix="google-tasks-mcp-skills-") as temporary:
        root = Path(temporary)
        skills = root / "skills with spaces"
        base = (str(command), "install-skills", "--dest", str(skills))
        run(*base, "--dry-run", cwd=root)
        assert not skills.exists()
        run(*base, cwd=root)
        run(*base, cwd=root)
        run(*base, "--check", cwd=root)
        for skill in SKILLS:
            runtime = json.loads((skills / skill / "references/runtime.json").read_text())
            assert runtime["version"] == args.version
            for key in ("python", "server", "auth"):
                assert Path(runtime[key]).is_absolute()
                assert Path(runtime[key]).is_file()
            run(runtime["server"], "--version", cwd=root)
            run(runtime["auth"], "--version", cwd=root)
    print(f"installed-wheel skills passed: {command.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
