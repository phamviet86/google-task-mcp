from __future__ import annotations

import json
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from googleapiclient.errors import HttpError

import google_tasks_mcp.google as google_module
from google_tasks_mcp.google import (
    api_num_retries,
    get_tasks_client,
    google_error,
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


def test_api_retries_default_override_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_NUM_RETRIES", raising=False)
    assert api_num_retries() == 3

    monkeypatch.setenv("GOOGLE_API_NUM_RETRIES", "5")
    assert api_num_retries() == 5

    for invalid in ("-1", "11", "not-an-integer"):
        monkeypatch.setenv("GOOGLE_API_NUM_RETRIES", invalid)
        with pytest.raises(RuntimeError, match="integer from 0 to 10"):
            api_num_retries()


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


def test_tasks_client_is_built_fresh_for_each_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")
    credentials = SimpleNamespace(expired=False)
    services: list[object] = []

    monkeypatch.setattr(google_module, "token_path", lambda: token)
    monkeypatch.setattr(
        google_module.Credentials,
        "from_authorized_user_file",
        lambda *_args, **_kwargs: credentials,
    )

    def fake_build(*_args: Any, **_kwargs: Any) -> object:
        service = object()
        services.append(service)
        return service

    monkeypatch.setattr(google_module, "build", fake_build)

    first = get_tasks_client()
    second = get_tasks_client()

    assert first is services[0]
    assert second is services[1]
    assert first is not second


def test_expired_credentials_refresh_once_and_are_atomically_persisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token = tmp_path / "protected" / "token.json"
    token.parent.mkdir()
    token.write_text(json.dumps({"expired": True}), encoding="utf-8")
    refresh_calls: list[object] = []
    closed_sessions: list[bool] = []
    built_credentials: list[object] = []

    class RefreshableCredentials:
        refresh_token = "refresh-token"

        def __init__(self, expired: bool) -> None:
            self.expired = expired

        def refresh(self, request: object) -> None:
            refresh_calls.append(request)
            self.expired = False

        def to_json(self) -> str:
            return json.dumps({"expired": self.expired, "refresh_token": self.refresh_token})

    class FakeSession:
        def close(self) -> None:
            closed_sessions.append(True)

    class FakeRefreshRequest:
        def __init__(self) -> None:
            self.session = FakeSession()

    def load_credentials(*_args: Any, **_kwargs: Any) -> RefreshableCredentials:
        payload = json.loads(token.read_text(encoding="utf-8"))
        return RefreshableCredentials(expired=payload["expired"])

    def fake_build(*_args: Any, **kwargs: Any) -> object:
        built_credentials.append(kwargs["credentials"])
        return object()

    monkeypatch.setattr(google_module, "token_path", lambda: token)
    monkeypatch.setattr(google_module.Credentials, "from_authorized_user_file", load_credentials)
    monkeypatch.setattr(google_module, "GoogleAuthRequest", FakeRefreshRequest)
    monkeypatch.setattr(google_module, "build", fake_build)

    with ThreadPoolExecutor(max_workers=2) as executor:
        services = list(executor.map(lambda _index: get_tasks_client(), range(2)))

    assert services[0] is not services[1]
    assert len(refresh_calls) == 1
    assert closed_sessions == [True]
    assert len(built_credentials) == 2
    assert all(not credentials.expired for credentials in built_credentials)
    assert json.loads(token.read_text(encoding="utf-8"))["expired"] is False
    assert stat.S_IMODE(token.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(token.stat().st_mode) == 0o600


@pytest.mark.parametrize("failure_stage", ["refresh", "persist"])
def test_refresh_failure_does_not_build_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure_stage: str
) -> None:
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")
    session_closed: list[bool] = []
    build_calls: list[bool] = []
    persist_calls: list[bool] = []

    class ExpiredCredentials:
        expired = True
        refresh_token = "refresh-token"

        def refresh(self, _request: object) -> None:
            if failure_stage == "refresh":
                raise ValueError("refresh failed")

    class FakeSession:
        def close(self) -> None:
            session_closed.append(True)

    class FakeRefreshRequest:
        def __init__(self) -> None:
            self.session = FakeSession()

    def fail_persist(*_args: Any, **_kwargs: Any) -> Path:
        persist_calls.append(True)
        if failure_stage == "persist":
            raise OSError("persist failed")
        raise AssertionError("persist must not run after refresh failure")

    def unexpected_build(*_args: Any, **_kwargs: Any) -> object:
        build_calls.append(True)
        return object()

    monkeypatch.setattr(google_module, "token_path", lambda: token)
    monkeypatch.setattr(
        google_module.Credentials,
        "from_authorized_user_file",
        lambda *_args, **_kwargs: ExpiredCredentials(),
    )
    monkeypatch.setattr(google_module, "GoogleAuthRequest", FakeRefreshRequest)
    monkeypatch.setattr(google_module, "save_authorized_user_token", fail_persist)
    monkeypatch.setattr(google_module, "build", unexpected_build)

    with pytest.raises(RuntimeError, match="Failed to refresh and persist"):
        get_tasks_client()

    assert session_closed == [True]
    assert build_calls == []
    assert persist_calls == ([] if failure_stage == "refresh" else [True])


def test_expired_credentials_without_refresh_token_do_not_build_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")
    credentials = SimpleNamespace(expired=True, refresh_token=None)
    build_calls: list[bool] = []

    monkeypatch.setattr(google_module, "token_path", lambda: token)
    monkeypatch.setattr(
        google_module.Credentials,
        "from_authorized_user_file",
        lambda *_args, **_kwargs: credentials,
    )
    monkeypatch.setattr(
        google_module,
        "build",
        lambda *_args, **_kwargs: build_calls.append(True),
    )

    with pytest.raises(RuntimeError, match="expired and have no refresh token"):
        get_tasks_client()

    assert build_calls == []


def test_google_error_uses_public_http_error_fields() -> None:
    response = SimpleNamespace(status=429, reason="Too Many Requests")
    content = json.dumps(
        {
            "error": {
                "message": "Quota exceeded",
                "errors": [{"domain": "usageLimits", "reason": "rateLimitExceeded"}],
            }
        }
    ).encode()
    error = HttpError(response, content)  # type: ignore[arg-type]

    assert google_error(error) == (
        "Google Tasks API error (429): Quota exceeded; details: "
        '[{"domain": "usageLimits", "reason": "rateLimitExceeded"}]'
    )
