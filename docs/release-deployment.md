# Release and deployment

## Current status and names

`google-task-mcp` is the public GitHub repository name. Its MCP commands are
`google-tasks-mcp` and `google-tasks-mcp-auth`; its intended Python distribution is
`phamviet-google-tasks-mcp`.

The [GitHub Release `v0.3.0`](https://github.com/phamviet86/google-task-mcp/releases/tag/v0.3.0),
published 2026-09-01, is the authoritative `0.3.0` distribution. Its assets include the wheel,
source archive, and `SHA256SUMS`. PyPI is not published for this project. The PyPI project named
`google-tasks-mcp` is unrelated; never install it for this repository.

## Release process for maintainers

For each future release, run the release build, test suite, static checks, clean-wheel installation,
and MCP discovery check before creating the version tag and GitHub Release. Attach the wheel and
source archive, publish checksums, and record the commit and release date in
[CHANGELOG.md](../CHANGELOG.md). If PyPI publication is chosen, publish only the unique
`phamviet-google-tasks-mcp` distribution and verify its files match the GitHub Release artifacts.

## Deploy a GitHub Release wheel

On macOS or Linux, download the exact `v0.3.0` wheel and checksum, verify the checksum, then install
into a dedicated virtual environment. Use an absolute path owned by the operator; `/opt` below is
only an example.

```bash
curl -fL -O \
  "https://github.com/phamviet86/google-task-mcp/releases/download/v0.3.0/phamviet_google_tasks_mcp-0.3.0-py3-none-any.whl"
curl -fL -O \
  "https://github.com/phamviet86/google-task-mcp/releases/download/v0.3.0/SHA256SUMS"
shasum -a 256 -c SHA256SUMS --ignore-missing
uv venv --python /usr/bin/python3.12 /opt/google-tasks-mcp/venv
uv pip install --python /opt/google-tasks-mcp/venv/bin/python \
  "https://github.com/phamviet86/google-task-mcp/releases/download/v0.3.0/phamviet_google_tasks_mcp-0.3.0-py3-none-any.whl"
/opt/google-tasks-mcp/venv/bin/google-tasks-mcp-auth --help
```

On Linux, use `sha256sum -c SHA256SUMS --ignore-missing`. The server command has no operational
arguments; `--help` and `--version` are safe console-script checks that do not launch a stdio
server. Configure your MCP client with the absolute server path. Keep the environment separate from
the repository checkout and from system Python.

PyPI is not published for this release. Do not replace the GitHub Release URL with a PyPI command,
and never install the unrelated project named `google-tasks-mcp`.

## OAuth and first-use verification

Create a Google OAuth **Desktop app** client, enable Google Tasks API, and retain the downloaded
client JSON outside the repository. It must contain the top-level `installed` object. Authorize on
the same host and account that will run the MCP server:

```bash
GOOGLE_TOKEN_FILE=/absolute/protected/google-tasks/token.json \
  /opt/google-tasks-mcp/venv/bin/google-tasks-mcp-auth \
  --client-secret /absolute/protected/google/client_secret.json
```

The helper requests the full Google Tasks scope because the MCP contract includes writes. On macOS
and Linux it creates the token directory with mode `0700` and writes the token atomically with mode
`0600`. Do not place the client JSON or token in the checkout, build artifact, issue, or log.

Before authorization, MCP initialization and `tools/list` should succeed: neither needs Google
credentials. The first tool call should fail with an authentication error identifying the token path.
After authorization, verify `list_task_lists` before attempting any write. This distinction helps
diagnose a configuration error without treating normal pre-auth discovery as a failure.

## Client configuration

All clients must launch the exact executable through an absolute path and pass the same absolute
`GOOGLE_TOKEN_FILE` used during authorization. The server uses stdio only; it opens no network port,
has no local database, cache, webhook, or background worker.

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.google_tasks]
command = "/opt/google-tasks-mcp/venv/bin/google-tasks-mcp"

[mcp_servers.google_tasks.env]
GOOGLE_TOKEN_FILE = "/absolute/protected/google-tasks/token.json"
GOOGLE_API_NUM_RETRIES = "3"
```

Hermes (`~/.hermes/config.yaml`):

```yaml
mcp_servers:
  google_tasks:
    command: /opt/google-tasks-mcp/venv/bin/google-tasks-mcp
    args: []
    env:
      GOOGLE_TOKEN_FILE: /absolute/protected/google-tasks/token.json
      GOOGLE_API_NUM_RETRIES: "3"
    timeout: 120
    connect_timeout: 30
```

Do not enable parallel tool calls in Hermes for this complete write-capable tool set.

For a generic MCP client, use its native stdio adapter with these equivalent fields:

```json
{
  "mcpServers": {
    "google_tasks": {
      "command": "/opt/google-tasks-mcp/venv/bin/google-tasks-mcp",
      "env": {
        "GOOGLE_TOKEN_FILE": "/absolute/protected/google-tasks/token.json",
        "GOOGLE_API_NUM_RETRIES": "3"
      }
    }
  }
}
```

## Upgrade, rollback, and uninstall

1. Preserve the protected token directory; it is independent of the virtual environment.
2. Download and verify the new release artifact before touching the current environment.
3. Create a new versioned environment, install the new artifact, re-run OAuth only if the token is
   missing or invalid, and verify `list_task_lists`.
4. Change the MCP client command to the new absolute path and restart the client. Keep the previous
   environment until discovery and a safe read are confirmed.
5. To roll back, restore the previous absolute command path and restart the MCP client. Do not
   delete the token as a rollback step.
6. To uninstall, remove only the identified dedicated virtual environment after confirming no MCP
   configuration still references it. Removing the token separately revokes local access; revoke the
   OAuth grant in the Google account as well if access should end completely.

## Platform boundary

macOS and Linux are supported for `v0.3.0`. Windows has not been validated and is not supported yet:
the current token writer relies on POSIX permission operations. A Windows release requires explicit
compatibility work and end-to-end validation before it can be documented as supported.
