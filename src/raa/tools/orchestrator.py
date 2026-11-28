"""Smart Unified Orchestrator MCP tool combining Tools, MCP Mesh, Skills, and Agents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import CORE
from raa.services.orchestrator import SmartOrchestratorService


class SmartOrchestrateInput(BaseModel):
    """Parameters to plan or execute a smart single/combined RAA workflow."""

    goal: str = Field(
        min_length=1,
        description="Natural-language objective (e.g. 'triage apk and design compose ui').",
    )
    mode: Literal["auto", "single", "combined"] = Field(
        default="auto",
        description="Orchestration mode: auto-select, single-tool, or combined multi-tool/MCP/skill pipeline.",
    )
    project_id: str | None = Field(default=None, description="Optional RAA project ID.")
    target_path: str | None = Field(
        default=None, description="Optional APK, IPA, or screenshot path."
    )
    notify_channel: Literal["telegram", "whatsapp"] | None = Field(
        default=None,
        description="Optional mobile channel to send a live progress report to.",
    )
    notify_recipient: str | None = Field(
        default=None,
        description="Recipient chat ID or phone number for progress notifications.",
    )


_ORCHESTRATOR = SmartOrchestratorService()


async def _smart_orchestrate(ctx: ToolContext, args: SmartOrchestrateInput) -> ToolOutcome:
    plan = _ORCHESTRATOR.build_execution_plan(
        args.goal,
        mode=args.mode,
        target_path=args.target_path,
        runtime=ctx.runtime,
    )
    notification = None
    if args.notify_channel and args.notify_recipient:
        notification = ctx.runtime.channels.broadcast_progress(
            stage="Orchestration Plan Ready",
            progress_pct=25,
            summary=f"Goal: {args.goal} ({plan['step_count']} steps in {plan['mode']} mode)",
            channel=args.notify_channel,
            recipient=args.notify_recipient,
            project_id=args.project_id,
        )
    return ToolOutcome(data={**plan, "notification": notification})


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="smart_orchestrate",
            title="Smart Multi-Tool, MCP, Skill & Agent Orchestrator",
            description=(
                "Intelligently select and combine RAA tools, external MCP Mesh servers, Skills, "
                "and Agent roles for a goal (single or combined), with optional WhatsApp/Telegram progress reporting."
            ),
            input_model=SmartOrchestrateInput,
            handler=_smart_orchestrate,
            family="agents",
            profiles=CORE,
            scopes=frozenset(),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
