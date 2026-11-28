"""Integration tests for RAA MCP Mesh live tool discovery and forwarding."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from raa.errors import NotFoundError, StateError
from raa.runtime import Runtime

_DUMMY_MCP_SERVER_SCRIPT = """
import json
import sys

for raw_line in sys.stdin:
    line = raw_line.strip()
    if not line:
        continue
    msg = json.loads(line)
    req_id = msg.get("id")
    method = msg.get("method")
    if method == "initialize":
        resp = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "dummy-re-server", "version": "1.0.0"},
            },
        }
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
    elif method == "tools/list":
        resp = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "inspect_pe",
                        "description": "Inspect a binary header.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"],
                        },
                    }
                ]
            },
        }
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
    elif method == "tools/call":
        params = msg.get("params") or {}
        args = params.get("arguments") or {}
        payload = {"tool": params.get("name"), "path": args.get("path"), "arch": "x86_64"}
        resp = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "isError": False,
                "content": [{"type": "text", "text": json.dumps(payload)}],
            },
        }
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
"""


@pytest.mark.asyncio
async def test_mcp_mesh_list_tools_and_call_real_stdio_server(
    runtime: Runtime,
    tmp_path: Path,
) -> None:
    script_path = tmp_path / "dummy_mcp.py"
    script_path.write_text(_DUMMY_MCP_SERVER_SCRIPT, encoding="utf-8")

    await runtime.invoke(
        "mcp_mesh_connect",
        {
            "name": "rea-test",
            "transport": "stdio",
            "command": f'"{sys.executable}" "{script_path}"',
            "display_name": "Dummy REA Server",
        },
    )

    listed = await runtime.invoke("mcp_mesh_list_tools", {"name": "rea-test"})
    assert listed.data["status"] == "success"
    assert listed.data["tools_count"] == 1
    assert listed.data["tools"][0]["name"] == "inspect_pe"

    called = await runtime.invoke(
        "mcp_mesh_call",
        {
            "server_name": "rea-test",
            "tool_name": "inspect_pe",
            "arguments": {"path": "sample.exe"},
        },
    )
    assert called.data["status"] == "success"
    assert called.data["is_error"] is False
    assert called.data["parsed_json"] == {
        "tool": "inspect_pe",
        "path": "sample.exe",
        "arch": "x86_64",
    }

    await runtime.invoke("mcp_mesh_toggle", {"name": "rea-test", "enabled": False})
    with pytest.raises(StateError):
        await runtime.invoke(
            "mcp_mesh_call",
            {"server_name": "rea-test", "tool_name": "inspect_pe", "arguments": {}},
        )

    with pytest.raises(NotFoundError):
        await runtime.invoke("mcp_mesh_list_tools", {"name": "missing-server"})
