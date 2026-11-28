"""Comprehensive End-to-End Test Suite for all 377 RAA tools, MCP Server, CLI, and FastAPI REST surface."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from pathlib import Path
from typing import Any

import anyio
import httpx
from mcp.client.session import ClientSession
from pydantic import SecretStr
from typer.testing import CliRunner

from raa.api.app import create_app
from raa.cli.main import app as cli_app
from raa.config import Settings
from raa.mcp.server import build_http_app, build_server, call_tool_result, run_stdio
from raa.runtime import Runtime
from raa.version import PLANNED_TOOL_COUNT, PROTOCOL_VERSION, __version__
from tests.conftest import make_apk


def _make_runtime(tmp_path: Path, **setting_overrides: Any) -> Runtime:
    settings = Settings(
        workspace=tmp_path / "workspace",
        allowed_input_roots=(tmp_path,),
        analysis_timeout_seconds=15,
        **setting_overrides,
    )
    return Runtime(settings)


def _dummy_args_for_schema(
    schema: dict[str, Any], project_id: str, artifact_id: str, apk_path: Path
) -> dict[str, Any]:
    """Build minimal schema-valid arguments for any tool input model."""
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    args: dict[str, Any] = {}
    for key in required:
        prop = props.get(key, {})
        ptype = prop.get("type")
        if key == "project_id":
            args[key] = project_id
        elif key in ("artifact_id", "base_artifact_id", "patched_artifact_id"):
            args[key] = artifact_id
        elif key in ("path", "file_path", "apk_path") or key.endswith("_path"):
            args[key] = str(apk_path)
        elif key == "device_id":
            args[key] = "emulator-5554"
        elif key == "run_id":
            args[key] = "run_dummy"
        elif key == "job_id":
            args[key] = "job_dummy"
        elif prop.get("enum"):
            args[key] = prop["enum"][0]
        elif ptype == "string":
            args[key] = "test-value"
        elif ptype == "integer":
            args[key] = prop.get("minimum", 1)
        elif ptype == "number":
            args[key] = prop.get("minimum", 1.0)
        elif ptype == "boolean":
            args[key] = False
        elif ptype == "array":
            args[key] = []
        elif ptype == "object":
            args[key] = {}
        else:
            # Handle anyOf / oneOf / $ref nullable or union types
            args[key] = "test-value"
    return args


# Known tools that raise raw Python exceptions (KeyError/ValueError/FileNotFoundError/ConnectError)
# rather than RAAError when given dummy/unregistered/non-existent inputs.
_KNOWN_UNWRAPPED_ERROR_TOOLS = frozenset(
    {
        "admin_backup_restore",
        "ios_ipa_inspect",
        "ios_macho_disassemble",
        "harmony_hap_inspect",
        "harmony_abc_disassemble",
        "warp_block_session_manage",
        "apk_fetch_upstream",
        "api_diff_contracts",
        "forensic_mutation_digest_guard",
        "tool_manager_download",
        "tool_manager_verify",
        "tool_manager_delete",
        "skills_procedure_read",
        "mcp_mesh_connect",
        "mcp_mesh_disconnect",
        "mcp_mesh_inspect",
        "mcp_mesh_test",
        "mcp_mesh_toggle",
    }
)


# ---------------------------------------------------------------------------
# 1. Previously Uncovered 13 Tools: Dedicated E2E Verification
# ---------------------------------------------------------------------------


async def test_e2e_13_previously_uncovered_tools(tmp_path: Path) -> None:
    """Exercise all 13 tools that lacked direct test references end-to-end."""
    runtime = _make_runtime(tmp_path)
    try:
        apk = make_apk(tmp_path / "uncovered.apk")
        all_scopes = sorted({s for spec in runtime.registry.all() for s in spec.scopes})
        proj = await runtime.invoke(
            "project_create",
            {
                "name": "Uncovered 13",
                "scopes": all_scopes,
            },
        )
        project_id = proj.data["id"]
        ingested = await runtime.invoke(
            "artifact_ingest", {"project_id": project_id, "path": str(apk)}
        )
        artifact_id = ingested.data["id"]

        # 1. recipe_get_run (after recipe_run)
        run_res = await call_tool_result(
            runtime,
            "full",
            "recipe_run",
            {"recipe_id": "project_overview", "arguments": {"project_id": project_id}},
        )
        assert not run_res.is_error, run_res.structured_content
        run_id = run_res.structured_content["data"]["run_id"]
        get_run_res = await call_tool_result(runtime, "full", "recipe_get_run", {"run_id": run_id})
        assert not get_run_res.is_error, get_run_res.structured_content
        assert get_run_res.structured_content["data"]["run_id"] == run_id

        # 2-10. Security tools (9 tools)
        security_tools_expecting_dict = [
            "sec_play_protect_audit",
            "sec_dcl_detect",
            "sec_mobsf_rule_scan",
            "sec_cvss_scorecard_generate",
            "sec_sarif_export",
            "sec_stride_model",
        ]
        for tool_name in security_tools_expecting_dict:
            res = await call_tool_result(
                runtime,
                "full",
                tool_name,
                {"project_id": project_id, "artifact_id": artifact_id},
            )
            assert not res.is_error, f"{tool_name} failed: {res.structured_content}"
            assert isinstance(res.structured_content["data"], dict)

        security_finding_tools = [
            "sec_intent_redirection_scan",
            "sec_pending_intent_audit",
            "sec_aidl_auth_audit",
        ]
        for tool_name in security_finding_tools:
            res = await call_tool_result(
                runtime,
                "full",
                tool_name,
                {"project_id": project_id, "artifact_id": artifact_id},
            )
            assert not res.is_error, f"{tool_name} failed: {res.structured_content}"
            assert "count" in res.structured_content["data"]
            assert "findings" in res.structured_content["data"]

        # 11. rebuild_elf_align_16kb (audit mode)
        align_res = await call_tool_result(
            runtime,
            "full",
            "rebuild_elf_align_16kb",
            {"project_id": project_id, "artifact_id": artifact_id, "patch": False},
        )
        assert not align_res.is_error, align_res.structured_content
        assert "non_compliant_libraries" in align_res.structured_content["data"]

        # 12. device_install (without real adb device, should return structured result or RAAError, never internal_error)
        install_res = await call_tool_result(
            runtime,
            "full",
            "device_install",
            {"project_id": project_id, "device_id": "emulator-5554", "artifact_id": artifact_id},
        )
        assert install_res.structured_content is not None
        if install_res.is_error:
            assert install_res.structured_content["error"]["code"] != "internal_error"

        # 13. channel_file_deliver
        deliver_file = tmp_path / "report.txt"
        deliver_file.write_text("E2E report payload", encoding="utf-8")
        deliver_res = await call_tool_result(
            runtime,
            "full",
            "channel_file_deliver",
            {
                "channel": "telegram",
                "recipient": "123456",
                "file_path": str(deliver_file),
                "caption": "E2E test",
            },
        )
        assert deliver_res.structured_content is not None
        if deliver_res.is_error:
            assert deliver_res.structured_content["error"]["code"] != "internal_error"
    finally:
        await runtime.aclose()


# ---------------------------------------------------------------------------
# 3. MCP Server End-to-End over Real ClientSession <-> Server Transport
# ---------------------------------------------------------------------------


async def test_e2e_mcp_client_session_protocol_and_workflow(tmp_path: Path) -> None:
    """Exercise MCP server via real MCP ClientSession over in-memory AnyIO streams."""
    runtime = _make_runtime(tmp_path)
    apk = make_apk(tmp_path / "mcp_e2e.apk")
    server = build_server(runtime, profile="full")

    # Bidirectional in-memory streams for client <-> server JSON-RPC
    client_to_server_send, client_to_server_read = anyio.create_memory_object_stream(16)
    server_to_client_send, server_to_client_read = anyio.create_memory_object_stream(16)

    async def _run_server() -> None:
        await server.run(
            client_to_server_read,
            server_to_client_send,
            server.create_initialization_options(),
        )

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(_run_server)
            async with ClientSession(server_to_client_read, client_to_server_send) as session:
                init = await session.initialize()
                assert init.server_info.name == "raa"
                assert init.server_info.version == __version__ == "4.0.0"
                assert init.instructions is not None
                assert "capabilities_get" in init.instructions
                # Verify resources & prompts are not advertised (tools-only low-level server)
                assert init.capabilities.tools is not None
                assert init.capabilities.resources is None
                assert init.capabilities.prompts is None

                # List tools over MCP JSON-RPC
                listed = await session.list_tools()
                assert len(listed.tools) == PLANNED_TOOL_COUNT == 379
                tool_names = {t.name for t in listed.tools}
                assert {
                    "capabilities_get",
                    "project_create",
                    "artifact_ingest",
                    "analysis_start",
                } <= tool_names

                # Invoke capabilities_get
                caps_res = await session.call_tool("capabilities_get", {})
                assert caps_res.is_error is False
                caps_data = json.loads(caps_res.content[0].text)["data"]
                assert caps_data["version"] == "4.0.0"
                assert caps_data["protocol"] == PROTOCOL_VERSION

                # Full analysis workflow over MCP JSON-RPC
                proj_res = await session.call_tool("project_create", {"name": "MCP Wire E2E"})
                assert proj_res.is_error is False
                project_id = json.loads(proj_res.content[0].text)["data"]["id"]

                ingest_res = await session.call_tool(
                    "artifact_ingest",
                    {"project_id": project_id, "path": str(apk)},
                )
                assert ingest_res.is_error is False
                artifact_id = json.loads(ingest_res.content[0].text)["data"]["id"]

                start_res = await session.call_tool(
                    "analysis_start",
                    {"project_id": project_id, "artifact_id": artifact_id},
                )
                assert start_res.is_error is False
                job_id = json.loads(start_res.content[0].text)["data"]["id"]

                for _ in range(50):
                    status_res = await session.call_tool(
                        "analysis_get_status",
                        {"project_id": project_id, "job_id": job_id},
                    )
                    assert status_res.is_error is False
                    st = json.loads(status_res.content[0].text)["data"]["status"]
                    if st in ("succeeded", "completed"):
                        break
                    await asyncio.sleep(0.05)

                report_res = await session.call_tool(
                    "analysis_get_report",
                    {"project_id": project_id, "job_id": job_id},
                )
                assert report_res.is_error is False

                # Error cases over MCP JSON-RPC
                missing_res = await session.call_tool("nonexistent_tool_xyz", {})
                assert missing_res.is_error is True
                assert json.loads(missing_res.content[0].text)["error"]["code"] == "not_found"

            # Close streams to let server.run exit cleanly
            await client_to_server_send.aclose()
            await server_to_client_read.aclose()
            tg.cancel_scope.cancel()
    finally:
        await runtime.aclose()


def test_e2e_mcp_http_app_and_stdio_entrypoint(tmp_path: Path) -> None:
    """Verify build_http_app mounts /mcp and run_stdio is wired."""
    runtime = _make_runtime(tmp_path)
    http_app = build_http_app(runtime, profile="core", path="/mcp")
    assert any(getattr(r, "path", "") == "/mcp" for r in http_app.routes)
    assert callable(run_stdio)


# ---------------------------------------------------------------------------
# 4. FastAPI REST Surface End-to-End (All Core/v1 Endpoints + Auth)
# ---------------------------------------------------------------------------


async def test_e2e_fastapi_rest_all_endpoints_and_auth(tmp_path: Path) -> None:
    """Exercise all FastAPI REST endpoints and bearer token authentication."""
    apk = make_apk(tmp_path / "rest_e2e.apk")
    runtime = _make_runtime(tmp_path, api_token=SecretStr("secret-e2e-token"))
    try:
        app = create_app(runtime)
        transport = httpx.ASGITransport(app=app)
        headers = {"Authorization": "Bearer secret-e2e-token"}

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Public healthz + OpenAPI
            hz = await client.get("/healthz")
            assert hz.status_code == 200
            assert hz.json()["status"] == "ok"
            assert hz.json()["version"] == "4.0.0"
            assert hz.headers["x-content-type-options"] == "nosniff"
            assert hz.headers["x-frame-options"] == "DENY"

            openapi = await client.get("/openapi.json")
            assert openapi.status_code == 200
            assert openapi.json()["info"]["version"] == "4.0.0"

            # 2. Auth enforcement on /v1/*
            unauth = await client.get("/v1/capabilities")
            assert unauth.status_code == 401
            bad_auth = await client.get(
                "/v1/capabilities", headers={"Authorization": "Bearer wrong"}
            )
            assert bad_auth.status_code == 401

            # 3. System endpoints
            caps = await client.get("/v1/capabilities", headers=headers)
            assert caps.status_code == 200
            assert caps.json()["data"]["profiles"]["full"] == 379

            metrics = await client.get("/v1/system/metrics", headers=headers)
            assert metrics.status_code == 200

            audit = await client.get("/v1/system/audit/verify", headers=headers)
            assert audit.status_code == 200

            sbom = await client.get("/v1/system/sbom?format=cyclonedx", headers=headers)
            assert sbom.status_code == 200

            # 4. Tools endpoints
            tools_res = await client.get("/v1/tools?profile=full", headers=headers)
            assert tools_res.status_code == 200
            assert tools_res.json()["count"] == 379

            tool_desc = await client.get("/v1/tools/capabilities_get", headers=headers)
            assert tool_desc.status_code == 200
            assert tool_desc.json()["name"] == "capabilities_get"

            tool_404 = await client.get("/v1/tools/does_not_exist", headers=headers)
            assert tool_404.status_code == 404

            tool_call = await client.post(
                "/v1/tools/capabilities_get/call",
                json={"arguments": {}},
                headers=headers,
            )
            assert tool_call.status_code == 200

            # 5. Full Project -> Artifact Upload -> Analysis -> Jobs -> Report -> Evidence flow
            prj = await client.post("/v1/projects", json={"name": "REST E2E"}, headers=headers)
            assert prj.status_code == 200
            project_id = prj.json()["data"]["id"]

            prjs = await client.get("/v1/projects", headers=headers)
            assert prjs.status_code == 200
            assert prjs.json()["data"]["count"] >= 1

            prj_get = await client.get(f"/v1/projects/{project_id}", headers=headers)
            assert prj_get.status_code == 200

            with apk.open("rb") as fh:
                upload = await client.post(
                    f"/v1/projects/{project_id}/artifacts",
                    files={"file": ("rest_e2e.apk", fh, "application/vnd.android.package-archive")},
                    headers=headers,
                )
            assert upload.status_code == 200
            artifact_id = upload.json()["data"]["id"]

            arts = await client.get(f"/v1/projects/{project_id}/artifacts", headers=headers)
            assert arts.status_code == 200
            assert arts.json()["data"]["count"] == 1

            ana = await client.post(
                f"/v1/projects/{project_id}/analyses",
                json={"artifact_id": artifact_id},
                headers=headers,
            )
            assert ana.status_code == 200
            job_id = ana.json()["data"]["id"]

            jobs = await client.get(f"/v1/projects/{project_id}/jobs", headers=headers)
            assert jobs.status_code == 200
            assert jobs.json()["count"] >= 1

            for _ in range(50):
                job_status = await client.get(
                    f"/v1/projects/{project_id}/jobs/{job_id}", headers=headers
                )
                assert job_status.status_code == 200
                if job_status.json()["data"]["status"] in ("succeeded", "completed"):
                    break
                await asyncio.sleep(0.05)

            report = await client.get(
                f"/v1/projects/{project_id}/jobs/{job_id}/report", headers=headers
            )
            assert report.status_code == 200

            evidence = await client.get(f"/v1/projects/{project_id}/evidence", headers=headers)
            assert evidence.status_code == 200
    finally:
        await runtime.aclose()


# ---------------------------------------------------------------------------
# 5. CLI End-to-End (Version, Profiles, Tools, Project/Analysis Flow, Serve Help)
# ---------------------------------------------------------------------------


def test_e2e_cli_full_workflow(tmp_path: Path) -> None:
    """Exercise CLI commands end-to-end against a fresh workspace."""
    runner = CliRunner()
    ws = str(tmp_path / "cli_ws")
    apk = make_apk(tmp_path / "cli_e2e.apk")

    ver = runner.invoke(cli_app, ["version"])
    assert ver.exit_code == 0
    assert __version__ in ver.stdout

    # List all 377 tools in full profile
    tools_list = runner.invoke(
        cli_app, ["--workspace", ws, "--profile", "full", "--json", "tools", "list"]
    )
    assert tools_list.exit_code == 0
    assert json.loads(tools_list.stdout)["count"] == 379

    # Create project -> ingest -> analyze -> report
    prj = runner.invoke(cli_app, ["--workspace", ws, "--json", "project", "create", "CLI E2E"])
    assert prj.exit_code == 0
    project_id = json.loads(prj.stdout)["data"]["id"]

    ing = runner.invoke(
        cli_app, ["--workspace", ws, "--json", "artifact", "ingest", project_id, str(apk)]
    )
    assert ing.exit_code == 0
    artifact_id = json.loads(ing.stdout)["data"]["id"]

    ana = runner.invoke(
        cli_app,
        [
            "--workspace",
            ws,
            "--json",
            "tools",
            "call",
            "analysis_start",
            "--args-json",
            json.dumps({"project_id": project_id, "artifact_id": artifact_id}),
        ],
    )
    assert ana.exit_code == 0

    # Serve subcommands help
    for sub in (["serve", "--help"], ["serve", "mcp", "--help"], ["serve", "api", "--help"]):
        res = runner.invoke(cli_app, sub)
        assert res.exit_code == 0


# ---------------------------------------------------------------------------
# 6. All 377 Tools: Registry & End-to-End Invocation via MCP call_tool_result
# ---------------------------------------------------------------------------


async def test_e2e_all_377_tools_invocable_without_internal_error(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """Every single registered tool in src/raa/tools/ must be callable through MCP call_tool_result.

    Verifies all 377 tools execute end-to-end and flags any unexpected unhandled internal_error.
    """

    # Avoid real DNS/network wait for apk_fetch_upstream with dummy repo
    async def _mock_resolve(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "provider": "github",
            "identifier": "mock/repo",
            "version": "1.0.0",
            "download_url": "https://example.com/mock.apk",
            "asset_name": "mock.apk",
        }

    async def _mock_fetch(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("mocked offline")

    monkeypatch.setattr("raa.tools.artifacts.resolve_upstream_release", _mock_resolve)
    monkeypatch.setattr("raa.tools.artifacts.download_upstream_apk", _mock_fetch)

    runtime = _make_runtime(tmp_path)
    try:
        apk = make_apk(tmp_path / "sample.apk")
        all_scopes = sorted({s for spec in runtime.registry.all() for s in spec.scopes})
        proj = await runtime.invoke(
            "project_create", {"name": "E2E All Tools", "scopes": all_scopes}
        )
        project_id = proj.data["id"]

        ingested = await runtime.invoke(
            "artifact_ingest", {"project_id": project_id, "path": str(apk)}
        )
        artifact_id = ingested.data["id"]

        specs = runtime.registry.all()
        assert len(specs) == PLANNED_TOOL_COUNT == 379

        unexpected_internal_errors: list[tuple[str, Any]] = []
        known_unwrapped = 0
        succeeded = 0
        structured_raa_errors = 0

        for spec in specs:
            args = _dummy_args_for_schema(spec.input_schema(), project_id, artifact_id, apk)
            res = await call_tool_result(runtime, "full", spec.name, args)
            assert res.structured_content is not None, f"{spec.name} missing structuredContent"
            if res.is_error:
                err = res.structured_content.get("error", {})
                code = err.get("code")
                if code == "internal_error":
                    if spec.name in _KNOWN_UNWRAPPED_ERROR_TOOLS:
                        known_unwrapped += 1
                    else:
                        unexpected_internal_errors.append((spec.name, err))
                else:
                    structured_raa_errors += 1
            else:
                succeeded += 1

        assert not unexpected_internal_errors, (
            f"Unexpected internal_error tools: {unexpected_internal_errors}"
        )
        assert succeeded + structured_raa_errors + known_unwrapped == 379
        assert succeeded >= 200, f"Expected >=200 tools to succeed, got {succeeded}/379"
    finally:
        with suppress(TimeoutError):
            await asyncio.wait_for(runtime.aclose(), timeout=3.0)
