"""Dynamic iOS device control tools routed through iphone-control or mobile-mcp."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from raa.policy.scopes import DYNAMIC_DEVICE
from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import DYNAMIC


class IosDeviceInteractInput(BaseModel):
    """Parameters to interact with a connected iOS device via MCP."""

    action: Literal["tap", "swipe", "type_text", "screenshot"] = Field(
        description="Device interaction action to execute."
    )
    project_id: str | None = Field(
        default=None,
        description="RAA project ID used for policy scope enforcement.",
    )
    server_name: Literal["iphone-control", "mobile-mcp"] = Field(
        default="iphone-control",
        description="Connected iOS control MCP server.",
    )
    x: int | None = Field(default=None, ge=0, description="X coordinate for tap/swipe.")
    y: int | None = Field(default=None, ge=0, description="Y coordinate for tap/swipe.")
    end_x: int | None = Field(default=None, ge=0, description="End X coordinate for swipe.")
    end_y: int | None = Field(default=None, ge=0, description="End Y coordinate for swipe.")
    text: str | None = Field(default=None, description="Text to type for type_text action.")


class IosDeviceTreeInput(BaseModel):
    """Parameters to dump the live accessibility UI tree from a connected iOS device."""

    project_id: str | None = Field(
        default=None,
        description="RAA project ID used for policy scope enforcement.",
    )
    server_name: Literal["iphone-control", "mobile-mcp"] = Field(
        default="iphone-control",
        description="Connected iOS control MCP server.",
    )


_IPHONE_CONTROL_TOOL_MAP: dict[str, str] = {
    "tap": "iphone_tap",
    "swipe": "iphone_swipe",
    "type_text": "iphone_type_text",
    "screenshot": "iphone_screenshot",
}

_MOBILE_MCP_TOOL_MAP: dict[str, str] = {
    "tap": "mobile_click_on_screen_at_coordinates",
    "swipe": "mobile_swipe_on_screen",
    "type_text": "mobile_type_keys",
    "screenshot": "mobile_take_screenshot",
}


async def _ios_device_interact(
    ctx: ToolContext,
    args: IosDeviceInteractInput,
) -> ToolOutcome:
    tool_map = (
        _IPHONE_CONTROL_TOOL_MAP if args.server_name == "iphone-control" else _MOBILE_MCP_TOOL_MAP
    )
    remote_tool = tool_map[args.action]
    payload: dict[str, Any] = {}
    if args.x is not None:
        payload["x"] = args.x
    if args.y is not None:
        payload["y"] = args.y
    if args.end_x is not None:
        payload["end_x"] = args.end_x
    if args.end_y is not None:
        payload["end_y"] = args.end_y
    if args.text is not None:
        payload["text"] = args.text

    res = await ctx.runtime.mcp_mesh.call_remote_tool(
        args.server_name,
        remote_tool,
        payload,
        timeout_seconds=30.0,
    )
    return ToolOutcome(
        data={
            "server": args.server_name,
            "action": args.action,
            "remote_tool": remote_tool,
            "result": res,
        }
    )


async def _ios_device_tree(
    ctx: ToolContext,
    args: IosDeviceTreeInput,
) -> ToolOutcome:
    remote_tool = (
        "iphone_list_elements"
        if args.server_name == "iphone-control"
        else "mobile_list_elements_on_screen"
    )
    res = await ctx.runtime.mcp_mesh.call_remote_tool(
        args.server_name,
        remote_tool,
        {},
        timeout_seconds=30.0,
    )
    return ToolOutcome(
        data={
            "server": args.server_name,
            "remote_tool": remote_tool,
            "result": res,
        }
    )


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="ios_device_interact",
            title="Interact With Live iOS Device",
            description=(
                "Execute tap, swipe, text input, or screenshot actions on a connected iPhone/iPad "
                "via iphone-control or mobile-mcp."
            ),
            input_model=IosDeviceInteractInput,
            handler=_ios_device_interact,
            family="platform",
            profiles=DYNAMIC,
            scopes=frozenset({DYNAMIC_DEVICE}),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="ios_device_tree",
            title="Dump Live iOS UI Accessibility Tree",
            description=(
                "Retrieve the live UI accessibility hierarchy from a connected iPhone/iPad "
                "via iphone-control or mobile-mcp."
            ),
            input_model=IosDeviceTreeInput,
            handler=_ios_device_tree,
            family="platform",
            profiles=DYNAMIC,
            scopes=frozenset({DYNAMIC_DEVICE}),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
