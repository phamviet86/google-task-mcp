from __future__ import annotations

import asyncio
import re
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from googleapiclient.discovery import Resource
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
    ToolAnnotations,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from . import __version__
from .google import get_tasks_client, google_error, json_result

TaskClientFactory = Callable[[], Resource]
ToolHandler = Callable[[str, dict[str, Any], Resource], Awaitable[Any]]

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1024)]
Notes = Annotated[str, StringConstraints(max_length=8192)]
Status = Literal["needsAction", "completed"]

READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
WRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
IDEMPOTENT_WRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListTaskListsInput(ToolInput):
    max_results: int = Field(default=100, ge=1, le=100)
    page_token: str | None = None


class TaskListIdInput(ToolInput):
    task_list_id: NonEmptyString = Field(
        description="Google task list ID; obtain it from list_task_lists"
    )


class CreateTaskListInput(ToolInput):
    title: Title


class UpdateTaskListInput(TaskListIdInput):
    title: Title


class DeleteTaskListInput(TaskListIdInput):
    confirm: Literal[True] = Field(
        description="Must be true after the user explicitly confirms deletion"
    )


class ListTasksInput(TaskListIdInput):
    max_results: int = Field(default=100, ge=1, le=100)
    page_token: str | None = None
    show_completed: bool = True
    show_deleted: bool = False
    show_hidden: bool = False
    due_min: str | None = None
    due_max: str | None = None
    completed_min: str | None = None
    completed_max: str | None = None
    updated_min: str | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> ListTasksInput:
        for field_name in (
            "due_min",
            "due_max",
            "completed_min",
            "completed_max",
            "updated_min",
        ):
            value = getattr(self, field_name)
            if value is not None:
                validate_rfc3339(value, field_name)
        return self


class TaskIdInput(TaskListIdInput):
    task_id: NonEmptyString = Field(description="Google task ID; obtain it from list_tasks")


class CreateTaskInput(TaskListIdInput):
    title: Title
    notes: Notes | None = None
    due: str | None = Field(
        default=None,
        description=(
            "Due date as YYYY-MM-DD or RFC 3339. Google Tasks stores only the date "
            "and discards the time."
        ),
    )
    parent_task_id: NonEmptyString | None = None
    previous_task_id: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_due(self) -> CreateTaskInput:
        if self.due is not None:
            normalize_due_date(self.due)
        return self


class UpdateTaskInput(TaskIdInput):
    title: Title | None = None
    notes: Notes | None = None
    due: str | None = Field(
        default=None,
        description="Use null to clear the due date; otherwise use YYYY-MM-DD or RFC 3339.",
    )
    status: Status | None = None

    @model_validator(mode="after")
    def validate_update(self) -> UpdateTaskInput:
        mutable_fields = {"title", "notes", "due", "status"}
        if not self.model_fields_set.intersection(mutable_fields):
            raise ValueError("Provide at least one field to update")
        if "due" in self.model_fields_set and self.due is not None:
            normalize_due_date(self.due)
        return self


class MoveTaskInput(TaskIdInput):
    destination_task_list_id: NonEmptyString | None = None
    parent_task_id: NonEmptyString | None = None
    previous_task_id: NonEmptyString | None = None


class DeleteTaskInput(TaskIdInput):
    confirm: Literal[True] = Field(
        description="Must be true after the user explicitly confirms deletion"
    )


class ClearCompletedTasksInput(TaskListIdInput):
    confirm: Literal[True] = Field(
        description="Must be true after the user explicitly confirms clearing completed tasks"
    )


@dataclass(frozen=True)
class ToolSpec:
    description: str
    input_model: type[ToolInput]
    annotations: ToolAnnotations


