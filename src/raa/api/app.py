"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from starlette.status import HTTP_401_UNAUTHORIZED

from raa.api.setup_ui import router as setup_ui_router
from raa.config import ProfileName, Settings
from raa.errors import LimitExceededError, RAAError
from raa.registry.profiles import ALL_PROFILES
from raa.runtime import Runtime
from raa.services.workspace import sanitize_filename
from raa.version import __version__

logger = logging.getLogger(__name__)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolCallBody(ApiModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


class ProjectCreateBody(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    scopes: list[str] | None = None


class AnalysisStartBody(ApiModel):
    artifact_id: str
    stages: list[str] | None = None


def create_app(runtime: Runtime | None = None) -> FastAPI:
    active_runtime = runtime or Runtime(Settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        del app

        async def _auto_poll_channels() -> None:
            while True:
                try:
                    await asyncio.sleep(0.5)
                    ch = active_runtime.channels
                    tg_ready = ch.telegram.is_configured()
                    wa_ready = bool(ch.whatsapp.paired or ch.whatsapp.is_configured())
                    if tg_ready or wa_ready:
                        await asyncio.to_thread(ch.poll_and_dispatch, "all", active_runtime)
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug("Channel auto-poll iteration failed: %s", exc)

        poll_task = (
            asyncio.create_task(_auto_poll_channels())
            if not os.environ.get("PYTEST_CURRENT_TEST")
            else None
        )
        try:
            yield
        finally:
            if poll_task is not None:
                poll_task.cancel()
                with suppress(asyncio.CancelledError):
                    await poll_task
            await active_runtime.aclose()

    app = FastAPI(
        title="RAA - Reverse Android Anything",
        description=(
            "REST surface generated from the RAA capability registry. "
            "Every tool is also available at POST /v1/tools/{tool_name}/call."
        ),
        version=__version__,
        openapi_url="/openapi.json",
        docs_url="/docs",
        lifespan=lifespan,
    )
    app.state.runtime = active_runtime

    # Security headers applied via ASGI middleware rather than BaseHTTPMiddleware
    # to avoid AnyIO task group deadlocks in Starlette/FastAPI test harnesses.
    from starlette.datastructures import MutableHeaders
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    class SecurityHeadersMiddleware:
        def __init__(self, app: ASGIApp) -> None:
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers["X-Content-Type-Options"] = "nosniff"
                    headers["X-Frame-Options"] = "DENY"
                    headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                    headers["X-XSS-Protection"] = "1; mode=block"
                await send(message)

            await self.app(scope, receive, send_wrapper)

    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(setup_ui_router, dependencies=[Depends(authorize)])

    @app.get("/healthz", tags=["system"])
    async def healthz() -> dict[str, Any]:
        return {
            "status": "ok" if active_runtime.database.ping() else "degraded",
            "name": "raa",
            "version": __version__,
        }

    @app.get("/v1/capabilities", tags=["system"], dependencies=[Depends(authorize)])
    async def capabilities() -> dict[str, Any]:
        return await _invoke(active_runtime, "capabilities_get", {})

    @app.get("/v1/system/metrics", tags=["system"], dependencies=[Depends(authorize)])
    async def system_metrics() -> dict[str, Any]:
        return await _invoke(active_runtime, "admin_system_metrics", {})

    @app.get("/v1/system/audit/verify", tags=["system"], dependencies=[Depends(authorize)])
    async def audit_verify() -> dict[str, Any]:
        return await _invoke(active_runtime, "admin_audit_verify", {})

    @app.get("/v1/system/sbom", tags=["system"], dependencies=[Depends(authorize)])
    async def sbom_generate(format: str = "cyclonedx") -> dict[str, Any]:
        return await _invoke(active_runtime, "admin_sbom_generate", {"format": format})

    @app.get("/v1/tools", tags=["tools"], dependencies=[Depends(authorize)])
    async def list_tools(profile: str | None = None) -> dict[str, Any]:
        selected = _profile(profile or active_runtime.settings.profile)
        specs = active_runtime.registry.for_profile(selected)
        return {
            "profile": selected,
            "items": [
                {
                    "name": spec.name,
                    "title": spec.title,
                    "description": spec.description,
                    "family": spec.family,
                    "scopes": sorted(spec.scopes),
                    "profiles": sorted(spec.profiles),
                    "cost": spec.cost,
                    "read_only": spec.annotations.read_only,
                    "destructive": spec.annotations.destructive,
                }
                for spec in specs
            ],
            "count": len(specs),
        }

    @app.get("/v1/tools/{tool_name}", tags=["tools"], dependencies=[Depends(authorize)])
    async def describe_tool(tool_name: str) -> dict[str, Any]:
        if not active_runtime.registry.has(tool_name):
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
        spec = active_runtime.registry.get(tool_name)
        return {
            "name": spec.name,
            "title": spec.title,
            "description": spec.description,
            "family": spec.family,
            "scopes": sorted(spec.scopes),
            "profiles": sorted(spec.profiles),
            "input_schema": spec.input_schema(),
        }

    @app.post(
        "/v1/tools/{tool_name}/call",
        tags=["tools"],
        dependencies=[Depends(authorize)],
    )
    async def call_tool(tool_name: str, body: ToolCallBody) -> dict[str, Any]:
        return await _invoke(active_runtime, tool_name, body.arguments)

    @app.post("/v1/projects", tags=["projects"], dependencies=[Depends(authorize)])
    async def create_project(body: ProjectCreateBody) -> dict[str, Any]:
        active_runtime.tenancy.enforce_project_creation("default", active_runtime.projects.count())
        payload = body.model_dump()
        return await _invoke(active_runtime, "project_create", payload)

    @app.get("/v1/projects", tags=["projects"], dependencies=[Depends(authorize)])
    async def list_projects(limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return await _invoke(
            active_runtime,
            "project_list",
            {"limit": limit, "offset": offset},
        )

    @app.get(
        "/v1/projects/{project_id}",
        tags=["projects"],
        dependencies=[Depends(authorize)],
    )
    async def get_project(project_id: str) -> dict[str, Any]:
        return await _invoke(active_runtime, "project_get", {"project_id": project_id})

    @app.get(
        "/v1/projects/{project_id}/artifacts",
        tags=["artifacts"],
        dependencies=[Depends(authorize)],
    )
    async def list_artifacts(
        project_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await _invoke(
            active_runtime,
            "artifact_list",
            {"project_id": project_id, "limit": limit, "offset": offset},
        )

    @app.post(
        "/v1/projects/{project_id}/artifacts",
        tags=["artifacts"],
        dependencies=[Depends(authorize)],
    )
    async def upload_artifact(
        project_id: str,
        file: UploadFile = File(...),
    ) -> dict[str, Any]:
        original_name = file.filename or "upload.bin"
        upload_dir = active_runtime.workspace.tmp_dir / uuid.uuid4().hex
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / sanitize_filename(original_name)
        total = 0
        try:
            with target.open("wb") as writer:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > active_runtime.settings.max_input_bytes:
                        raise LimitExceededError(
                            "Upload exceeds the configured input limit.",
                            details={"max_input_bytes": active_runtime.settings.max_input_bytes},
                        )
                    writer.write(chunk)
            return await _invoke(
                active_runtime,
                "artifact_ingest",
                {"project_id": project_id, "path": str(target)},
            )
        finally:
            target.unlink(missing_ok=True)
            with suppress(OSError):
                upload_dir.rmdir()

    @app.post(
        "/v1/projects/{project_id}/analyses",
        tags=["analysis"],
        dependencies=[Depends(authorize)],
    )
    async def start_analysis(
        project_id: str,
        body: AnalysisStartBody,
    ) -> dict[str, Any]:
        return await _invoke(
            active_runtime,
            "analysis_start",
            {
                "project_id": project_id,
                "artifact_id": body.artifact_id,
                "stages": body.stages,
            },
        )

    @app.get(
        "/v1/projects/{project_id}/jobs",
        tags=["analysis"],
        dependencies=[Depends(authorize)],
    )
    async def list_jobs(project_id: str, limit: int = 50) -> dict[str, Any]:
        await _invoke(active_runtime, "project_get", {"project_id": project_id})
        jobs = active_runtime.analysis.jobs.list(project_id, limit=limit)
        return {
            "items": [job.model_dump(mode="json") for job in jobs],
            "count": len(jobs),
        }

    @app.get(
        "/v1/projects/{project_id}/jobs/{job_id}",
        tags=["analysis"],
        dependencies=[Depends(authorize)],
    )
    async def get_job(project_id: str, job_id: str) -> dict[str, Any]:
        return await _invoke(
            active_runtime,
            "analysis_get_status",
            {"project_id": project_id, "job_id": job_id},
        )

    @app.get(
        "/v1/projects/{project_id}/jobs/{job_id}/report",
        tags=["analysis"],
        dependencies=[Depends(authorize)],
    )
    async def get_report(project_id: str, job_id: str) -> dict[str, Any]:
        return await _invoke(
            active_runtime,
            "analysis_get_report",
            {"project_id": project_id, "job_id": job_id},
        )

    @app.get(
        "/v1/projects/{project_id}/evidence",
        tags=["evidence"],
        dependencies=[Depends(authorize)],
    )
    async def list_evidence(
        project_id: str,
        artifact_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await _invoke(
            active_runtime,
            "evidence_list",
            {
                "project_id": project_id,
                "artifact_id": artifact_id,
                "limit": limit,
                "offset": offset,
            },
        )

    return app


async def authorize(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    token = getattr(request.app.state.runtime.settings, "api_token", None)
    if token is None:
        return
    expected = token.get_secret_value()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    provided = authorization[7:].strip()
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _profile(value: str) -> ProfileName:
    if value not in ALL_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown profile: {value}. Valid profiles: {', '.join(ALL_PROFILES)}",
        )
    return value


async def _invoke(
    runtime: Runtime,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    try:
        envelope = await runtime.invoke(
            tool_name,
            arguments,
            surface="rest",
        )
        return envelope.model_dump(mode="json")
    except RAAError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.to_dict()) from exc
