---
name: google-tasks-setup
description: Set up the local Google Tasks MCP server, OAuth authorization, and MCP client configuration for a user's chosen Google account.
---

# Google Tasks MCP setup

Use this skill when a user wants to install, configure, authorize, or diagnose the local Google
Tasks MCP server. It is a `stdio` server for one local Google account and keeps no local task cache.
The server opens no network port; the authorization helper
may use a temporary local loopback callback while the user completes browser consent.

## Start locally

For the installed `0.4.0` release or a later release, read this skill's
`references/runtime.json` before running a command. Use its absolute `server` field:

```bash
/absolute/path/from/runtime.json/google-tasks-mcp doctor
```

If the installed skills need repair or update, retain their current skills root and use
`install-skills --check --dest CURRENT_ROOT`; after review, use `--replace` with that same
destination when needed. It accepts `--dry-run` without writes. The installed
`references/runtime.json` holds nonsecret identifiers for the
matching distribution and version plus absolute `python`, `server`, and `auth` paths. Use the
absolute paths in the MCP client configuration; do not guess paths or resolve a virtual-environment
Python symlink.

`doctor` only stats the configured token path and its permissions. Its `authentication` and
`mcp_discovery` results remain `unverified`; a token file or successful tool discovery never proves
that Google authorization works.

Published `v0.3.1` does not provide `install-skills` or `doctor`. Before installing `v0.4.0`, verify
that its GitHub Release provides the wheel, source archive, and `SHA256SUMS`; do not treat a source
branch or tag as a published release.

## Configure Google and OAuth

Reuse the user's selected existing Google account, Cloud project, OAuth configuration, and token
location. Preserve the server's Google Tasks scope and the configured `GOOGLE_TOKEN_FILE`; use an
absolute protected path outside a checkout. Never ask for, copy, print, or store OAuth JSON
contents, authorization codes, refresh tokens, token files, or task data in chat or manual
inspection. Passing the selected local JSON path to the authorization helper is expected: the helper
reads it and persists the authorized-user token locally.

If a usable OAuth Desktop-client JSON is already available, ask only for its local path when it is
needed. If it is missing, use available authorized tools to prepare the selected Cloud project,
enable Google Tasks API, and create a Desktop OAuth client when the console capability is available.
Ask the user only when a project, Google account, or consent-screen audience decision is needed;
do not assume an Internal audience is appropriate. Also ask when the local JSON path is needed, the
user must consent or log in in a browser, or the required console capability is unavailable.

Run the absolute `auth` path from `runtime.json` with the JSON **path** and the chosen token
destination. The user completes browser consent and login:

```bash
GOOGLE_TOKEN_FILE=/absolute/protected/google-tasks/token.json \
  /absolute/path/from/runtime.json/google-tasks-mcp-auth \
  --client-secret /absolute/protected/google/client_secret.json
```

The official [Google Tasks Python quickstart](https://developers.google.com/workspace/tasks/quickstart/python)
and [OAuth token-expiration guidance](https://developers.google.com/identity/protocols/oauth2#expiration)
are useful when a client or token needs attention.

Do not make a live Google call just because setup is complete. When the user authorizes a live
check—or explicitly asks to configure and verify the server for use—make one read-only
`list_task_lists` call. Treat only its successful API result as evidence of authentication; report
a failed call accurately and do not try writes to compensate.

## Configure the MCP client

Set the client's command to the absolute `server` value from `runtime.json`. Set
`GOOGLE_TOKEN_FILE` to the same absolute token path used by authorization, and retain any existing
`GOOGLE_API_NUM_RETRIES` choice. Restart the client after changing its configuration. MCP startup
and the 14-tool listing work without Google credentials, so they verify transport and discovery,
not authorization.
