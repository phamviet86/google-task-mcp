#!/usr/bin/env python3
"""Verify modern and legacy MCP discovery from an installed server without Google access."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import MCPError
from mcp.types import INVALID_PARAMS, CallToolResult

EXPECTED_TOOLS = [
    "list_task_lists",
    "get_task_list",
    "create_task_list",
    "update_task_list",
    "delete_task_list",
    "list_tasks",
    "get_task",
    "create_task",
    "update_task",
    "complete_task",
    "reopen_task",
    "move_task",
    "delete_task",
    "clear_completed_tasks",
]


async def verify(command: Path, version: str, modern: bool, home: Path) -> None:
    environment = dict(os.environ)
    environment["GOOGLE_TOKEN_FILE"] = str(home / "missing-token.json")
    parameters = StdioServerParameters(command=str(command), env=environment, cwd=home)
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream, read_timeout_seconds=30) as session,
    ):
        if modern:
            discovered = await session.discover()
            assert "2026-07-28" in discovered.supported_versions
            assert session.protocol_version == "2026-07-28"
        else:
            initialized = await session.initialize()
            assert initialized.protocol_version == "2025-11-25"
        assert session.server_info and session.server_info.name == "google-tasks-mcp"
        assert session.server_info.version == version
        listed = await session.list_tools()
        assert [tool.name for tool in listed.tools] == EXPECTED_TOOLS
        try:
            await session.call_tool("absent-tool", {})
        except MCPError as error:
            assert error.error.code == INVALID_PARAMS
        else:
            raise AssertionError("unknown tools must produce JSON-RPC invalid params")
        authentication = await session.call_tool("list_task_lists", {})
        assert isinstance(authentication, CallToolResult)
        assert authentication.is_error


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--command", type=Path, required=True)
    result.add_argument("--version", required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    command = args.command.absolute()
    with tempfile.TemporaryDirectory(prefix="google-tasks-mcp-stdio-") as temporary:
        home = Path(temporary) / "empty-home"
        home.mkdir()
        for modern in (True, False):
            anyio.run(verify, command, args.version, modern, home)
    print("verified native MCP discovery and exact 14-tool listing (2026-07-28 + 2025-11-25)")


if __name__ == "__main__":
    main()
