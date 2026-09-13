from __future__ import annotations

import stat
from pathlib import Path

import pytest

from google_tasks_mcp import readiness


def test_doctor_missing_token_is_local_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token = tmp_path / "private" / "missing.json"
    monkeypatch.setattr(readiness, "token_path", lambda: token)
    result = readiness.doctor()
    assert not result["ok"]
    assert result["authentication"] == result["mcp_discovery"] == "unverified"
    assert result["checks"]["token_file_exists"] is False
    assert "does not read credentials" in result["note"]


def test_doctor_does_not_read_present_token_or_claim_authentication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token = tmp_path / "token.json"
    token.write_text("not parsed")
    token.chmod(0o600)
    monkeypatch.setattr(readiness, "token_path", lambda: token)
    result = readiness.doctor()
    assert result["ok"]
    assert result["authentication"] == "unverified"
    assert result["checks"] == {
        "token_path_is_absolute": True,
        "token_parent_exists": True,
        "token_parent_is_directory": True,
        "token_parent_is_not_symlink": True,
        "token_parent_owner_only": True,
        "token_file_exists": True,
        "token_file_is_regular": True,
        "token_file_is_not_symlink": True,
        "token_file_owned_by_current_user": True,
        "token_file_owner_readable": True,
        "token_file_owner_only": True,
    }


def test_doctor_rejects_symlink_or_permissive_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "target"
    target.write_text("fixture")
    token = tmp_path / "token.json"
    token.symlink_to(target)
    monkeypatch.setattr(readiness, "token_path", lambda: token)
    result = readiness.doctor()
    assert not result["ok"] and not result["checks"]["token_file_is_not_symlink"]
    token.unlink()
    token.write_text("fixture")
    token.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
    result = readiness.doctor()
    assert not result["ok"] and not result["checks"]["token_file_owner_only"]


def test_doctor_reports_relative_configuration_as_not_ready(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    token = Path("relative-token.json")
    token.write_text("fixture")
    token.chmod(0o600)
    monkeypatch.setattr(readiness, "token_path", lambda: token)
    result = readiness.doctor()
    assert not result["ok"]
    assert not result["checks"]["token_path_is_absolute"]
    assert any("absolute" in action for action in result["actions"])
