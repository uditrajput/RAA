"""REST/OpenAPI surface tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from raa.api.app import create_app
from raa.config import Settings
from raa.runtime import Runtime
from raa.version import __version__


@pytest.fixture
async def client(runtime: Runtime) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(runtime)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


async def test_openapi_is_generated(client: httpx.AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"].startswith("RAA")
    assert "/v1/tools/{tool_name}/call" in schema["paths"]


async def test_capabilities_and_tools(client: httpx.AsyncClient) -> None:
    capabilities = await client.get("/v1/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()["data"]["implemented_tools"] >= 244

    tools = await client.get("/v1/tools")
    assert tools.status_code == 200
    body = tools.json()
    assert body["count"] >= 135
    assert body["profile"] == "core"

    minimal = await client.get("/v1/tools", params={"profile": "minimal"})
    assert minimal.json()["count"] == 12

    tool = await client.get("/v1/tools/artifact_ingest")
    assert tool.status_code == 200
    assert tool.json()["input_schema"]["type"] == "object"

    not_found = await client.get("/v1/tools/nope")
    assert not_found.status_code == 404
    bad_req = await client.get("/v1/tools", params={"profile": "turbo"})
    assert bad_req.status_code == 400


async def test_project_flow(client: httpx.AsyncClient) -> None:
    created = await client.post(
        "/v1/projects",
        json={"name": "REST project", "description": "demo"},
    )
    assert created.status_code == 200
    project = created.json()["data"]
    project_id = project["id"]

    fetched = await client.get(f"/v1/projects/{project_id}")
    assert fetched.status_code == 200

    listed = await client.get("/v1/projects")
    assert listed.status_code == 200
    assert listed.json()["data"]["count"] == 1

    missing = await client.get("/v1/projects/prj_missing")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "not_found"


async def test_upload_and_start_analysis(client: httpx.AsyncClient, apk_path: Path) -> None:
    created_res = await client.post("/v1/projects", json={"name": "Upload"})
    project_id = created_res.json()["data"]["id"]

    uploaded = await client.post(
        f"/v1/projects/{project_id}/artifacts",
        files={
            "file": (
                "sample.apk",
                apk_path.read_bytes(),
                "application/vnd.android.package-archive",
            )
        },
    )
    assert uploaded.status_code == 200
    artifact = uploaded.json()["data"]
    assert artifact["artifact_type"] == "apk"

    artifacts = await client.get(f"/v1/projects/{project_id}/artifacts")
    assert artifacts.json()["data"]["count"] == 1

    started = await client.post(
        f"/v1/projects/{project_id}/analyses",
        json={"artifact_id": artifact["id"]},
    )
    assert started.status_code == 200
    job = started.json()["data"]
    assert job["status"] in {"queued", "running"}

    fetched = await client.get(f"/v1/projects/{project_id}/jobs/{job['id']}")
    assert fetched.status_code == 200

    jobs = await client.get(f"/v1/projects/{project_id}/jobs")
    assert jobs.status_code == 200
    assert jobs.json()["count"] == 1


async def test_tool_call(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/v1/tools/project_create/call",
        json={"arguments": {"name": "Called through REST"}},
    )
    assert response.status_code == 200
    assert response.json()["surface"] == "rest"

    denied = await client.post(
        "/v1/tools/admin_engine_list/call",
        json={"arguments": {}},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "profile_denied"


async def test_api_authentication(tmp_path: Path) -> None:
    settings = Settings(
        workspace=tmp_path / "workspace",
        api_token="super-secret-" + "token",
        allowed_input_roots=[tmp_path],
    )
    runtime = Runtime(settings)
    app = create_app(runtime)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await client.get("/healthz")
        assert health.status_code == 200
        unauth = await client.get("/v1/capabilities")
        assert unauth.status_code == 401

        authorized = await client.get(
            "/v1/capabilities",
            headers={"Authorization": "Bearer " + "super-secret-" + "token"},
        )
        assert authorized.status_code == 200

        wrong = await client.get(
            "/v1/capabilities",
            headers={"Authorization": "Bearer wrong"},
        )
        assert wrong.status_code == 401

        setup_unauth = await client.get("/api/setup/status")
        assert setup_unauth.status_code == 401
        setup_auth = await client.get(
            "/api/setup/status",
            headers={"Authorization": "Bearer " + "super-secret-" + "token"},
        )
        assert setup_auth.status_code == 200
