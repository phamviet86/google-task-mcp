from __future__ import annotations

import asyncio
import json
import logging
import threading
from types import SimpleNamespace
from typing import Any

import pytest
from googleapiclient.errors import HttpError
from mcp.types import CallToolRequestParams

from google_tasks_mcp.server import (
    TOOL_SPECS,
    call_tool_with_client,
    normalize_due_date,
)


class FakeRequest:
    def __init__(
        self,
        result: Any,
        executions: list[int],
        owner_thread: int | None,
    ) -> None:
        self.result = result
        self.executions = executions
        self.owner_thread = owner_thread

    def execute(self, *, num_retries: int = 0) -> Any:
        if self.owner_thread is not None:
            assert threading.get_ident() == self.owner_thread
        self.executions.append(num_retries)
        return self.result


class FakeCollection:
    def __init__(
        self,
        collection: str,
        calls: list[tuple[str, str, dict[str, Any]]],
        executions: list[int],
        owner_thread: int | None,
    ) -> None:
        self.collection = collection
        self.calls = calls
        self.executions = executions
        self.owner_thread = owner_thread

    def _request(self, operation: str, arguments: dict[str, Any]) -> FakeRequest:
        self.calls.append((self.collection, operation, arguments))
        if operation == "list":
            item_key = "taskLists" if self.collection == "tasklists" else "tasks"
            return FakeRequest(
                {"items": [{"id": item_key}], "nextPageToken": "next"},
                self.executions,
                self.owner_thread,
            )
        if operation in {"delete", "clear"}:
            return FakeRequest(None, self.executions, self.owner_thread)
        return FakeRequest(
            {"id": f"{self.collection}-{operation}", **arguments.get("body", {})},
            self.executions,
            self.owner_thread,
        )

    def list(self, **arguments: Any) -> FakeRequest:
        return self._request("list", arguments)

    def get(self, **arguments: Any) -> FakeRequest:
        return self._request("get", arguments)

    def insert(self, **arguments: Any) -> FakeRequest:
        return self._request("insert", arguments)

    def patch(self, **arguments: Any) -> FakeRequest:
        return self._request("patch", arguments)

    def delete(self, **arguments: Any) -> FakeRequest:
        return self._request("delete", arguments)

    def move(self, **arguments: Any) -> FakeRequest:
        return self._request("move", arguments)

    def clear(self, **arguments: Any) -> FakeRequest:
        return self._request("clear", arguments)


class FakeClient:
    def __init__(self, *, enforce_thread_ownership: bool = False) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.executions: list[int] = []
        self.close_threads: list[int] = []
        self.owner_thread = threading.get_ident() if enforce_thread_ownership else None
        self.tasklist_collection = FakeCollection(
            "tasklists", self.calls, self.executions, self.owner_thread
        )
        self.task_collection = FakeCollection(
            "tasks", self.calls, self.executions, self.owner_thread
        )

    def tasklists(self) -> FakeCollection:
        return self.tasklist_collection

    def tasks(self) -> FakeCollection:
        return self.task_collection

    def close(self) -> None:
        current_thread = threading.get_ident()
        if self.owner_thread is not None:
            assert current_thread == self.owner_thread
        self.close_threads.append(current_thread)


def call(name: str, arguments: dict[str, Any], client: FakeClient) -> tuple[bool, Any]:
    result = asyncio.run(
        call_tool_with_client(
            CallToolRequestParams(name=name, arguments=arguments),
            client_factory=lambda: client,  # type: ignore[return-value]
        )
    )
    text = result.content[0].text
    return result.is_error, json.loads(text) if not result.is_error else text


def test_exact_fourteen_tool_contract() -> None:
    assert list(TOOL_SPECS) == [
        "list_task_lists",
        "get_task_list",
        "create_task_list",
        "update_task_list",
        "delete_task_list",
        "list_tasks",
        "get_task",
        "create_task",
        "update_task",
        "complete_task",
        "reopen_task",
        "move_task",
        "delete_task",
        "clear_completed_tasks",
    ]
    assert len(TOOL_SPECS) == 14
    for name in ("delete_task_list", "delete_task", "clear_completed_tasks"):
        schema = TOOL_SPECS[name].input_model.model_json_schema()
        assert schema["properties"]["confirm"]["const"] is True
        assert TOOL_SPECS[name].annotations.destructive_hint is True
    update_schema = TOOL_SPECS["update_task"].input_model.model_json_schema()
    assert update_schema["properties"]["title"]["type"] == "string"
    assert "anyOf" not in update_schema["properties"]["title"]
    assert "null" not in update_schema["properties"]["status"]["enum"]


def test_all_fourteen_tools_dispatch_successfully() -> None:
    client = FakeClient()
    calls = {
        "list_task_lists": {"max_results": 25, "page_token": "page"},
        "get_task_list": {"task_list_id": "list-1"},
        "create_task_list": {"title": "Created"},
        "update_task_list": {"task_list_id": "list-1", "title": "Renamed"},
        "delete_task_list": {"task_list_id": "list-1", "confirm": True},
        "list_tasks": {
            "task_list_id": "list-1",
            "due_min": "2026-08-01T00:00:00Z",
            "show_completed": False,
        },
        "get_task": {"task_list_id": "list-1", "task_id": "task-1"},
        "create_task": {
            "task_list_id": "list-1",
            "title": "Created task",
            "notes": "Notes",
            "due": "2026-08-22",
            "parent_task_id": "parent-1",
            "previous_task_id": "previous-1",
        },
        "update_task": {
            "task_list_id": "list-1",
            "task_id": "task-1",
            "title": "Updated task",
        },
        "complete_task": {"task_list_id": "list-1", "task_id": "task-1"},
        "reopen_task": {"task_list_id": "list-1", "task_id": "task-1"},
        "move_task": {
            "task_list_id": "list-1",
            "task_id": "task-1",
            "destination_task_list_id": "list-2",
            "parent_task_id": "parent-2",
            "previous_task_id": "previous-2",
        },
        "delete_task": {"task_list_id": "list-1", "task_id": "task-1", "confirm": True},
        "clear_completed_tasks": {"task_list_id": "list-1", "confirm": True},
    }

    for name, arguments in calls.items():
        is_error, _result = call(name, arguments, client)
        assert not is_error, name

    assert len(client.calls) == 14
    assert client.calls[0] == (
        "tasklists",
        "list",
        {"maxResults": 25, "pageToken": "page"},
    )
    assert client.executions == [3] * 14
    assert len(client.close_threads) == 14


