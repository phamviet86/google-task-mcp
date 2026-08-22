from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

import pytest

from google_tasks_mcp.google import (
    load_client_secrets,
    save_authorized_user_token,
    token_path,
)


class FakeCredentials:
    refresh_token = "refresh-token"

    def to_json(self) -> str:
        return json.dumps(
            {
                "type": "authorized_user",
                "client_id": "client-id",
                "client_secret": "client-secret",
                "refresh_token": self.refresh_token,
            }
        )


def test_token_path_default_and_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GOOGLE_TOKEN_FILE", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert token_path() == tmp_path / ".config" / "google-tasks-mcp" / "token.json"

    override = tmp_path / "private" / "tasks.json"
    monkeypatch.setenv("GOOGLE_TOKEN_FILE", str(override))
    assert token_path() == override


def test_client_secret_requires_desktop_shape(tmp_path: Path) -> None:
    valid = tmp_path / "valid.json"
    valid.write_text(
        json.dumps({"installed": {"client_id": "id", "client_secret": "secret"}}),
        encoding="utf-8",
    )
    assert load_client_secrets(valid) == {"client_id": "id", "client_secret": "secret"}

    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"web": {"client_id": "id"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Desktop client"):
        load_client_secrets(invalid)


def test_authorized_user_token_is_written_atomically_with_owner_only_mode(tmp_path: Path) -> None:
    destination = tmp_path / "protected" / "token.json"
    result = save_authorized_user_token(FakeCredentials(), destination)  # type: ignore[arg-type]
    assert result == destination
    assert stat.S_IMODE(destination.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    payload: dict[str, Any] = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["type"] == "authorized_user"
