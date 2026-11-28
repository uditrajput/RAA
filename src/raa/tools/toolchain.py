"""Toolchain and engine management MCP tools."""

from __future__ import annotations

from pydantic import BaseModel, Field

from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import CORE


class ToolManagerListInput(BaseModel):
    """Parameters to query current tool installations."""

    pass


class ToolManagerDownloadInput(BaseModel):
    """Parameters to download and unpack reversing tool binaries."""

    tool_name: str = Field(
        description="Tool identifier: 'jadx', 'apktool', 'platform-tools', 'ghidra', 'frida', 'uber-apk-signer', or 'all'."
    )
    force: bool = Field(default=False, description="Force re-download even if already installed.")


class ToolManagerVerifyInput(BaseModel):
    """Parameters to cryptographically verify tool binary checksums."""

    tool_name: str = Field(description="Tool identifier to verify.")


class ToolManagerAutoPathInput(BaseModel):
    """Parameters to dynamically inject tool binaries into the system PATH."""

    tool_name: str | None = Field(
        default=None, description="Optional specific tool to add, or None for all installed."
    )


class ToolManagerDeleteInput(BaseModel):
    """Parameters to safely uninstall tool binaries and reclaim disk space."""

    tool_name: str = Field(description="Tool identifier to delete.")


class ToolManagerStatusInput(BaseModel):
    """Parameters to query overall toolchain health and readiness."""

    pass


async def _tool_manager_list(ctx: ToolContext, args: ToolManagerListInput) -> ToolOutcome:
    tools = ctx.runtime.tool_manager.list_tools()
    return ToolOutcome(data={"tools": tools, "total": len(tools)})


async def _tool_manager_download(ctx: ToolContext, args: ToolManagerDownloadInput) -> ToolOutcome:
    res = ctx.runtime.tool_manager.download_tool(name=args.tool_name, force=args.force)
    return ToolOutcome(data=res)


async def _tool_manager_verify(ctx: ToolContext, args: ToolManagerVerifyInput) -> ToolOutcome:
    res = ctx.runtime.tool_manager.verify_tool(name=args.tool_name)
    return ToolOutcome(data=res)


async def _tool_manager_auto_path(ctx: ToolContext, args: ToolManagerAutoPathInput) -> ToolOutcome:
    res = ctx.runtime.tool_manager.auto_path(name=args.tool_name)
    return ToolOutcome(data=res)


async def _tool_manager_delete(ctx: ToolContext, args: ToolManagerDeleteInput) -> ToolOutcome:
    res = ctx.runtime.tool_manager.delete_tool(name=args.tool_name)
    return ToolOutcome(data=res)


async def _tool_manager_status(ctx: ToolContext, args: ToolManagerStatusInput) -> ToolOutcome:
    res = ctx.runtime.tool_manager.get_status()
    return ToolOutcome(data=res)


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="tool_manager_list",
            title="List Toolchain Engines",
            description="Inquire current installation status, binary versions, and disk usage across reversing engines.",
            input_model=ToolManagerListInput,
            handler=_tool_manager_list,
            family="toolchain",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="tool_manager_download",
            title="Download Toolchain Engine",
            description="Download and unpack verified engine bundles (JADX, Apktool, Platform-Tools, Ghidra, Frida) into workspace storage.",
            input_model=ToolManagerDownloadInput,
            handler=_tool_manager_download,
            family="toolchain",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="tool_manager_verify",
            title="Verify Tool Checksum",
            description="Cryptographically verify downloaded binaries against official SHA-256 release digests.",
            input_model=ToolManagerVerifyInput,
            handler=_tool_manager_verify,
            family="toolchain",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="tool_manager_auto_path",
            title="Auto-Path Toolchain Binaries",
            description="Dynamically register tool binaries into RAA's runtime environment PATH without requiring terminal reboots.",
            input_model=ToolManagerAutoPathInput,
            handler=_tool_manager_auto_path,
            family="toolchain",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="tool_manager_delete",
            title="Delete Toolchain Binary",
            description="Safely uninstall engine binaries and reclaim disk space.",
            input_model=ToolManagerDeleteInput,
            handler=_tool_manager_delete,
            family="toolchain",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="tool_manager_status",
            title="Toolchain Health Status",
            description="Comprehensive health and readiness check of the reversing toolchain.",
            input_model=ToolManagerStatusInput,
            handler=_tool_manager_status,
            family="toolchain",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
