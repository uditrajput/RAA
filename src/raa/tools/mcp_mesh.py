"""External MCP Mesh and Service Connector MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import CORE


class McpMeshConnectInput(BaseModel):
    """Parameters to connect a third-party external MCP server."""

    name: str = Field(min_length=1, description="Identifier for external MCP server.")
    transport: Literal["stdio", "sse", "streamable-http"] = Field(
        default="stdio", description="Communication transport protocol."
    )
    command: str | None = Field(default=None, description="Command to execute for stdio transport.")
    url: str | None = Field(
        default=None, description="Remote URL for sse or streamable-http transport."
    )
    display_name: str = Field(default="", description="Human-readable title.")


class McpMeshDisconnectInput(BaseModel):
    """Parameters to disconnect an external MCP server."""

    name: str = Field(description="Name of the MCP server to disconnect.")


class McpMeshListInput(BaseModel):
    """Parameters to list all configured and active external MCP servers."""

    pass


class McpMeshInspectInput(BaseModel):
    """Parameters to inspect schemas and capabilities of a connected MCP server."""

    name: str = Field(description="Name of the MCP server to inspect.")


class McpMeshTestInput(BaseModel):
    """Parameters to execute a ping/handshake test against an external MCP server."""

    name: str = Field(description="Name of the MCP server to test.")


class McpMeshToggleInput(BaseModel):
    """Parameters to enable or disable an external MCP connector."""

    name: str = Field(description="Name of the MCP server to toggle.")
    enabled: bool = Field(description="True to enable, False to disable.")


class McpMeshListToolsInput(BaseModel):
    """Parameters to live-discover tools and schemas from a connected MCP server."""

    name: str = Field(
        description="Name of the connected MCP server (e.g. 'rea', 'craft-anything')."
    )
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)


class McpMeshCallInput(BaseModel):
    """Parameters to forward a tool call to a connected external MCP server."""

    server_name: str = Field(
        description="Name of the connected MCP server (e.g. 'rea', 'craft-anything')."
    )
    tool_name: str = Field(description="Exact tool name exposed by that MCP server.")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON arguments object to pass to the remote MCP tool.",
    )
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)


async def _mcp_mesh_connect(ctx: ToolContext, args: McpMeshConnectInput) -> ToolOutcome:
    res = ctx.runtime.mcp_mesh.connect(
        name=args.name,
        transport=args.transport,
        command=args.command,
        url=args.url,
        display_name=args.display_name,
    )
    return ToolOutcome(data=res)


async def _mcp_mesh_disconnect(ctx: ToolContext, args: McpMeshDisconnectInput) -> ToolOutcome:
    res = ctx.runtime.mcp_mesh.disconnect(name=args.name)
    return ToolOutcome(data=res)


async def _mcp_mesh_list(ctx: ToolContext, args: McpMeshListInput) -> ToolOutcome:
    servers = ctx.runtime.mcp_mesh.list_connectors()
    return ToolOutcome(data={"servers": servers, "total": len(servers)})


async def _mcp_mesh_inspect(ctx: ToolContext, args: McpMeshInspectInput) -> ToolOutcome:
    res = ctx.runtime.mcp_mesh.inspect_server(name=args.name)
    return ToolOutcome(data=res)


async def _mcp_mesh_test(ctx: ToolContext, args: McpMeshTestInput) -> ToolOutcome:
    res = ctx.runtime.mcp_mesh.test_ping(name=args.name)
    return ToolOutcome(data=res)


async def _mcp_mesh_toggle(ctx: ToolContext, args: McpMeshToggleInput) -> ToolOutcome:
    res = ctx.runtime.mcp_mesh.toggle(name=args.name, enabled=args.enabled)
    return ToolOutcome(data=res)


async def _mcp_mesh_list_tools(ctx: ToolContext, args: McpMeshListToolsInput) -> ToolOutcome:
    res = await ctx.runtime.mcp_mesh.list_remote_tools(
        args.name,
        timeout_seconds=args.timeout_seconds,
    )
    return ToolOutcome(data=res)


async def _mcp_mesh_call(ctx: ToolContext, args: McpMeshCallInput) -> ToolOutcome:
    res = await ctx.runtime.mcp_mesh.call_remote_tool(
        args.server_name,
        args.tool_name,
        args.arguments,
        timeout_seconds=args.timeout_seconds,
    )
    return ToolOutcome(data=res)


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="mcp_mesh_connect",
            title="Connect External MCP Server",
            description="Register and initialize an external MCP server connection (stdio child process or remote sse/streamable-http).",
            input_model=McpMeshConnectInput,
            handler=_mcp_mesh_connect,
            family="mcp_mesh",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="mcp_mesh_disconnect",
            title="Disconnect External MCP Server",
            description="Disconnect an external MCP server and safely unregister its exposed tools from RAA's registry.",
            input_model=McpMeshDisconnectInput,
            handler=_mcp_mesh_disconnect,
            family="mcp_mesh",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="mcp_mesh_list",
            title="List External MCP Servers",
            description="List all configured and active external MCP servers, transport protocols, connection health, and ingested tool counts.",
            input_model=McpMeshListInput,
            handler=_mcp_mesh_list,
            family="mcp_mesh",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="mcp_mesh_inspect",
            title="Inspect External MCP Server",
            description="Deeply inspect the schemas, descriptions, and parameter definitions of tools exposed by a connected MCP server.",
            input_model=McpMeshInspectInput,
            handler=_mcp_mesh_inspect,
            family="mcp_mesh",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="mcp_mesh_test",
            title="Test External MCP Server Ping",
            description="Execute an immediate JSON-RPC ping handshake and response latency probe against an external MCP server.",
            input_model=McpMeshTestInput,
            handler=_mcp_mesh_test,
            family="mcp_mesh",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="mcp_mesh_toggle",
            title="Toggle External MCP Server",
            description="Temporarily enable or disable an external MCP connector without deleting its saved credentials or configuration.",
            input_model=McpMeshToggleInput,
            handler=_mcp_mesh_toggle,
            family="mcp_mesh",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="mcp_mesh_list_tools",
            title="List Live Tools on External MCP Server",
            description="Connect to a registered MCP server (such as rea or craft-anything), run tools/list, and return live tool schemas.",
            input_model=McpMeshListToolsInput,
            handler=_mcp_mesh_list_tools,
            family="mcp_mesh",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="mcp_mesh_call",
            title="Call Tool on External MCP Server",
            description="Forward a tools/call invocation to a connected external MCP server (e.g. rea or craft-anything) and return its result.",
            input_model=McpMeshCallInput,
            handler=_mcp_mesh_call,
            family="mcp_mesh",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
