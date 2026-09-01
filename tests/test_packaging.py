"""Release metadata that must stay aligned with the importable package."""

from __future__ import annotations

import tomllib
from pathlib import Path

from google_tasks_mcp import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_distribution_identity_version_and_maintainer_metadata() -> None:
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert metadata["name"] == "phamviet-google-tasks-mcp"
    assert metadata["version"] == "0.3.0"
    assert __version__ == metadata["version"]
    assert metadata["license"] == "MIT"
    assert metadata["maintainers"] == [
        {"name": "phamviet86", "email": "phamquangviet@bingoenglish.edu.vn"}
    ]
    assert metadata["requires-python"] == ">=3.11"
    assert {
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    }.issubset(metadata["classifiers"])


def test_console_scripts_and_typed_marker_are_packaged() -> None:
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert metadata["scripts"] == {
        "google-tasks-mcp": "google_tasks_mcp.server:main",
        "google-tasks-mcp-auth": "google_tasks_mcp.auth:main",
    }
    assert (PROJECT_ROOT / "src" / "google_tasks_mcp" / "py.typed").is_file()