TOOL_SPECS: dict[str, ToolSpec] = {
    "list_task_lists": ToolSpec(
        "List the authenticated user's Google task lists.",
        ListTaskListsInput,
        READ_ONLY,
    ),
    "get_task_list": ToolSpec("Get one Google task list by ID.", TaskListIdInput, READ_ONLY),
    "create_task_list": ToolSpec("Create a Google task list.", CreateTaskListInput, WRITE),
    "update_task_list": ToolSpec(
        "Rename a Google task list.", UpdateTaskListInput, IDEMPOTENT_WRITE
    ),
    "delete_task_list": ToolSpec(
        "Permanently delete a Google task list. Requires explicit confirmation.",
        DeleteTaskListInput,
        DESTRUCTIVE,
    ),
    "list_tasks": ToolSpec(
        "List tasks in a Google task list with filters and pagination.",
        ListTasksInput,
        READ_ONLY,
    ),
    "get_task": ToolSpec("Get one task by task-list ID and task ID.", TaskIdInput, READ_ONLY),
    "create_task": ToolSpec(
        "Create a task, optionally as a subtask or after a sibling.", CreateTaskInput, WRITE
    ),
    "update_task": ToolSpec(
        "Patch a task's title, notes, due date, or status. Use null to clear notes or due.",
        UpdateTaskInput,
        IDEMPOTENT_WRITE,
    ),
    "complete_task": ToolSpec("Mark a task completed.", TaskIdInput, IDEMPOTENT_WRITE),
    "reopen_task": ToolSpec(
        "Mark a completed task as needing action again.", TaskIdInput, IDEMPOTENT_WRITE
    ),
    "move_task": ToolSpec(
        "Reorder a task, change its parent, or move it to another task list.",
        MoveTaskInput,
        WRITE,
    ),
    "delete_task": ToolSpec(
        "Permanently delete a task. Requires explicit confirmation.",
        DeleteTaskInput,
        DESTRUCTIVE,
    ),
    "clear_completed_tasks": ToolSpec(
        "Hide all completed tasks in a list. Requires explicit confirmation.",
        ClearCompletedTasksInput,
        DESTRUCTIVE,
    ),
}


def validate_rfc3339(value: str, field_name: str = "timestamp") -> datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a valid RFC 3339 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return parsed


def normalize_due_date(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as error:
            raise ValueError("due must be a valid calendar date") from error
        return f"{value}T00:00:00.000Z"
    parsed = validate_rfc3339(value, "due")
    normalized = parsed.astimezone(UTC).isoformat(timespec="milliseconds")
    return normalized.replace("+00:00", "Z")


async def execute_request(request: Any) -> Any:
    return await asyncio.to_thread(request.execute)


async def execute_tool(name: str, arguments: dict[str, Any], client: Resource) -> Any:
    tasklists = client.tasklists()
    tasks = client.tasks()

    if name == "list_task_lists":
        list_arguments: dict[str, Any] = {"maxResults": arguments.get("max_results", 100)}
        if "page_token" in arguments:
            list_arguments["pageToken"] = arguments["page_token"]
        result = await execute_request(tasklists.list(**list_arguments))
        return {
            "task_lists": result.get("items", []),
            "next_page_token": result.get("nextPageToken"),
        }
    if name == "get_task_list":
        return await execute_request(tasklists.get(tasklist=arguments["task_list_id"]))
    if name == "create_task_list":
        return await execute_request(tasklists.insert(body={"title": arguments["title"]}))
    if name == "update_task_list":
        return await execute_request(
            tasklists.patch(tasklist=arguments["task_list_id"], body={"title": arguments["title"]})
        )
    if name == "delete_task_list":
        await execute_request(tasklists.delete(tasklist=arguments["task_list_id"]))
        return {"deleted": True, "task_list_id": arguments["task_list_id"]}
    if name == "list_tasks":
        api_arguments: dict[str, Any] = {
            "tasklist": arguments["task_list_id"],
            "maxResults": arguments.get("max_results", 100),
            "showCompleted": arguments.get("show_completed", True),
            "showDeleted": arguments.get("show_deleted", False),
            "showHidden": arguments.get("show_hidden", False),
        }
        for public_name, api_name in (
            ("page_token", "pageToken"),
            ("due_min", "dueMin"),
            ("due_max", "dueMax"),
            ("completed_min", "completedMin"),
            ("completed_max", "completedMax"),
            ("updated_min", "updatedMin"),
        ):
            if public_name in arguments:
                api_arguments[api_name] = arguments[public_name]
        result = await execute_request(tasks.list(**api_arguments))
        return {"tasks": result.get("items", []), "next_page_token": result.get("nextPageToken")}
    if name == "get_task":
        return await execute_request(
            tasks.get(tasklist=arguments["task_list_id"], task=arguments["task_id"])
        )
    if name == "create_task":
        body: dict[str, Any] = {"title": arguments["title"]}
        if "notes" in arguments:
            body["notes"] = arguments["notes"]
        if "due" in arguments:
            body["due"] = normalize_due_date(arguments["due"])
        insert_arguments: dict[str, Any] = {
            "tasklist": arguments["task_list_id"],
            "body": body,
        }
        if "parent_task_id" in arguments:
            insert_arguments["parent"] = arguments["parent_task_id"]
        if "previous_task_id" in arguments:
            insert_arguments["previous"] = arguments["previous_task_id"]
        return await execute_request(tasks.insert(**insert_arguments))
    if name == "update_task":
        body = {
            key: (normalize_due_date(value) if key == "due" else value)
            for key, value in arguments.items()
            if key in {"title", "notes", "due", "status"}
        }
        return await execute_request(
            tasks.patch(
                tasklist=arguments["task_list_id"],
                task=arguments["task_id"],
                body=body,
            )
        )
    if name in {"complete_task", "reopen_task"}:
        status = "completed" if name == "complete_task" else "needsAction"
        return await execute_request(
            tasks.patch(
                tasklist=arguments["task_list_id"],
                task=arguments["task_id"],
                body={"status": status},
            )
        )
    if name == "move_task":
        move_arguments: dict[str, Any] = {
            "tasklist": arguments["task_list_id"],
            "task": arguments["task_id"],
        }
        for public_name, api_name in (
            ("destination_task_list_id", "destinationTasklist"),
            ("parent_task_id", "parent"),
            ("previous_task_id", "previous"),
        ):
            if public_name in arguments:
                move_arguments[api_name] = arguments[public_name]
        return await execute_request(tasks.move(**move_arguments))
    if name == "delete_task":
        await execute_request(
            tasks.delete(tasklist=arguments["task_list_id"], task=arguments["task_id"])
        )
        return {
            "deleted": True,
            "task_list_id": arguments["task_list_id"],
            "task_id": arguments["task_id"],
        }
    if name == "clear_completed_tasks":
        await execute_request(tasks.clear(tasklist=arguments["task_list_id"]))
        return {"cleared": True, "task_list_id": arguments["task_list_id"]}
    raise ValueError(f"Unknown tool: {name}")


async def list_tools(
    _context: ServerRequestContext[Any], _params: PaginatedRequestParams | None
) -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name=name,
                description=spec.description,
                input_schema=spec.input_model.model_json_schema(),
                annotations=spec.annotations,
            )
            for name, spec in TOOL_SPECS.items()
        ]
    )


