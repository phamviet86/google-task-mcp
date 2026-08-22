from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.types import CallToolRequestParams

from google_tasks_mcp.server import (
    TOOL_SPECS,
    call_tool_with_client,
    normalize_due_date,
)


class FakeRequest:
    def __init__(self, result: Any) -> None:
        self.result = result

    def execute(self) -> Any:
        return self.result


class FakeCollection:
    def __init__(self, collection: str, calls: list[tuple[str, str, dict[str, Any]]]) -> None:
        self.collection = collection
        self.calls = calls

    def _request(self, operation: str, arguments: dict[str, Any]) -> FakeRequest:
        self.calls.append((self.collection, operation, arguments))
        if operation == "list":
            item_key = "taskLists" if self.collection == "tasklists" else "tasks"
            return FakeRequest({"items": [{"id": item_key}], "nextPageToken": "next"})
        if operation in {"delete", "clear"}:
            return FakeRequest(None)
        return FakeRequest({"id": f"{self.collection}-{operation}", **arguments.get("body", {})})

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
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.tasklist_collection = FakeCollection("tasklists", self.calls)
        self.task_collection = FakeCollection("tasks", self.calls)

    def tasklists(self) -> FakeCollection:
        return self.tasklist_collection

    def tasks(self) -> FakeCollection:
        return self.task_collection


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
    assert client.calls == []


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
