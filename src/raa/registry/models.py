"""Registry contracts shared by MCP, REST, CLI and the Python SDK."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from raa.config import ProfileName
from raa.domain.models import Project

ToolCost = Literal["fast", "slow", "device", "network"]
ToolHandler = Callable[["ToolContext", Any], Awaitable["ToolOutcome"]]


class ToolInput(BaseModel):
    """Base class for tool arguments. Unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True, slots=True)
class ToolAnnotations:
    read_only: bool = True
    destructive: bool = False
    idempotent: bool = True
    open_world: bool = False


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    title: str
    description: str
    input_model: type[BaseModel]
    handler: ToolHandler
    family: str
    scopes: frozenset[str] = frozenset()
    profiles: frozenset[str] = frozenset({"core", "full"})
    annotations: ToolAnnotations = field(default_factory=ToolAnnotations)
    output_model: type[BaseModel] | None = None
    cost: ToolCost = "fast"
    device_required: bool = False
    mutates_artifact: bool = False
    version: str = "0.1.0"

    def input_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema(mode="validation")

    def output_schema(self) -> dict[str, Any] | None:
        if self.output_model is None:
            return None
        return self.output_model.model_json_schema(mode="serialization")


@dataclass(slots=True)
class ToolOutcome:
    data: Any
    evidence_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolContext:
    runtime: Any
    profile: ProfileName
    surface: str
    request_id: str
    project: Project | None = None


class ToolEnvelope(BaseModel):
    """Uniform response returned by every surface."""

    tool: str
    version: str
    request_id: str
    surface: str
    profile: ProfileName
    data: Any
    evidence_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class CapabilityRegistry:
    """Ordered, duplicate-safe tool collection."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._profile_cache: dict[ProfileName, list[ToolSpec]] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._tools:
            raise ValueError(f"Duplicate tool registration: {spec.name}")
        if spec.output_model is not None and not issubclass(spec.output_model, BaseModel):
            raise TypeError(f"output_model for {spec.name} must be a Pydantic model")
        self._tools[spec.name] = spec
        self._profile_cache.clear()
        return spec

    def clone(self) -> CapabilityRegistry:
        copy = CapabilityRegistry()
        copy._tools = dict(self._tools)
        return copy

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools)

    def for_profile(self, profile: ProfileName) -> list[ToolSpec]:
        cached = self._profile_cache.get(profile)
        if cached is not None:
            return cached
        result = (
            self.all()
            if profile == "full"
            else [spec for spec in self._tools.values() if profile in spec.profiles]
        )
        self._profile_cache[profile] = result
        return result

    def count(self) -> int:
        return len(self._tools)
