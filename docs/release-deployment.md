# Release and deployment

## Current status and names

`google-task-mcp` is the public GitHub repository name. Its MCP commands are
`google-tasks-mcp` and `google-tasks-mcp-auth`; its intended Python distribution is
`phamviet-google-tasks-mcp`.

`v0.4.0` is the release target. Before deploying it, confirm that the
[GitHub Release `v0.4.0`](https://github.com/phamviet86/google-task-mcp/releases/tag/v0.4.0) is
available with its wheel, source archive, and `SHA256SUMS`. Until then, a source branch or tag is
not a published release. PyPI is not published for this project. The PyPI project named
`google-tasks-mcp` is unrelated; never install it for this repository.

`v0.4.0` provides `google-tasks-mcp install-skills` and `google-tasks-mcp doctor`. The published
`v0.3.1` wheel is historical and does not include those commands. See [agent-led setup](agent-setup.md)
for the intended user workflow and verification boundaries.

## Release process for maintainers

For each future release, run the release build, test suite, static checks, clean-wheel installation,
and MCP discovery check before creating the version tag and GitHub Release. Attach the wheel and
source archive, publish checksums, and record the commit and release date in
[CHANGELOG.md](../CHANGELOG.md). If PyPI publication is chosen, publish only the unique
`phamviet-google-tasks-mcp` distribution and verify its files match the GitHub Release artifacts.

For a release that includes the onboarding commands, verify the clean installed wheel can install
both bundled skills in an isolated destination, rerun idempotently, and pass `--check` without
writes. Confirm the generated `references/runtime.json` contains only the expected nonsecret
`distribution` and `version` identifiers plus absolute `python`, `server`, and `auth` paths. Run
`doctor` without a live Google call and record authentication and discovery as unverified unless a
separately authorized read-only API check succeeds.

## Deploy a GitHub Release wheel

After confirming the `v0.4.0` release assets, download the exact wheel and checksum, verify the
checksum, then install into a dedicated virtual environment on macOS or Linux. This flow does not
require a repository checkout or a preinstalled Python 3.12. It requires
[`uv`](https://docs.astral.sh/uv/getting-started/installation/); if `uv --version` does not succeed,
install it with the official instructions and open a new terminal.

```bash
uv --version
uv python install 3.12
INSTALL_ROOT="$HOME/.local/share/google-tasks-mcp/v0.4.0"
mkdir -p "$INSTALL_ROOT"
```

Then download and verify the wheel, and install that verified local file:

```bash
INSTALL_ROOT="$HOME/.local/share/google-tasks-mcp/v0.4.0"
DOWNLOAD_DIR="$INSTALL_ROOT/downloads"
WHEEL_NAME="phamviet_google_tasks_mcp-0.4.0-py3-none-any.whl"
mkdir -p "$DOWNLOAD_DIR"
curl -fL -o "$DOWNLOAD_DIR/$WHEEL_NAME" \
  "https://github.com/phamviet86/google-task-mcp/releases/download/v0.4.0/$WHEEL_NAME"
curl -fL -o "$DOWNLOAD_DIR/SHA256SUMS" \
  "https://github.com/phamviet86/google-task-mcp/releases/download/v0.4.0/SHA256SUMS"
(cd "$DOWNLOAD_DIR" && shasum -a 256 -c SHA256SUMS --ignore-missing)
uv venv --python 3.12 "$INSTALL_ROOT/venv"
uv pip install --python "$INSTALL_ROOT/venv/bin/python" "$DOWNLOAD_DIR/$WHEEL_NAME"
"$INSTALL_ROOT/venv/bin/google-tasks-mcp-auth" --help
```

On Linux, use `sha256sum -c SHA256SUMS --ignore-missing`. The `v0.4.0` release target supports
`install-skills` and `doctor`; no-argument invocation remains stdio. Install the bundled skills,
read the installed `google-tasks-setup` skill, then use its `references/runtime.json` before
authorizing or configuring the client:

```bash
"$INSTALL_ROOT/venv/bin/google-tasks-mcp" install-skills
```

The runtime file records only the matching distribution/version and absolute `python`, `server`,
and `auth` paths. Configure the MCP client with the absolute server path
`$HOME/.local/share/google-tasks-mcp/v0.4.0/venv/bin/google-tasks-mcp`; configuration files do not
expand `$HOME`, so use your actual absolute home-directory path. Keep the environment separate from
the repository checkout and from system Python.

PyPI is not published for this release. Do not replace the GitHub Release URL with a PyPI command,
and never install the unrelated project named `google-tasks-mcp`.

## OAuth and first-use verification

Create a Google OAuth **Desktop app** client, enable Google Tasks API, and retain the downloaded
client JSON outside the repository. It must contain the top-level `installed` object. Authorize on
the same host and account that will run the MCP server:

```bash
INSTALL_ROOT="$HOME/.local/share/google-tasks-mcp/v0.4.0"
GOOGLE_TOKEN_FILE=/absolute/protected/google-tasks/token.json \
  "$INSTALL_ROOT/venv/bin/google-tasks-mcp-auth" \
  --client-secret /absolute/protected/google/client_secret.json
```

The helper requests the full Google Tasks scope because the MCP contract includes writes. On macOS
and Linux it creates the token directory with mode `0700` and writes the token atomically with mode
`0600`. Do not place the client JSON or token in the checkout, build artifact, issue, or log.

Before authorization, MCP initialization and `tools/list` should succeed: neither needs Google
credentials. The first tool call should fail with an authentication error identifying the token path.
After authorization, verify `list_task_lists` before attempting any write. This distinction helps
diagnose a configuration error without treating normal pre-auth discovery as a failure.

`google-tasks-mcp doctor` only stats token-path metadata and
permissions. It never reads credentials, refreshes a token, contacts Google, or proves MCP
discovery. A present token and `tools/list` are therefore not authentication evidence; make one
read-only `list_task_lists` call only when the operator has authorized that live check.

## Client configuration

All clients must launch the exact executable through an absolute path and pass the same absolute
`GOOGLE_TOKEN_FILE` used during authorization. The server uses stdio only; it opens no network port,
has no local database, cache, webhook, or background worker.

The authorization helper may use a temporary local loopback callback while browser OAuth consent is
completed. That callback is separate from the server transport and does not make the server a
network listener.

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.google_tasks]
command = "/absolute/path/to/home/.local/share/google-tasks-mcp/v0.4.0/venv/bin/google-tasks-mcp"

[mcp_servers.google_tasks.env]
GOOGLE_TOKEN_FILE = "/absolute/protected/google-tasks/token.json"
GOOGLE_API_NUM_RETRIES = "3"
```

Hermes (`~/.hermes/config.yaml`):

```yaml
mcp_servers:
  google_tasks:
    command: /absolute/path/to/home/.local/share/google-tasks-mcp/v0.4.0/venv/bin/google-tasks-mcp
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
      "command": "/absolute/path/to/home/.local/share/google-tasks-mcp/v0.4.0/venv/bin/google-tasks-mcp",
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

macOS and Linux are supported for `v0.4.0`. Windows has not been validated and is not supported yet:
the current token writer relies on POSIX permission operations. A Windows release requires explicit
compatibility work and end-to-end validation before it can be documented as supported.
