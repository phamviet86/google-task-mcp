# Agent-led setup and use

This guide applies to `v0.4.0` and later releases that include the bundled skills. Before using this
guide for `v0.4.0`, verify that the [GitHub Release `v0.4.0`](https://github.com/phamviet86/google-task-mcp/releases/tag/v0.4.0)
is available with its wheel, source archive, and `SHA256SUMS`; a source branch or tag alone is not a
published release. The published [`v0.3.1`](https://github.com/phamviet86/google-task-mcp/releases/tag/v0.3.1)
does **not** include `google-tasks-mcp install-skills` or `google-tasks-mcp doctor`.

After installing the verified release wheel, an agent can install the two bundled skills:

```bash
/absolute/path/to/venv/bin/google-tasks-mcp install-skills
```

The default destination is `$CODEX_HOME/skills`, or `~/.agents/skills` when `CODEX_HOME` is not
set. Use `--dest /absolute/skills/root` to select a different root, `--dry-run` to preview,
`--check` to confirm an unchanged installation, and `--replace` only after reviewing differing
managed content. Installation writes a nonsecret `references/runtime.json` into each installed
skill with `distribution` and `version` identifiers plus absolute `python`, `server`, and `auth`
paths. Read that file before running a command; its absolute executable paths should be the source
of MCP client configuration and authorization commands.

## Authorization without secret handling

The agent should reuse the user's selected Google account, Cloud project, consent-screen setting,
OAuth configuration, and token destination. If an OAuth Desktop client JSON exists, it needs only
the local file path. It must never request, copy, display, or log the JSON contents, authorization
codes, refresh tokens, token files, or task data in chat or manual inspection. Passing the local
path to the authorization helper is expected: the helper reads the JSON and persists the token.

When the JSON is missing, an agent may use authorized available tools to select or prepare a Cloud
project, enable Google Tasks API, and create an OAuth **Desktop app** client. It asks the user only
when a project, account, or consent-screen audience choice is required, the local JSON path is
needed, browser consent/login is required, or it cannot access the relevant Google Cloud console
capability. Do not select an Internal audience automatically; it depends on the chosen account and
project. Follow the [Google Tasks Python quickstart](https://developers.google.com/workspace/tasks/quickstart/python)
and Google's [OAuth token-expiration guidance](https://developers.google.com/identity/protocols/oauth2#expiration)
as needed.

Run the absolute `auth` command in `runtime.json` with `--client-secret` set to the supplied local
path, preserving the user's selected absolute `GOOGLE_TOKEN_FILE`. The user completes browser
consent and login, which may use a temporary local loopback callback. Configure the MCP client with
the absolute `server` command and that same token path, then restart the client. The server itself
uses stdio and opens no network port. Detailed Codex, Hermes, and generic configuration examples are in
[README.md](../README.md#mcp-client-configuration).

## Know what has been verified

```bash
/absolute/path/to/venv/bin/google-tasks-mcp doctor
```

`doctor` only checks token-path metadata and permissions. It does not read credentials, refresh a
token, contact Google, or establish MCP discovery; both `authentication` and `mcp_discovery` remain
`unverified` even if a token exists. Likewise, an MCP 14-tool listing verifies the local transport
and contract, not a Google login.

Do not make a live API call automatically. With the user's authorization for a live check, or when
the request explicitly includes configuration and verification for use, call `list_task_lists` once.
A successful response is the authentication proof; a failure should be reported as such without
attempting a write.

## Normal task workflow

The installed `google-tasks` skill covers the server's 14 tools and safe update behavior. Read a
list or task before changing existing data when context matters. Creates are additive; for rename,
update, move, complete, and reopen, use the user's exact request for the named target as the
authorization step. For delete or clear, reuse exact existing authorization for the named target;
otherwise ask before sending `confirm: true`. For `update_task`, omit fields that should remain
unchanged and use explicit `null` only to clear `notes` or `due`.
