"""Tests for Phase 1 external MCP mesh presets, toolchain entries, and wrapper tools."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from raa.errors import PolicyDeniedError
from raa.runtime import Runtime
from raa.services.mcp_mesh import CATALOGUED_CONNECTORS
from raa.services.tool_manager import SUPPORTED_TOOLS

_DUMMY_PHASE1_MCP_SCRIPT = """
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
                "serverInfo": {"name": "dummy-phase1", "version": "1.0.0"},
            },
        }
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
    elif method == "tools/call":
        params = msg.get("params") or {}
        args = params.get("arguments") or {}
        payload = {"called": params.get("name"), "args": args}
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


def test_phase1_catalog_and_toolchain_entries() -> None:
    for tool_id in ("xerj", "iphone-control", "hetty"):
        assert tool_id in SUPPORTED_TOOLS
    for connector_id in (
        "xerj",
        "iphone-control",
        "mobile-mcp",
        "openosint",
        "burpsuite-mcp-bridge",
        "kali-burp-mcp-bridge",
    ):
        assert connector_id in CATALOGUED_CONNECTORS


@pytest.mark.asyncio
async def test_source_hybrid_search_fallback_and_forward(
    runtime: Runtime,
    tmp_path: Path,
) -> None:
    project = await runtime.invoke("project_create", {"name": "search-test"})
    pid = project.data["id"]

    # Without xerj connected, source_hybrid_search returns graceful fallback guidance
    fallback = await runtime.invoke(
        "source_hybrid_search",
        {"query": "Retrofit", "limit": 5, "project_id": pid},
    )
    assert fallback.data["backend"] == "fallback_required"
    assert fallback.data["fallback_tool"] == "source_search"
    assert fallback.warnings

    # Connect dummy xerj stdio server and verify forwarding
    script_path = tmp_path / "dummy_xerj.py"
    script_path.write_text(_DUMMY_PHASE1_MCP_SCRIPT, encoding="utf-8")
    await runtime.invoke(
        "mcp_mesh_connect",
        {
            "name": "xerj",
            "transport": "stdio",
            "command": f'"{sys.executable}" "{script_path}"',
        },
    )
    forwarded = await runtime.invoke(
        "source_hybrid_search",
        {"query": "Retrofit", "limit": 5, "project_id": pid},
    )
    assert forwarded.data["backend"] == "xerj"
    assert forwarded.data["result"]["parsed_json"]["called"] == "search"
    assert forwarded.data["result"]["parsed_json"]["args"]["query"] == "Retrofit"


@pytest.mark.asyncio
async def test_ios_device_tools_scope_and_forward(
    runtime: Runtime,
    tmp_path: Path,
) -> None:
    script_path = tmp_path / "dummy_iphone.py"
    script_path.write_text(_DUMMY_PHASE1_MCP_SCRIPT, encoding="utf-8")
    await runtime.invoke(
        "mcp_mesh_connect",
        {
            "name": "iphone-control",
            "transport": "stdio",
            "command": f'"{sys.executable}" "{script_path}"',
        },
    )

    # Without dynamic.device scope, invocation fails closed
    with pytest.raises(PolicyDeniedError):
        await runtime.invoke(
            "ios_device_interact",
            {"action": "tap", "x": 100, "y": 200},
            profile="dynamic",
        )

    # Create project with dynamic.device scope and verify forwarding
    project = await runtime.invoke(
        "project_create",
        {"name": "ios-test", "scopes": ["project.read", "dynamic.device"]},
    )
    pid = project.data["id"]

    tap_res = await runtime.invoke(
        "ios_device_interact",
        {"action": "tap", "x": 100, "y": 200, "project_id": pid},
        profile="dynamic",
    )
    assert tap_res.data["remote_tool"] == "iphone_tap"
    assert tap_res.data["result"]["parsed_json"]["args"] == {"x": 100, "y": 200}

    tree_res = await runtime.invoke(
        "ios_device_tree",
        {"project_id": pid},
        profile="dynamic",
    )
    assert tree_res.data["remote_tool"] == "iphone_list_elements"
    assert tree_res.data["result"]["parsed_json"]["called"] == "iphone_list_elements"
