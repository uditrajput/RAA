"""Interactive Setup UI and Lifecycle MCP tools."""

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


class OpenSetupUiInput(BaseModel):
    """Parameters to launch or retrieve the interactive setup console."""

    auto_open_browser: bool = Field(
        default=False, description="Attempt to launch local browser window."
    )
    port: int = Field(default=8765, ge=1024, le=65535, description="Local web console port.")


class SetupStateGetInput(BaseModel):
    """Parameters to inspect current onboarding state and preferences."""

    pass


class SetupSkipRegisterInput(BaseModel):
    """Parameters to register a skip action and switch to pure-Python engines."""

    pass


class SetupReopenRequestInput(BaseModel):
    """Parameters to request reopening the setup console on-demand."""

    pass


async def _open_setup_ui(ctx: ToolContext, args: OpenSetupUiInput) -> ToolOutcome:
    setup_url = f"http://127.0.0.1:{args.port}/setup"
    state = ctx.runtime.tool_manager.get_state()
    tools = ctx.runtime.tool_manager.list_tools()

    # Return complete interactive UI metadata card
    return ToolOutcome(
        data={
            "status": "ready",
            "setup_url": setup_url,
            "port": args.port,
            "browser_launch_requested": args.auto_open_browser,
            "current_state": state,
            "installed_tools_count": len([t for t in tools if t["installed"]]),
            "total_tools_count": len(tools),
            "design_system": "Cyber-Glass Neon Design System (v4.0.0)",
            "ui_card": {
                "title": "🛡️ RAA Studio v4.0.0 Setup & Tool Manager Console",
                "description": "Interactive onboarding wizard & persistent tool manager console.",
                "actions": [
                    {"label": "Open Setup Web UI", "url": setup_url},
                    {"label": "Download All Missing Tools", "command": "raa tools install all"},
                    {"label": "Skip for Now (Pure-Python)", "action": "setup_skip_register"},
                ],
            },
        }
    )


async def _setup_state_get(ctx: ToolContext, args: SetupStateGetInput) -> ToolOutcome:
    state = ctx.runtime.tool_manager.get_state()
    tools = ctx.runtime.tool_manager.list_tools()
    return ToolOutcome(
        data={
            "state": state,
            "tools_summary": {
                "installed": [t["tool_id"] for t in tools if t["installed"]],
                "missing": [t["tool_id"] for t in tools if not t["installed"]],
            },
        }
    )


async def _setup_skip_register(ctx: ToolContext, args: SetupSkipRegisterInput) -> ToolOutcome:
    res = ctx.runtime.tool_manager.register_skip()
    return ToolOutcome(data=res)


async def _setup_reopen_request(ctx: ToolContext, args: SetupReopenRequestInput) -> ToolOutcome:
    res = ctx.runtime.tool_manager.reopen_setup()
    return ToolOutcome(data=res)


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="open_setup_ui",
            title="Open Setup & Tool Manager UI",
            description="Spin up and launch the interactive React/Tailwind visual onboarding wizard on local loopback.",
            input_model=OpenSetupUiInput,
            handler=_open_setup_ui,
            family="setup",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="setup_state_get",
            title="Get Setup State",
            description="Retrieve current onboarding progress, skipped status, and tool configuration.",
            input_model=SetupStateGetInput,
            handler=_setup_state_get,
            family="setup",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    registry.register(
        ToolSpec(
            name="setup_skip_register",
            title="Skip Setup Wizard",
            description="Record user selection to skip onboarding and activate pure-Python fallback engines.",
            input_model=SetupSkipRegisterInput,
            handler=_setup_skip_register,
            family="setup",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=False),
        )
    )
    registry.register(
        ToolSpec(
            name="setup_reopen_request",
            title="Reopen Setup Console",
            description="Re-trigger the onboarding console on-demand from conversational chat.",
            input_model=SetupReopenRequestInput,
            handler=_setup_reopen_request,
            family="setup",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=False, idempotent=True),
        )
    )
