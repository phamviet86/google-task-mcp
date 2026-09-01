# Contributing to Google Tasks MCP

Thank you for helping improve the project. By participating, you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- Search existing issues before opening a new one.
- Use the bug or feature template for public, non-sensitive work.
- Report vulnerabilities privately according to [SECURITY.md](SECURITY.md).
- Never commit or paste OAuth tokens, client secrets, authorization codes, real task data, or
  unredacted logs.

For a substantial MCP contract or architecture change, open an issue first so the scope can be
agreed before implementation.

## Development setup

The project supports Python 3.11 and newer. CI currently covers Python 3.11 through 3.14.

```bash
git clone https://github.com/phamviet86/google-task-mcp
cd google-task-mcp
uv sync --extra dev
```

Create a focused branch from an up-to-date `main` branch. Names such as `fix/token-refresh` or
`docs/client-setup` are helpful but not required. Keep unrelated refactors out of the same pull
request.

If you change dependency declarations, update `uv.lock` with `uv lock` and explain the reason in the
pull request.

## Required checks

Run the same checks as CI:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

Use `uv run ruff format .` to apply formatting. Strict mypy settings live in `pyproject.toml`; avoid
new ignores unless the dependency genuinely lacks usable typing and the ignore is narrowly scoped.

Add regression tests for behavior changes. Tests must remain deterministic and must not call a live
Google account.

## Testing MCP without real credentials

The test suite uses fake Google Tasks clients and covers all 14 tools, retries, validation,
credential persistence, and service lifecycle. It does not require `GOOGLE_TOKEN_FILE`.

You can also verify stdio initialization and tool discovery without authenticating:

```bash
uv run python - <<'PY'
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server = StdioServerParameters(command="uv", args=["run", "google-tasks-mcp"])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert len(tools.tools) == 14


asyncio.run(main())
PY
```

Do not run live create, update, move, clear, or delete operations as part of an automated test. If a
maintainer explicitly performs a live manual check, use a dedicated test list and clean it up only
after verifying the target IDs.

## Documentation and contracts

Update `README.md` whenever a change affects installation, CLI arguments, environment variables,
MCP tool schemas, defaults, authentication, retries, client configuration, or security behavior.
Examples must use fake IDs and placeholder paths.

Keep these contracts aligned:

- console scripts and package metadata in `pyproject.toml`;
- runtime schemas and behavior in `src/google_tasks_mcp/`;
- regression coverage in `tests/`;
- setup and user-facing guidance in `README.md`.

For release-facing changes, also keep `README.vi.md`, `docs/release-deployment.md`, `AGENTS.md`, and
`CHANGELOG.md` accurate. Do not state that a Git tag, GitHub Release, wheel, or PyPI package exists
until it has been created and verified. The distribution name for this project is
`phamviet-google-tasks-mcp`; do not direct users to the unrelated PyPI project
`google-tasks-mcp`.

## Pull requests

Open a pull request against `main` and complete the template. A useful pull request:

- explains the user-visible problem and chosen approach;
- stays small enough to review safely;
- includes tests and documentation where needed;
- passes every CI job on supported Python versions;
- contains no generated environments, build artifacts, credentials, or personal data.

Maintainers may request changes or close work that is unsafe, out of scope, or cannot be maintained.
