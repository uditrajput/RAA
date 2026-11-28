"""Built-in tool registration.

Modules are imported inside ``build_registry`` so the registry has no import
cycle with the runtime or surface packages.
"""

from __future__ import annotations

from functools import lru_cache

from raa.registry.models import CapabilityRegistry


@lru_cache(maxsize=1)
def _build_base_registry() -> CapabilityRegistry:
    from raa.tools import (
        admin,
        advanced_binary,
        analysis,
        api,
        artifacts,
        channels,
        cognitive,
        diff,
        dynamic,
        enterprise,
        evidence,
        evolution,
        frameworks,
        graph,
        mcp_mesh,
        native,
        offensive,
        orchestrator,
        platform,
        platform_ios_dynamic,
        rebuild,
        recipes,
        security,
        setup,
        source_search_xerj,
        swarm,
        toolchain,
        ui,
        ui_reconstruction,
        unpacking,
        vault_shield,
        wireless_tv,
    )

    registry = CapabilityRegistry()
    for module in (
        platform,
        artifacts,
        analysis,
        frameworks,
        native,
        graph,
        ui,
        dynamic,
        evidence,
        admin,
        recipes,
        api,
        unpacking,
        diff,
        security,
        rebuild,
        swarm,
        cognitive,
        advanced_binary,
        ui_reconstruction,
        enterprise,
        offensive,
        toolchain,
        channels,
        setup,
        evolution,
        vault_shield,
        mcp_mesh,
        wireless_tv,
        source_search_xerj,
        platform_ios_dynamic,
        orchestrator,
    ):
        module.register(registry)
    return registry


def build_registry() -> CapabilityRegistry:
    return _build_base_registry().clone()


__all__ = ["build_registry"]
