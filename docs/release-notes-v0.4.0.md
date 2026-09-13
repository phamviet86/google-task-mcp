# Google Tasks MCP v0.4.0

Agents can now complete installation, OAuth setup and everyday Google Tasks work using skills
bundled in the release wheel. Install the verified wheel, run `google-tasks-mcp install-skills`,
then follow `google-tasks-setup` and `google-tasks`.

- Adds transactional skill installation with custom destinations, dry-run/check, managed updates,
  portable runtime paths and preservation of unrelated files.
- Adds a local `doctor` command that checks configuration metadata without reading credentials or
  claiming authentication from token presence.
- Preserves all 14 tool names and input schemas, including omitted fields versus explicit null
  when clearing notes or due dates.
- Adds structured results alongside JSON text, native unknown-tool errors and conservative MCP
  annotations. Verifies modern `2026-07-28` and legacy `2025-11-25` stdio clients.

Download the `phamviet_google_tasks_mcp-0.4.0-py3-none-any.whl` wheel and `SHA256SUMS`, verify the
checksum, and install the verified local wheel into a dedicated Python environment on macOS/Linux.
Use the repository's release installation guide; a source checkout is not required. PyPI is not
published for this project. The unrelated PyPI package `google-tasks-mcp` is a different project.

The user supplies only required account/project choices, a local OAuth Desktop-client JSON path
when needed, and browser login/consent. Agent setup reuses existing configuration and authorization.
Tokens stay outside the checkout. No personal Google data or real OAuth credentials were used in
automated release verification; live authentication must be verified on the destination workstation.
