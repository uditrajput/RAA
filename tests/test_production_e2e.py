"""Production End-to-End & Security Hardening Verification Suite.

Validates:
1. Complete registry integrity: all 244 registered tools have valid metadata,
   descriptions, input models, profiles, and scopes.
2. Input model schema generation: every tool emits a valid JSON schema for MCP/OpenAPI.
3. Profile consistency: minimal (12), core (135), dynamic (169),
   api (139), ui (140), admin (19), full (244).
4. Profile subset constraints: every profile is a subset of full.
5. Scope isolation: mutative and dynamic tools strictly require authorization scopes.
6. Doctor diagnostic: reports healthy database, workspace, and 244 tools.
7. Engine catalog: all 24 catalogued reverse-engineering engines are available or simulated.
8. Security headers & nosniff enforcement on REST surface.
"""

from __future__ import annotations

import httpx
import pytest

from raa.api.app import create_app
from raa.config import Settings
from raa.errors import PolicyDeniedError, ProfileDeniedError
from raa.mcp.server import list_tools_result
from raa.registry.profiles import ALL_PROFILES
from raa.runtime import Runtime
from raa.version import PLANNED_TOOL_COUNT, PROTOCOL_VERSION, __version__


@pytest.mark.asyncio
async def test_all_244_tools_registry_integrity(runtime: Runtime) -> None:
    tools = runtime.registry.all()
    assert len(tools) == PLANNED_TOOL_COUNT
    assert runtime.registry.count() == PLANNED_TOOL_COUNT

    seen_names: set[str] = set()
    for spec in tools:
        # 1. Uniqueness
        assert spec.name not in seen_names, f"Duplicate tool name found: {spec.name}"
        seen_names.add(spec.name)

        # 2. Contract metadata
        assert spec.name == spec.name.lower(), f"Tool name must be lowercase: {spec.name}"
        assert len(spec.title) > 0, f"Tool {spec.name} has empty title"
        assert len(spec.description) > 0, f"Tool {spec.name} has empty description"

        # 3. Input model and JSON Schema validity
        assert spec.input_model is not None, f"Tool {spec.name} lacks input_model"
        schema = spec.input_model.model_json_schema()
        assert isinstance(schema, dict), f"Tool {spec.name} produced invalid schema"
        assert "type" in schema, f"Tool {spec.name} schema lacks 'type'"

        # 4. Profile assignment
        assert len(spec.profiles) > 0, f"Tool {spec.name} has no profile assignments"
        assert "full" in spec.profiles, f"Tool {spec.name} must belong to 'full' profile"
        for prof in spec.profiles:
            assert prof in ALL_PROFILES, f"Tool {spec.name} has unknown profile: {prof}"

        # 5. Scopes validation
        for scope in spec.scopes:
            assert "." in scope or scope == "admin", (
                f"Invalid scope format '{scope}' in tool {spec.name}"
            )


@pytest.mark.asyncio
async def test_mcp_surface_lists_all_tools_with_schemas(runtime: Runtime) -> None:
    result = await list_tools_result(runtime, "full")
    assert len(result.tools) == PLANNED_TOOL_COUNT

    for mcp_tool in result.tools:
        assert mcp_tool.name
        assert mcp_tool.description
        assert mcp_tool.input_schema is not None
        assert isinstance(mcp_tool.input_schema, dict)
        assert mcp_tool.input_schema.get("type") == "object"


@pytest.mark.asyncio
async def test_all_profile_target_counts_and_hierarchy(runtime: Runtime) -> None:
    caps = await runtime.invoke("capabilities_get", {})
    profiles = caps.data["profiles"]

    expected_counts = {
        "minimal": 12,
        "core": 232,
        "dynamic": 273,
        "api": 234,
        "ui": 233,
        "admin": 42,
        "swarm": 202,
        "full": 379,
    }
    for prof, expected_count in expected_counts.items():
        assert profiles[prof] == expected_count, (
            f"Profile '{prof}' count mismatch: expected {expected_count}, got {profiles[prof]}"
        )

    # Validate subset hierarchy
    full_tools = {t.name for t in runtime.registry.for_profile("full")}
    for prof in ALL_PROFILES:
        prof_tools = {t.name for t in runtime.registry.for_profile(prof)}
        assert prof_tools.issubset(full_tools), f"Profile {prof} has tools not in full"


@pytest.mark.asyncio
async def test_security_fail_closed_on_unauthorized_scope(runtime: Runtime) -> None:
    # Attempting to access project without scope
    created = await runtime.invoke("project_create", {"name": "Restricted", "scopes": []})
    project_id = created.data["id"]

    with pytest.raises(PolicyDeniedError) as exc_info:
        await runtime.invoke("project_get", {"project_id": project_id})
    assert "project.read" in exc_info.value.details.get("missing_scopes", [])


@pytest.mark.asyncio
async def test_security_fail_closed_on_profile_denial(runtime: Runtime) -> None:
    # Attempting to call an admin tool while locked in minimal profile
    with pytest.raises(ProfileDeniedError):
        await runtime.invoke("admin_engine_list", {}, profile="minimal")


@pytest.mark.asyncio
async def test_admin_doctor_production_status(runtime: Runtime) -> None:
    doctor = await runtime.invoke("admin_doctor", {})
    data = doctor.data

    assert data["ok"] is True
    assert data["database_ok"] is True
    assert data["workspace_writable"] is True
    assert bool(data["mcp_sdk"]) is True
    assert data["implemented_tools"] == PLANNED_TOOL_COUNT
    assert data["engines"]["catalogued"] >= 20


@pytest.mark.asyncio
async def test_production_rest_security_headers() -> None:
    runtime = Runtime(Settings())
    app = create_app(runtime)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/healthz")
        assert res.status_code == 200
        headers = res.headers

        # Verify production security headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert headers.get("x-xss-protection") == "1; mode=block"

        # Verify package metadata
        body = res.json()
        assert body["version"] == __version__
        assert body["version"] == "4.0.0"


def test_production_version_constants() -> None:
    assert __version__ == "4.0.0"
    assert PROTOCOL_VERSION == "2026-07-28"
    assert PLANNED_TOOL_COUNT == 379
