# Google Tasks MCP

An MCP server that lets AI agents read and manage a user's Google Tasks. It uses
Google's official Tasks API, OAuth 2.0 Desktop App credentials, and the MCP
TypeScript SDK over `stdio`.

## Features

- List, inspect, create, rename, and delete task lists
- List and filter tasks with API pagination
- Create, edit, complete, reopen, move, reorder, and delete tasks
- Create and move subtasks using `parent` and `previous`
- Clear completed tasks
- MCP safety annotations plus explicit confirmation for destructive operations
- OAuth refresh token stored outside the repository with owner-only permissions

## Requirements

- Node.js 20 or newer
- A Google account
- A Google Cloud project with the Google Tasks API enabled

## 1. Configure Google Cloud

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable **Google Tasks API** under **APIs & Services → Library**.
4. Configure the OAuth consent screen.
5. Under **APIs & Services → Credentials**, create an OAuth client ID with
   application type **Desktop app**.
6. Download the OAuth Desktop client JSON as `client_secret.json` and keep it protected
   outside this repository.

## 2. Install, build, and authorize

```bash
npm install
npm run build
npm run auth -- --client-secret /secure/google/client_secret.json
```

The auth command accepts only a Google OAuth Desktop client JSON containing the top-level
`installed` object. It opens a browser consent flow and saves the Tasks refresh token to:

```text
~/.config/google-tasks-mcp/token.json
```

Override the generated token location when needed:

```bash
GOOGLE_TOKEN_FILE=/secure/google/tasks-token.json \
npm run auth -- --client-secret /secure/google/client_secret.json
```

The installed package uses the same authentication syntax:

```bash
google-tasks-mcp-auth --client-secret /secure/google/client_secret.json
```

The server requests the full `https://www.googleapis.com/auth/tasks` scope
because it exposes both read and write operations. Never commit either JSON
file.

## 3. Connect an MCP host

Use the built server directly from this checkout. Replace the paths with absolute
paths on your machine.

### Codex (`~/.codex/config.toml`)

```toml
[mcp_servers.google_tasks]
command = "node"
args = ["/absolute/path/google-task-mcp/dist/index.js"]

[mcp_servers.google_tasks.env]
GOOGLE_TOKEN_FILE = "/Users/you/.config/google-tasks-mcp/token.json"
```

### Hosts using JSON configuration

```json
{
  "mcpServers": {
    "google_tasks": {
      "command": "node",
      "args": ["/absolute/path/google-task-mcp/dist/index.js"],
      "env": {
        "GOOGLE_TOKEN_FILE": "/Users/you/.config/google-tasks-mcp/token.json"
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

Google Tasks stores only the date portion of a due timestamp. A time-of-day sent
through the API is discarded. Task titles are limited to 1,024 characters and
notes to 8,192 characters.

## Test with MCP Inspector

```bash
npm run build
npm run inspect
```

The `stdio` protocol uses stdout exclusively. Runtime diagnostics are therefore
written to stderr.

## Package for distribution

Create an installable npm tarball:

```bash
npm pack
```

After publishing the package, a host can launch it with:

```json
{
  "command": "npx",
  "args": ["-y", "google-tasks-mcp@0.1.0"],
  "env": {
    "GOOGLE_TOKEN_FILE": "/secure/google/tasks-token.json"
  }
}
```

For one user on one workstation, `stdio` plus a local token is the simplest and
safest deployment. For multiple users or a hosted service, use MCP Streamable
HTTP and implement per-user OAuth sessions and encrypted server-side token
storage; do not share one refresh token among users.

## References

- [Google Tasks API REST reference](https://developers.google.com/workspace/tasks/reference/rest)
- [Google Tasks resource fields](https://developers.google.com/workspace/tasks/reference/rest/v1/tasks)
- [Google Tasks ordering](https://developers.google.com/workspace/tasks/order)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [MCP TypeScript SDK](https://ts.sdk.modelcontextprotocol.io/v2/)
