"""Install the packaged Google Tasks setup and usage skills safely."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any

from . import __version__

SKILLS = ("google-tasks-setup", "google-tasks")
MANIFEST = ".google-tasks-mcp-managed.json"
DISTRIBUTION = "phamviet-google-tasks-mcp"


def default_skill_root() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return (
        Path(configured).expanduser() / "skills"
        if configured
        else Path.home() / ".agents" / "skills"
    )


def _digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _runtime() -> bytes:
    # Do not resolve this path: a venv interpreter may be a symlink to system Python.
    python = Path(sys.executable).absolute()
    server = python.parent / "google-tasks-mcp"
    auth = python.parent / "google-tasks-mcp-auth"
    if not server.is_file() or not auth.is_file():
        raise RuntimeError("install the distribution in this Python environment before its skills")
    return (
        json.dumps(
            {
                "distribution": DISTRIBUTION,
                "version": __version__,
                "python": str(python),
                "server": str(server),
                "auth": str(auth),
            },
            indent=2,
        )
        + "\n"
    ).encode()


def _safe_relative(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and value != MANIFEST


def _managed_files(target: Path, skill: str) -> dict[str, str] | None:
    marker = target / MANIFEST
    if marker.is_symlink():
        return None
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        files = payload["files"]
        if (
            payload["distribution"] != DISTRIBUTION
            or payload["skill"] != skill
            or not isinstance(files, dict)
            or not files
        ):
            return None
        if not all(
            isinstance(path, str) and _safe_relative(path) and isinstance(digest, str)
            for path, digest in files.items()
        ):
            return None
        return files
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _files(skill: str) -> dict[str, bytes]:
    root = resources.files("google_tasks_mcp").joinpath("skills", skill)
    files: dict[str, bytes] = {}

    def collect(item: Any, prefix: str = "") -> None:
        for child in item.iterdir():
            name = prefix + child.name
            if child.is_dir():
                collect(child, name + "/")
            elif child.is_file():
                files[name] = child.read_bytes()

    collect(root)
    files["references/runtime.json"] = _runtime()
    manifest = {
        "distribution": DISTRIBUTION,
        "skill": skill,
        "files": {path: _digest(contents) for path, contents in sorted(files.items())},
    }
    files[MANIFEST] = (json.dumps(manifest, indent=2) + "\n").encode()
    return files


def _has_symlink(target: Path) -> bool:
    return target.is_symlink() or any(item.is_symlink() for item in target.rglob("*"))


def _state(
    target: Path, skill: str, expected: dict[str, bytes], *, replace: bool
) -> tuple[str, str]:
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        return "conflict", "target is a symlink or file"
    if not target.exists():
        return "missing", ""
    if _has_symlink(target):
        return "conflict", "target contains a symlink"
    previous = _managed_files(target, skill)
    if previous is None:
        return "conflict", "existing directory is not managed by this installer"
    previous_paths = set(previous)
    expected_paths = set(expected) - {MANIFEST}
    for path in previous_paths | expected_paths | {MANIFEST}:
        candidate = target / path
        for parent in candidate.parents:
            if parent == target:
                break
            if parent.exists() and not parent.is_dir():
                return "conflict", "a managed path parent is occupied by a file"
        if candidate.exists() and not candidate.is_file():
            return "conflict", "managed file path is occupied by a directory"
    for path in expected_paths - previous_paths:
        if (target / path).exists():
            return "conflict", "an unmanaged file occupies a packaged skill path"
    if (
        all(
            (target / path).is_file() and (target / path).read_bytes() == contents
            for path, contents in expected.items()
        )
        and previous_paths == expected_paths
    ):
        return "unchanged", ""
    if replace:
        return "replace", ""
    return "conflict", "managed content differs; review then use --replace"


def install_skills(
    destination: Path | None = None,
    *,
    check: bool = False,
    dry_run: bool = False,
    replace: bool = False,
) -> tuple[dict[str, Any], int]:
    root = (destination or default_skill_root()).expanduser().absolute()
    report: dict[str, Any] = {
        "destination": str(root),
        "mode": "check" if check else ("dry-run" if dry_run else "install"),
        "skills": [],
    }
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        return {
            **report,
            "ok": False,
            "error": "skill root must be a directory, not a symlink or file",
        }, 2

    plans: list[tuple[str, Path, dict[str, bytes], dict[str, str] | None, str]] = []
    for skill in SKILLS:
        target = root / skill
        expected = _files(skill)
        state, reason = _state(target, skill, expected, replace=replace)
        previous = (
            _managed_files(target, skill) if target.is_dir() and not target.is_symlink() else None
        )
        plans.append((skill, target, expected, previous, state))
        entry: dict[str, str] = {"name": skill, "state": state}
        if reason:
            entry["reason"] = reason
        report["skills"].append(entry)

    blocked = any(plan[-1] == "conflict" for plan in plans)
    report["ok"] = not blocked and (not check or all(plan[-1] == "unchanged" for plan in plans))
    if blocked:
        report["message"] = (
            "No skills changed. Unmanaged or symlinked destinations are never replaced; "
            "different managed files require review and --replace."
        )
    if blocked or check or dry_run:
        return report, 0 if report["ok"] else 2

    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".google-tasks-skills-", dir=root) as temporary:
        temporary_root = Path(temporary)
        prepared: list[tuple[str, Path, Path, Path, str]] = []
        for skill, target, expected, previous, state in plans:
            if state == "unchanged":
                continue
            staged = temporary_root / skill
            backup = temporary_root / f"{skill}.previous"
            if target.exists():
                shutil.copytree(target, staged)
                for path in previous or {}:
                    if path not in expected:
                        candidate = staged / path
                        if candidate.exists():
                            candidate.unlink()
            else:
                staged.mkdir()
            for path, contents in expected.items():
                candidate = staged / path
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_bytes(contents)
            current, _reason = _state(target, skill, expected, replace=replace)
            if current != state:
                raise RuntimeError(f"skill changed during installation: {target}")
            prepared.append((skill, target, staged, backup, state))
        changed: list[tuple[Path, Path]] = []
        try:
            for _skill, target, staged, backup, _state_value in prepared:
                if target.exists():
                    target.rename(backup)
                try:
                    staged.rename(target)
                except OSError:
                    if backup.exists() and not target.exists():
                        backup.rename(target)
                    raise
                changed.append((target, backup))
        except Exception:
            for target, backup in reversed(changed):
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                if backup.exists():
                    backup.rename(target)
            raise
        for skill, _target, _staged, _backup, state in prepared:
            item = next(entry for entry in report["skills"] if entry["name"] == skill)
            item["state"] = "replaced" if state == "replace" else "installed"
    return report, 0
