from __future__ import annotations

import argparse
from collections.abc import Callable

import pytest

from google_tasks_mcp import auth, server


@pytest.mark.parametrize(
    ("parser", "program"),
    [
        (auth.parser, "google-tasks-mcp-auth"),
    ],
)
def test_cli_version(
    parser: Callable[[], argparse.ArgumentParser],
    program: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        parser().parse_args(["--version"])
    assert raised.value.code == 0
    assert capsys.readouterr().out == f"{program} 0.4.0\n"


def test_server_main_version(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["google-tasks-mcp", "--version"])
    with pytest.raises(SystemExit) as raised:
        server.main()
    assert raised.value.code == 0
    assert capsys.readouterr().out == "google-tasks-mcp 0.4.0\n"


def test_doctor_cli_reports_structured_readiness(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["google-tasks-mcp", "doctor"])
    monkeypatch.setattr(
        "google_tasks_mcp.readiness.doctor",
        lambda: {"ok": False, "authentication": "unverified"},
    )
    with pytest.raises(SystemExit) as raised:
        server.main()
    assert raised.value.code == 2
    assert '"authentication": "unverified"' in capsys.readouterr().out