def test_update_preserves_omitted_fields_and_explicit_null_clears() -> None:
    client = FakeClient()
    is_error, _result = call(
        "update_task",
        {"task_list_id": "list-1", "task_id": "task-1", "title": "Only title"},
        client,
    )
    assert not is_error
    assert client.calls[-1][2]["body"] == {"title": "Only title"}

    is_error, _result = call(
        "update_task",
        {
            "task_list_id": "list-1",
            "task_id": "task-1",
            "notes": None,
            "due": None,
        },
        client,
    )
    assert not is_error
    assert client.calls[-1][2]["body"] == {"notes": None, "due": None}


def test_validation_rejects_unsafe_or_ambiguous_calls() -> None:
    client = FakeClient()
    is_error, message = call(
        "delete_task",
        {"task_list_id": "list-1", "task_id": "task-1", "confirm": False},
        client,
    )
    assert is_error
    assert "confirm" in message

    is_error, message = call("update_task", {"task_list_id": "list-1", "task_id": "task-1"}, client)
    assert is_error
    assert "at least one field" in message

    is_error, message = call(
        "list_tasks",
        {"task_list_id": "list-1", "due_min": "2026-08-22T09:00:00"},
        client,
    )
    assert is_error
    assert "timezone offset" in message

    for field_name in ("title", "status"):
        is_error, message = call(
            "update_task",
            {"task_list_id": "list-1", "task_id": "task-1", field_name: None},
            client,
        )
        assert is_error
        assert field_name in message

    assert client.calls == []


def test_each_tool_call_builds_and_uses_client_in_one_worker_thread() -> None:
    clients: list[FakeClient] = []
    main_thread = threading.get_ident()

    def factory() -> FakeClient:
        client = FakeClient(enforce_thread_ownership=True)
        clients.append(client)
        return client

    async def run_calls() -> list[Any]:
        return await asyncio.gather(
            call_tool_with_client(
                CallToolRequestParams(name="list_task_lists", arguments={}),
                client_factory=factory,  # type: ignore[arg-type]
            ),
            call_tool_with_client(
                CallToolRequestParams(name="list_task_lists", arguments={}),
                client_factory=factory,  # type: ignore[arg-type]
            ),
        )

    results = asyncio.run(run_calls())

    assert all(not result.is_error for result in results)
    assert len(clients) == 2
    assert clients[0] is not clients[1]
    assert all(client.owner_thread != main_thread for client in clients)
    assert all(client.executions == [3] for client in clients)
    assert all(client.close_threads == [client.owner_thread] for client in clients)


def test_native_retry_override_is_passed_to_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_NUM_RETRIES", "5")
    client = FakeClient()

    is_error, _result = call("list_task_lists", {}, client)

    assert not is_error
    assert client.executions == [5]


def test_http_errors_are_mapped_and_logged_without_stdout(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    response = SimpleNamespace(status=503, reason="Service Unavailable")
    error = HttpError(
        response,  # type: ignore[arg-type]
        b'{"error":{"message":"Backend unavailable","details":"retry later"}}',
    )

    class FailingRequest:
        def execute(self, *, num_retries: int = 0) -> Any:
            assert num_retries == 3
            raise error

    class FailingCollection:
        def list(self, **_arguments: Any) -> FailingRequest:
            return FailingRequest()

    class FailingClient:
        def __init__(self) -> None:
            self.owner_thread = threading.get_ident()
            self.close_threads: list[int] = []

        def tasklists(self) -> FailingCollection:
            return FailingCollection()

        def tasks(self) -> FailingCollection:
            return FailingCollection()

        def close(self) -> None:
            current_thread = threading.get_ident()
            assert current_thread == self.owner_thread
            self.close_threads.append(current_thread)

    clients: list[FailingClient] = []

    def factory() -> FailingClient:
        client = FailingClient()
        clients.append(client)
        return client

    with caplog.at_level(logging.ERROR):
        result = asyncio.run(
            call_tool_with_client(
                CallToolRequestParams(name="list_task_lists", arguments={}),
                client_factory=factory,  # type: ignore[arg-type]
            )
        )

    assert result.is_error
    assert result.content[0].text == (
        "Google Tasks API error (503): Backend unavailable; details: retry later"
    )
    assert "Google Tasks tool list_task_lists failed with HttpError" in caplog.text
    assert capsys.readouterr().out == ""
    assert len(clients) == 1
    assert clients[0].close_threads == [clients[0].owner_thread]


def test_due_normalization_is_calendar_safe_and_utc() -> None:
    assert normalize_due_date("2026-08-22") == "2026-08-22T00:00:00.000Z"
    assert normalize_due_date("2026-08-22T07:00:00+07:00") == "2026-08-22T00:00:00.000Z"
    assert normalize_due_date(None) is None

    try:
        normalize_due_date("2026-02-30")
    except ValueError as error:
        assert "calendar date" in str(error)
    else:
        raise AssertionError("invalid calendar date was accepted")
