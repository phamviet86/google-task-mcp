# Agent contract

This repository is a local, stdio-only MCP server for one authenticated Google Tasks account. Keep
the repository name `google-task-mcp`, the console commands `google-tasks-mcp` and
`google-tasks-mcp-auth`, and the unique distribution name `phamviet-google-tasks-mcp` distinct.

## Operating rules

- Never read, create, commit, print, or request OAuth client secrets, authorization codes, refresh
  tokens, token files, real task content, or unredacted client configuration during ordinary work.
  A live authenticated read is allowed only when a maintainer explicitly authorizes it and provides a
  dedicated non-production Google account containing only test data. Otherwise do not invoke a
  Google tool and record the authenticated-read check as `NOT_VERIFIED`.
- Treat Google Tasks as external user data. In a maintainer-authorized interaction, read before
  modifying when context matters; ask for explicit user confirmation before `delete_task_list`,
  `delete_task`, or `clear_completed_tasks`.
- Do not represent MCP initialization or tool discovery as an authentication test. Discovery works
  without credentials; a real tool call requires a valid token.
- Preserve stdio-only operation. Do not add a listener, database, background service, sync job, or
  webhook without an explicit architecture decision.
- Use absolute executable and token paths in client examples. Keep local tokens outside the checkout.
- macOS and Linux are the current supported release platforms. Do not claim Windows
  support until permission handling and end-to-end operation are verified.

## Change contract

When behavior changes, keep `README.md`, `README.vi.md`, `docs/release-deployment.md`, and tests in
sync with the runtime schema. Preserve the 14-tool public contract unless a versioned compatibility
decision explicitly changes it. Maintain the difference between omitted update fields and explicit
`null` for clearing `notes` or `due`.

Before proposing a release, follow [the release and deployment guide](docs/release-deployment.md),
run the configured format, lint, type, and test checks; build the artifact; install it in a clean
dedicated virtual environment; and run the machine-actionable verifiers:

```bash
python3 scripts/verify_release_artifacts.py dist --version "$RELEASE_VERSION"
"$RELEASE_VENV/bin/python" scripts/verify_mcp_stdio.py \
  --command "$RELEASE_VENV/bin/google-tasks-mcp" --version "$RELEASE_VERSION"
```

These checks verify artifact metadata plus MCP initialization and the exact 14-tool discovery
without Google credentials. An authenticated read is optional and remains `NOT_VERIFIED` unless the
maintainer explicitly authorizes the dedicated test account described above; never use a personal or
production account merely to satisfy a release checklist. Do not claim a tag, GitHub Release, or
PyPI publication without checking it exists.
