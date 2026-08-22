# Google Tasks MCP

A Python MCP server that lets AI agents read and manage a user's Google Tasks.
It uses Google's official Tasks API, OAuth 2.0 Desktop App credentials, and the
MCP Python SDK over `stdio`.

## Features

- List, inspect, create, rename, and delete task lists
- List and filter tasks with API pagination
- Create, edit, complete, reopen, move, reorder, and delete tasks
- Create and move subtasks using `parent` and `previous`
- Clear completed tasks
- MCP safety annotations plus explicit confirmation for destructive operations
- OAuth refresh token stored outside the repository with owner-only permissions
- Python-only runtime; Node.js is not required

## Requirements

- Python 3.11 or 3.12
- `uv` or another Python package installer
- A Google account
- A Google Cloud project with the Google Tasks API enabled

## 1. Configure Google Cloud

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable **Google Tasks API** under **APIs & Services → Library**.
4. Configure the OAuth consent screen.
5. Under **APIs & Services → Credentials**, create an OAuth client ID with
   application type **Desktop app**.
6. Download the OAuth Desktop client JSON as `client_secret.json` and keep it
   protected outside this repository.

## 2. Install and authorize

Install a development checkout:

```bash
uv sync --extra dev
```

Authorize from a desktop that can open the browser consent flow:

```bash
uv run google-tasks-mcp-auth \
  --client-secret /secure/google/client_secret.json
```

The command accepts only a Google OAuth Desktop client JSON containing the
top-level `installed` object. It saves a separate Google Tasks token to:

```text
~/.config/google-tasks-mcp/token.json
```

Override the token location when needed:

```bash
GOOGLE_TOKEN_FILE=/secure/google/tasks-token.json \
uv run google-tasks-mcp-auth \
  --client-secret /secure/google/client_secret.json
```

The server requests the full `https://www.googleapis.com/auth/tasks` scope
because it exposes read and write operations. Later MCP runs refresh access
automatically. Never commit the OAuth client or generated token.

The same OAuth Desktop client definition may be used to authorize another
local application, but each service should retain its own token and exact
scope. Do not reuse a broader Google Workspace token as this service's token.

## 3. Connect an MCP host

Use the Python console script from the virtual environment. Replace paths with
absolute paths on the target machine.

### Codex (`~/.codex/config.toml`)

```toml
[mcp_servers.google_tasks]
command = "/absolute/path/google-task-mcp/.venv/bin/google-tasks-mcp"

[mcp_servers.google_tasks.env]
GOOGLE_TOKEN_FILE = "/Users/you/.config/google-tasks-mcp/token.json"
```

### Hosts using JSON configuration

```json
{
  "mcpServers": {
    "google_tasks": {
      "command": "/absolute/path/google-task-mcp/.venv/bin/google-tasks-mcp",
      "env": {
        "GOOGLE_TOKEN_FILE": "/secure/google/tasks-token.json"
      }
    }
  }
}
```

Restart the MCP host after changing its configuration.

## Available tools

| Tool | Purpose |
| --- | --- |
| `list_task_lists` | List task lists |
| `get_task_list` | Get one task list |
| `create_task_list` | Create a task list |
| `update_task_list` | Rename a task list |
| `delete_task_list` | Delete a task list; requires `confirm: true` |
| `list_tasks` | List/filter tasks with pagination |
| `get_task` | Get one task |
| `create_task` | Create a task or subtask |
| `update_task` | Patch title, notes, due date, or status |
| `complete_task` | Mark a task completed |
| `reopen_task` | Mark a task as needing action |
| `move_task` | Reorder, reparent, or move a task to another list |
| `delete_task` | Delete a task; requires `confirm: true` |
| `clear_completed_tasks` | Clear completed tasks; requires `confirm: true` |

Google Tasks stores only the date portion of a due timestamp. A time-of-day
sent through the API is discarded. Task titles are limited to 1,024 characters
and notes to 8,192 characters.

The Python implementation preserves the previous TypeScript tool names,
arguments, pagination defaults, safety annotations, date normalization, and
the distinction between an omitted update field and explicit `null` used to
clear `notes` or `due`.

## Validate

Run all configured checks:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

The regression suite dispatches all 14 tools against a fake Google Tasks
client, verifies destructive confirmation, and tests omitted-versus-null update
behavior. A fresh MCP stdio client should discover exactly 14 tools before live
Google API testing.

## Build and install from GitHub

Build wheel and source distributions:

```bash
uv build
```

Install an immutable Git commit into a dedicated virtual environment:

```bash
uv venv --python /usr/bin/python3.12 /opt/google-tasks-mcp/venv
uv pip install \
  --python /opt/google-tasks-mcp/venv/bin/python \
  "git+https://github.com/phamviet86/google-task-mcp.git@<commit>"
```

Launch the installed MCP server with:

```text
/opt/google-tasks-mcp/venv/bin/google-tasks-mcp
```

For one user on one workstation or VPS, `stdio` plus a protected local token is
the simplest deployment. For multiple users or a hosted service, use MCP
Streamable HTTP and implement per-user OAuth sessions and encrypted server-side
token storage; do not share one refresh token among users.

## Migration from the TypeScript release

Version 0.2.0 replaces the Node.js implementation with Python. Before removing
the old installation:

1. Preserve the protected Google Tasks token; do not print or commit it.
2. Install this Python package into a new virtual environment.
3. Point the MCP host at the new `google-tasks-mcp` console script while keeping
   `GOOGLE_TOKEN_FILE` unchanged.
4. Discover exactly 14 tools and run live read/write/cleanup tests.
5. Remove the old Node checkout only after the Python server is verified.

## References

- [Google Tasks API REST reference](https://developers.google.com/workspace/tasks/reference/rest)
- [Google Tasks resource fields](https://developers.google.com/workspace/tasks/reference/rest/v1/tasks)
- [Google Tasks ordering](https://developers.google.com/workspace/tasks/order)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
