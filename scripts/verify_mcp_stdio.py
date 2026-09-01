"""Exercise the packaged MCP server over stdio without invoking Google APIs."""

from __future__ import annotations

import argparse
import json
import selectors
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

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


def read_response(process: subprocess.Popen[bytes], request_id: int) -> dict[str, Any]:
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while True:
            if not selector.select(timeout=10):
                raise TimeoutError(f"timed out waiting for MCP response {request_id}")
            line = process.stdout.readline()
            if not line:
                raise RuntimeError(f"MCP server exited before response {request_id}")
            message = cast(dict[str, Any], json.loads(line))
            if message.get("id") == request_id:
                return message
    finally:
        selector.close()


def send(process: subprocess.Popen[bytes], message: dict[str, Any]) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message, separators=(",", ":")).encode() + b"\n")
    process.stdin.flush()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Verify the installed server MCP stdio contract.")
    result.add_argument("--command", type=Path, required=True)
    result.add_argument("--version", required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    process = subprocess.Popen(
        [str(args.command)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "release-verifier", "version": args.version},
                },
            },
        )
        initialized = read_response(process, 1)
        server_info = initialized.get("result", {}).get("serverInfo", {})
        if server_info != {"name": "google-tasks-mcp", "version": args.version}:
            raise AssertionError(f"unexpected MCP server info: {server_info!r}")
        send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = read_response(process, 2).get("result", {}).get("tools")
        names = [tool.get("name") for tool in tools] if isinstance(tools, list) else None
        if names != EXPECTED_TOOLS:
            raise AssertionError(f"expected exact fourteen-tool contract, got {names!r}")
        print("verified MCP initialize and exact 14-tool listing without Google credentials")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.returncode not in (0, -15):
            stderr = process.stderr.read().decode(errors="replace") if process.stderr else ""
            print(f"MCP server stderr:\n{stderr}", file=sys.stderr)


if __name__ == "__main__":
    main()
