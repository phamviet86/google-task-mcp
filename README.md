# Google Tasks MCP

[![CI](https://github.com/phamviet86/google-task-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/phamviet86/google-task-mcp/actions/workflows/ci.yml)

## Overview

Google Tasks MCP is a local Python MCP server that lets compatible AI agents read and manage the
authenticated user's Google Tasks. It uses Google's official Tasks API, OAuth 2.0 Desktop App
credentials, and the MCP Python SDK over `stdio`.

This repository is one component of the Google Services MCP collection.

The Git repository is named `google-task-mcp` (singular), while the Python distribution and console
commands are named `google-tasks-mcp` (plural). The paths and commands below preserve those names.

The package is currently classified as Alpha in `pyproject.toml`.

## Features

- List, inspect, create, rename, and delete task lists.
- List and filter tasks with API pagination.
- Create, edit, complete, reopen, move, reorder, and delete tasks.
- Create and move subtasks using `parent` and `previous`.
- Hide completed tasks through Google Tasks' clear operation.
- Preserve the distinction between an omitted update field and explicit `null` used to clear
  `notes` or `due`.
- Publish MCP safety annotations and require explicit confirmation for destructive operations.
- Store the OAuth refresh token outside the repository with owner-only permissions.
- Run entirely on Python; Node.js is not required.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `list_task_lists` | List task lists |
| `get_task_list` | Get one task list |
| `create_task_list` | Create a task list |
| `update_task_list` | Rename a task list |
| `delete_task_list` | Delete a task list; requires `confirm: true` |
| `list_tasks` | List or filter tasks with pagination |
| `get_task` | Get one task |
| `create_task` | Create a task or subtask |
| `update_task` | Patch title, notes, due date, or status |
| `complete_task` | Mark a task completed |
| `reopen_task` | Mark a task as needing action |
| `move_task` | Reorder, reparent, or move a task to another list |
| `delete_task` | Delete a task; requires `confirm: true` |
| `clear_completed_tasks` | Clear completed tasks; requires `confirm: true` |

Google Tasks stores only the date portion of a due timestamp; the API discards a supplied
time-of-day. Task titles are limited to 1,024 characters and notes to 8,192 characters.

All input objects reject unknown fields. IDs and other required strings must be non-empty. The
complete input contract is:

| Tool | Arguments |
| --- | --- |
| `list_task_lists` | `max_results` (integer 1–100, default `100`), optional `page_token` |
| `get_task_list` | `task_list_id` |
| `create_task_list` | `title` (trimmed, 1–1,024 characters) |
| `update_task_list` | `task_list_id`, `title` (trimmed, 1–1,024 characters) |
| `delete_task_list` | `task_list_id`, literal `confirm: true` |
| `list_tasks` | `task_list_id`; `max_results` (integer 1–100, default `100`); optional `page_token`; `show_completed` (default `true`), `show_deleted` (default `false`), `show_hidden` (default `false`); optional `due_min`, `due_max`, `completed_min`, `completed_max`, and `updated_min` |
| `get_task` | `task_list_id`, `task_id` |
| `create_task` | `task_list_id`, `title`; optional `notes` (up to 8,192 characters), `due`, `parent_task_id`, and `previous_task_id` |
| `update_task` | `task_list_id`, `task_id`, and at least one of `title`, `notes`, `due`, or `status` (`needsAction` or `completed`) |
| `complete_task` | `task_list_id`, `task_id` |
| `reopen_task` | `task_list_id`, `task_id` |
| `move_task` | `task_list_id`, `task_id`; optional `destination_task_list_id`, `parent_task_id`, and `previous_task_id` |
| `delete_task` | `task_list_id`, `task_id`, literal `confirm: true` |
| `clear_completed_tasks` | `task_list_id`, literal `confirm: true` |

The five `list_tasks` time filters must be RFC 3339 timestamps with a timezone. A `due` value may
instead be `YYYY-MM-DD`; the server validates calendar dates and normalizes due values to UTC before
calling Google. To see tasks completed in Google's first-party clients, set both `show_completed`
and `show_hidden` to `true`.

For `update_task`, omit fields that should remain unchanged and use explicit `null` only to clear
`notes` or `due`. Explicit `null` for `title` or `status` is rejected before any Google API call.

List operations return `task_lists` or `tasks` plus `next_page_token`. Other successful operations
return Google's resource object, except deletes and clear, which return a small acknowledgement.
Results are JSON in MCP text content. Validation, authentication, and Google API failures are
returned as MCP tool errors. `clear_completed_tasks` uses Google Tasks' `clear` operation, which
hides completed tasks; it does not permanently delete each task.

## Requirements

- Python 3.11 or newer, matching `requires-python = ">=3.11"` in `pyproject.toml`. The examples
  below use Python 3.12 where an explicit interpreter is useful.
- `uv` or another Python package installer.
- A Google account.
- A Google Cloud project with the Google Tasks API enabled.
- A local MCP client that supports `stdio` servers.

## Installation

Clone the repository and install the development environment:

```bash
git clone https://github.com/phamviet86/google-task-mcp
cd google-task-mcp
uv sync --extra dev
```

To build wheel and source distributions:

```bash
uv build
```

For an immutable deployment, install a specific Git commit into a dedicated virtual environment:

```bash
uv venv --python /usr/bin/python3.12 /opt/google-tasks-mcp/venv
uv pip install \
  --python /opt/google-tasks-mcp/venv/bin/python \
  "git+https://github.com/phamviet86/google-task-mcp@<commit>"
```

The installed server entry point is `/opt/google-tasks-mcp/venv/bin/google-tasks-mcp`.

## Google Cloud and OAuth setup

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable **Google Tasks API** under **APIs & Services → Library**.
4. Configure the OAuth consent screen.
5. Under **APIs & Services → Credentials**, create an OAuth client ID with application type
   **Desktop app**.
6. Download the OAuth Desktop client JSON as `client_secret.json` and keep it protected outside
   this repository.

Authorize from a desktop that can open the browser consent flow:

```bash
uv run google-tasks-mcp-auth \
  --client-secret /secure/google/client_secret.json
```

The command accepts only a Google OAuth Desktop client JSON containing the top-level `installed`
object. It requests the full `https://www.googleapis.com/auth/tasks` scope because this server
exposes read and write operations. The token defaults to:

```text
~/.config/google-tasks-mcp/token.json
```

Later runs refresh expired credentials automatically. Refresh is guarded in-process so concurrent
tool calls do not refresh the same token repeatedly; the refreshed authorized-user token is
atomically persisted with owner-only permissions before the service is built. The same OAuth
Desktop client definition may be used to authorize another local application, but each service
should keep its own token with its exact scope. Do not reuse a broader Google Workspace token as
this service's token.

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOOGLE_TOKEN_FILE` | No | `~/.config/google-tasks-mcp/token.json` | Override the Google Tasks OAuth token path |
| `GOOGLE_API_NUM_RETRIES` | No | `3` | Native Google client retries per request; integer from `0` to `10` |

`~` is expanded in `GOOGLE_TOKEN_FILE`. A relative token override remains relative to the MCP
subprocess's working directory, so use an absolute path in client configuration. The retry value is
passed to every Google request as `execute(num_retries=...)`; the SDK applies randomized exponential
backoff. The default `3` means one initial attempt plus at most three retries. Set it to `0` to
disable retries.

For example, authorize and store the token at an explicit protected path:

```bash
GOOGLE_TOKEN_FILE=/secure/google/tasks-token.json \
uv run google-tasks-mcp-auth \
  --client-secret /secure/google/client_secret.json
```

Pass the same `GOOGLE_TOKEN_FILE` value to the MCP server. Never commit the OAuth client JSON or
generated token.

## Running the server

From the development checkout:

```bash
uv run google-tasks-mcp
```

`google-tasks-mcp` accepts no command-line arguments. The authorization helper accepts one required
argument, `--client-secret PATH`; use `google-tasks-mcp-auth --help` for its generated CLI help.

An MCP client normally launches the virtual-environment console script directly:

```text
/absolute/path/google-task-mcp/.venv/bin/google-tasks-mcp
```

The server always communicates over `stdio` and does not open a network port.

## MCP client configuration

Use absolute paths and restart the MCP client after changing its configuration.

### Codex

Add the server to `~/.codex/config.toml` or a trusted project `.codex/config.toml`:

```toml
[mcp_servers.google_tasks]
command = "/absolute/path/google-task-mcp/.venv/bin/google-tasks-mcp"

[mcp_servers.google_tasks.env]
GOOGLE_TOKEN_FILE = "/Users/you/.config/google-tasks-mcp/token.json"
GOOGLE_API_NUM_RETRIES = "3"
```

See the [official Codex MCP guide](https://developers.openai.com/codex/mcp) for current client
configuration details.

### Hermes Agent

Hermes reads MCP servers from `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  google_tasks:
    command: "/absolute/path/google-task-mcp/.venv/bin/google-tasks-mcp"
    args: []
    env:
      GOOGLE_TOKEN_FILE: "/Users/you/.config/google-tasks-mcp/token.json"
      GOOGLE_API_NUM_RETRIES: "3"
    timeout: 120
    connect_timeout: 30
```

Use the absolute token path directly in the server's `env` mapping. Do not enable
`supports_parallel_tool_calls` for the complete tool set because it includes writes to shared task
lists. See the
[official Hermes MCP guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/mcp.md).

### Generic MCP clients

For clients that use JSON configuration, the equivalent transport settings are:

```json
{
  "mcpServers": {
    "google_tasks": {
      "command": "/absolute/path/google-task-mcp/.venv/bin/google-tasks-mcp",
      "env": {
        "GOOGLE_TOKEN_FILE": "/secure/google/tasks-token.json",
        "GOOGLE_API_NUM_RETRIES": "3"
      }
    }
  }
}
```

Configuration syntax is client-specific; use the client's native MCP adapter rather than assuming
that every client accepts the same JSON shape.

## Usage and examples

A typical safe workflow is:

1. Call `list_task_lists` to resolve a human-readable list name to its ID.
2. Call `list_tasks` or `get_task` before modifying an existing task.
3. Use a write tool such as `create_task`, `update_task`, or `move_task`.
4. Obtain explicit user confirmation before calling `delete_task_list`, `delete_task`, or
   `clear_completed_tasks` with `confirm: true`.

The Python implementation preserves the previous TypeScript tool names, arguments, pagination
defaults, safety annotations, date normalization, and omitted-versus-null update behavior.

There is no local task database, cache, index, background synchronization job, webhook, or network
listener. Each tool call accesses Google Tasks API v1 through the official Python client. The only
persistent local state managed by this package is the OAuth authorized-user token.

Each MCP tool call builds a fresh Google Tasks service and executes the complete operation in one
worker thread. No `googleapiclient` service or `httplib2` transport is shared across threads. This
follows the Google client library's thread-safety guidance while still allowing independent MCP
calls to run concurrently. The service is closed in that same worker thread after every call,
including when request execution fails, so its underlying sockets are not retained.

## Troubleshooting

- **Authentication error:** run `google-tasks-mcp-auth` again and confirm that the MCP subprocess
  receives the same `GOOGLE_TOKEN_FILE` value.
- **Token path looks correct but is not found:** use an absolute `GOOGLE_TOKEN_FILE`; relative paths
  are evaluated from the MCP subprocess's working directory.
- **Retry configuration error:** set `GOOGLE_API_NUM_RETRIES` to an integer from `0` through `10`.
- **No refresh token was returned:** revoke the application's existing Google account grant, then
  run the authorization helper again as directed by its error message.
- **Expired token has no refresh token:** run the authorization helper again; the server refuses to
  build a service from credentials that cannot be refreshed.
- **Browser flow cannot open:** authorize on a desktop that can complete the installed-app OAuth
  flow, then protect and transfer the generated service-specific token if needed.
- **Tools are missing:** restart the MCP client and verify the absolute command path. A fresh MCP
  client should discover exactly 14 tools.
- **Due time is missing:** Google Tasks retains only the date portion of a due timestamp.
- **Migrating from the TypeScript release:** preserve the protected token, install the Python
  package separately, point the client at `google-tasks-mcp`, verify all 14 tools with live
  read/write/cleanup checks, and only then remove the old Node.js checkout.

## Security

Report vulnerabilities privately according to the [security policy](SECURITY.md). Never include
credentials or real task data in a public issue.

- Keep `client_secret.json` and OAuth tokens outside source control and restrict their filesystem
  permissions.
- Use a dedicated token directory: authorization sets its directory to mode `0700` and writes the
  token atomically with mode `0600` on POSIX systems.
- Grant only the Google Tasks scope used by this service and keep separate tokens for other Google
  services.
- Treat create, update, move, clear, and delete operations as writes. Destructive tools require
  explicit confirmation, but the local account and MCP client still control access to the server.
- For one user on one workstation or VPS, `stdio` plus a protected local token is the simplest
  deployment. A multi-user hosted service requires per-user OAuth sessions, encrypted server-side
  token storage, and an appropriate network transport; never share one refresh token among users.

## Development and contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Participation is governed by
the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

Run all configured checks before submitting a change:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

The regression suite dispatches all 14 tools against a fake Google Tasks client, verifies
destructive confirmation, and tests omitted-versus-null update behavior.

For non-security bugs and feature requests, use the repository's structured
[issue templates](https://github.com/phamviet86/google-task-mcp/issues/new/choose).

## License

[MIT](LICENSE)

## References

- [Google Tasks API REST reference](https://developers.google.com/workspace/tasks/reference/rest)
- [Google Tasks resource fields](https://developers.google.com/workspace/tasks/reference/rest/v1/tasks)
- [Google Tasks ordering](https://developers.google.com/workspace/tasks/order)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Google API Python client thread safety](https://googleapis.github.io/google-api-python-client/docs/thread_safety.html)
- [Google API Python client request execution and retries](https://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.http.HttpRequest-class.html)