async def call_tool_with_client(
    params: CallToolRequestParams, client_factory: TaskClientFactory = get_tasks_client
) -> CallToolResult:
    spec = TOOL_SPECS.get(params.name)
    if spec is None:
        return CallToolResult(
            is_error=True,
            content=[TextContent(type="text", text=f"Unknown tool: {params.name}")],
        )
    try:
        model = spec.input_model.model_validate(params.arguments or {})
        arguments = model.model_dump(exclude_unset=True)
        result = await execute_tool(params.name, arguments, client_factory())
        return CallToolResult(content=[TextContent(type="text", text=json_result(result))])
    except (ValidationError, ValueError, RuntimeError) as error:
        return CallToolResult(
            is_error=True,
            content=[TextContent(type="text", text=google_error(error))],
        )
    except Exception as error:
        return CallToolResult(
            is_error=True,
            content=[TextContent(type="text", text=google_error(error))],
        )


async def call_tool(
    _context: ServerRequestContext[Any], params: CallToolRequestParams
) -> CallToolResult:
    return await call_tool_with_client(params)


def create_server() -> Server[Any]:
    return Server[Any](
        "google-tasks-mcp",
        version=__version__,
        instructions=(
            "Manage the authenticated user's Google Tasks. Resolve human names to IDs with "
            "list_task_lists/list_tasks before writes. Google Tasks due values are dates only; "
            "times are discarded. Ask the user before calling tools marked destructive."
        ),
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


async def serve() -> None:
    server = create_server()
    options = InitializationOptions(
        server_name="google-tasks-mcp",
        server_version=__version__,
        capabilities=server.get_capabilities(),
        instructions=server.instructions,
    )
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


def main() -> None:
    print("google-tasks-mcp running on stdio", file=sys.stderr)
    asyncio.run(serve())


if __name__ == "__main__":
    main()
