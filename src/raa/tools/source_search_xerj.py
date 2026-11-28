"""Hybrid source search backed by Xerj MCP when connected, with DexIndex fallback guidance."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from raa.errors import RAAError
from raa.policy.scopes import STATIC_READ
from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import CORE


class SourceHybridSearchInput(BaseModel):
    """Parameters for AST-aware hybrid search over decompiled project artifacts."""

    query: str = Field(
        min_length=1,
        description="Search query (symbol, string, API path, or natural-language concept).",
    )
    project_id: str | None = Field(
        default=None,
        description="Optional RAA project ID to scope the search path.",
    )
    server_name: str = Field(
        default="xerj",
        description="Connected MCP search server name (defaults to 'xerj').",
    )
    tool_name: str = Field(
        default="search",
        description="Remote search tool exposed by the MCP search server.",
    )
    limit: int = Field(default=20, ge=1, le=200, description="Maximum number of hits to return.")


async def _source_hybrid_search(
    ctx: ToolContext,
    args: SourceHybridSearchInput,
) -> ToolOutcome:
    arguments: dict[str, Any] = {
        "query": args.query,
        "limit": args.limit,
    }
    if args.project_id:
        arguments["project_id"] = args.project_id

    try:
        res = await ctx.runtime.mcp_mesh.call_remote_tool(
            args.server_name,
            args.tool_name,
            arguments,
            timeout_seconds=30.0,
        )
        return ToolOutcome(
            data={
                "backend": args.server_name,
                "query": args.query,
                "result": res,
            }
        )
    except RAAError as exc:
        return ToolOutcome(
            data={
                "backend": "fallback_required",
                "query": args.query,
                "reason": exc.message,
                "fallback_tool": "source_search",
            },
            warnings=[
                f"External search server '{args.server_name}' is not active ({exc.code}); "
                "use source_search for DexIndex lookup or connect xerj via mcp_mesh_connect."
            ],
        )


def register(registry: CapabilityRegistry) -> None:
    registry.register(
        ToolSpec(
            name="source_hybrid_search",
            title="Hybrid Decompiled Source Search",
            description=(
                "Run AST-aware BM25 + vector hybrid search over decompiled Java/Smali/logs via Xerj MCP, "
                "with graceful guidance to fall back to source_search when Xerj is not connected."
            ),
            input_model=SourceHybridSearchInput,
            handler=_source_hybrid_search,
            family="source",
            profiles=CORE,
            scopes=frozenset({STATIC_READ}),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
