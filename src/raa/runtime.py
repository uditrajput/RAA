"""Runtime composition root.

Surfaces never construct services themselves. They call ``Runtime.invoke`` so
profiles, schema validation, scopes, evidence and audit behave identically for
MCP, REST, CLI and Python callers.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ValidationError

from raa.config import ProfileName, Settings
from raa.domain.models import Project
from raa.errors import (
    InternalError,
    InvalidArgumentsError,
    NotFoundError,
    PolicyDeniedError,
    ProfileDeniedError,
    RAAError,
)
from raa.policy.scopes import ALL_SCOPES, DEFAULT_PROJECT_SCOPES, PolicyEngine
from raa.registry.models import (
    ToolContext,
    ToolEnvelope,
    ToolSpec,
)
from raa.registry.profiles import ALL_PROFILES
from raa.services.aair import AAIRService
from raa.services.advanced_binary import AdvancedBinaryService
from raa.services.agents.coverage_tracker import CoverageTracker
from raa.services.analysis import AnalysisService
from raa.services.api_service import ApiService
from raa.services.artifacts import ArtifactService
from raa.services.audit import AuditService
from raa.services.backup import BackupService
from raa.services.cadence import CadenceService
from raa.services.channels.gateway import ChannelGatewayService
from raa.services.cognitive import CognitiveAuditService
from raa.services.debloat import AndroidDebloatService
from raa.services.diff_service import DiffService
from raa.services.dynamic import DynamicService
from raa.services.engine_runner import EngineRunner
from raa.services.engines import EngineService
from raa.services.enterprise import EnterpriseIntegrationService
from raa.services.evidence import EvidenceService
from raa.services.mcp_mesh import McpMeshService
from raa.services.metrics import MetricsService
from raa.services.offensive import OffensiveSecurityService
from raa.services.playstore import PlayStoreService
from raa.services.projects import ProjectService
from raa.services.rebuild_service import RebuildService
from raa.services.recipes import RecipeService
from raa.services.sbom import SbomService
from raa.services.security_service import SecurityService
from raa.services.self_evolution import SelfEvolutionService
from raa.services.signing import SigningService
from raa.services.skills import SkillService
from raa.services.swarm import SwarmService
from raa.services.tenancy import TenancyService
from raa.services.tool_manager import ToolManagerService
from raa.services.tv_studio import TvStudioService
from raa.services.ui import UIService
from raa.services.ui_reconstruction import UIReconstructionService
from raa.services.unpacking_service import UnpackingService
from raa.services.vault import VaultShieldService
from raa.services.wireless_gateway import WirelessGatewayService
from raa.services.workspace import Workspace
from raa.storage.database import Database
from raa.storage.repositories import (
    ArtifactRepository,
    EvidenceRepository,
    JobRepository,
    ProjectRepository,
)
from raa.tools import build_registry
from raa.utils.ids import new_request_id
from raa.version import PLANNED_TOOL_COUNT, PROTOCOL_VERSION, __version__

logger = logging.getLogger(__name__)


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.workspace = Workspace(settings.resolved_workspace())
        self.workspace.ensure()

        self.database = Database(settings.database_path)
        self.database.initialize()

        project_repository = ProjectRepository(self.database)
        artifact_repository = ArtifactRepository(self.database)
        evidence_repository = EvidenceRepository(self.database)
        job_repository = JobRepository(self.database)

        self.projects = ProjectService(project_repository)
        self.evidence = EvidenceService(evidence_repository)
        self.artifacts = ArtifactService(
            settings=settings,
            workspace=self.workspace,
            repository=artifact_repository,
            projects=self.projects,
            evidence=self.evidence,
        )
        self.playstore = PlayStoreService(
            settings=settings,
            workspace=self.workspace,
            artifacts=self.artifacts,
            evidence=self.evidence,
        )
        self.analysis = AnalysisService(
            settings=settings,
            workspace=self.workspace,
            projects=self.projects,
            artifacts=self.artifacts,
            evidence=self.evidence,
            jobs=job_repository,
        )
        self.engines = EngineService(settings)
        self.engine_runner = EngineRunner(settings, self.workspace)
        self.recipes = RecipeService()
        self.skills = SkillService()
        self.ui = UIService(self.workspace)
        self.aair = AAIRService(
            workspace=self.workspace,
            evidence=self.evidence,
            artifacts=self.artifacts,
            analysis=self.analysis,
        )
        self.dynamic = DynamicService(
            workspace=self.workspace,
            evidence=self.evidence,
            artifacts=self.artifacts,
        )
        self.api = ApiService(
            workspace=self.workspace,
            evidence=self.evidence,
            artifacts=self.artifacts,
        )
        self.unpacking = UnpackingService(
            workspace=self.workspace,
            artifacts=self.artifacts,
            evidence=self.evidence,
            engine_runner=self.engine_runner,
        )
        self.diff = DiffService(
            workspace=self.workspace,
            artifacts=self.artifacts,
            evidence=self.evidence,
        )
        self.security = SecurityService(
            workspace=self.workspace,
            artifacts=self.artifacts,
            evidence=self.evidence,
        )
        self.rebuild = RebuildService(
            workspace=self.workspace,
            artifacts=self.artifacts,
            evidence=self.evidence,
            dynamic=self.dynamic,
        )
        self.coverage = CoverageTracker(
            workspace=self.workspace,
            evidence=self.evidence,
            artifacts=self.artifacts,
            projects=self.projects,
        )
        self.audit = AuditService(self.workspace.audit_dir)
        self.signing = SigningService()
        self.sbom = SbomService(self.engines)
        self.backup = BackupService(
            workspace=self.workspace,
            database=self.database,
            projects=self.projects,
            artifacts=self.artifacts,
        )
        self.tenancy = TenancyService()
        self.swarm = SwarmService(self.workspace.root)
        self.cognitive = CognitiveAuditService(self.workspace.root)
        self.advanced_binary = AdvancedBinaryService(self.workspace.root)
        self.ui_reconstruction = UIReconstructionService(self.workspace.root)
        self.enterprise = EnterpriseIntegrationService(self.workspace.root)
        self.offensive = OffensiveSecurityService(self.workspace.root)
        self.tool_manager = ToolManagerService(
            workspace_root=self.workspace.root,
            managed_dir=settings.tools_managed_dir,
        )
        self.vault = VaultShieldService(self.workspace.root)
        self.channels = ChannelGatewayService(
            workspace_root=self.workspace.root,
            telegram_token=settings.telegram_bot_token.get_secret_value()
            if settings.telegram_bot_token
            else None,
            telegram_allowed=settings.telegram_allowed_users,
            whatsapp_phone=settings.whatsapp_phone,
            whatsapp_token=settings.whatsapp_api_token.get_secret_value()
            if settings.whatsapp_api_token
            else None,
            whatsapp_mode=settings.whatsapp_mode,
            vault=self.vault,
        )
        self.cadence = CadenceService(
            default_mode=settings.cadence_mode,
            default_interval_minutes=settings.cadence_interval_minutes,
            urgent_cve_breakin=settings.cadence_urgent_cve_breakin,
        )
        self.self_evolution = SelfEvolutionService(self.workspace.root)
        self.mcp_mesh = McpMeshService(
            workspace_root=self.workspace.root,
            store_file=settings.mcp_mesh_store,
            vault=self.vault,
        )
        self.wireless_gateway = WirelessGatewayService(
            workspace_root=self.workspace.root,
            default_host=settings.wireless_device_host,
        )
        self.tv_studio = TvStudioService(self.workspace.root)
        self.debloat = AndroidDebloatService(self.workspace.root)
        self.metrics = MetricsService(
            workspace=self.workspace,
            database=self.database,
            engines=self.engines,
            audit=self.audit,
        )
        self.policy = PolicyEngine()
        self.registry = build_registry()

    def info(self) -> dict[str, Any]:
        return {
            "name": self.settings.app_name,
            "version": __version__,
            "protocol": PROTOCOL_VERSION,
            "implemented_tools": self.registry.count(),
            "planned_tools": PLANNED_TOOL_COUNT,
            "profiles": {
                profile: len(self.registry.for_profile(profile)) for profile in ALL_PROFILES
            },
            "surfaces": ["mcp", "rest", "cli", "python"],
            "skills": self._skill_summary(),
            "extensions": {
                "tasks": "planned",
                "skills": "active",
                "mcp_apps": "planned",
            },
            "scopes": sorted(ALL_SCOPES),
            "default_project_scopes": list(DEFAULT_PROJECT_SCOPES),
            "admin_enabled": self.settings.admin_enabled,
            "allowed_input_roots": [str(p) for p in self.settings.allowed_input_roots],
            "engines": self.engines.summary(),
            "workspace": str(self.workspace.root),
        }

    def _skill_summary(self) -> dict[str, object]:
        """Report skills without letting a bad local skill break capabilities."""

        try:
            return {"count": len(self.skills.discover()), "error": None}
        except RAAError as exc:
            return {"count": 0, "error": exc.message}

    async def invoke(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        profile: ProfileName | str | None = None,
        surface: str = "python",
    ) -> ToolEnvelope:
        started = time.perf_counter()
        request_id = new_request_id()
        arguments = arguments or {}
        selected_profile = profile or self.settings.profile
        if selected_profile not in ALL_PROFILES:
            raise InvalidArgumentsError(
                f"Unknown profile: {selected_profile}",
                hint="Valid profiles are: " + ", ".join(ALL_PROFILES),
            )
        resolved_profile: ProfileName = selected_profile

        project_id = arguments.get("project_id")
        project: Project | None = None
        try:
            spec = self._spec_or_raise(name)
            self._check_profile(spec, resolved_profile)
            parsed = self._validate_arguments(spec, arguments)

            argument_project_id = getattr(parsed, "project_id", None)
            if isinstance(argument_project_id, str) and argument_project_id:
                project = self.projects.get_or_raise(argument_project_id)
                project_id = project.id

            decision = self.policy.evaluate(
                spec.scopes,
                self._granted_scopes(project),
            )
            if not decision.allowed:
                raise PolicyDeniedError(
                    f"Tool '{spec.name}' is not allowed by the project policy.",
                    hint=decision.reason,
                    details={
                        "tool": spec.name,
                        "project_id": project.id if project else None,
                        "missing_scopes": sorted(decision.missing),
                    },
                )

            context = ToolContext(
                runtime=self,
                profile=resolved_profile,
                surface=surface,
                request_id=request_id,
                project=project,
            )
            outcome = await spec.handler(context, parsed)
            envelope = ToolEnvelope(
                tool=spec.name,
                version=spec.version,
                request_id=request_id,
                surface=surface,
                profile=resolved_profile,
                data=_serialize(outcome.data),
                evidence_ids=outcome.evidence_ids,
                warnings=outcome.warnings,
                meta={
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "implemented_tools": self.registry.count(),
                    "required_scopes": sorted(spec.scopes),
                },
            )
            self._audit(
                spec=spec,
                arguments=arguments,
                project_id=project.id if project else None,
                context=context,
                outcome="ok",
                duration_ms=(time.perf_counter() - started) * 1000,
            )
            return envelope
        except RAAError as exc:
            self._audit_error(
                name=name,
                arguments=arguments,
                project_id=project.id if project else project_id,
                profile=resolved_profile,
                surface=surface,
                request_id=request_id,
                started=started,
                error_code=exc.code,
            )
            raise
        except Exception as exc:
            self._audit_error(
                name=name,
                arguments=arguments,
                project_id=project.id if project else project_id,
                profile=resolved_profile,
                surface=surface,
                request_id=request_id,
                started=started,
                error_code="internal_error",
            )
            sanitized_tool = name.replace("\r", "_").replace("\n", "_")
            logger.exception("Unhandled tool failure for %s", sanitized_tool)
            raise InternalError(
                "The tool failed unexpectedly.",
                hint="Check the server log with the request id.",
                details={"tool": sanitized_tool, "request_id": request_id},
            ) from exc

    def _spec_or_raise(self, name: str) -> ToolSpec:
        # Strip common external caller / client prefixes such as 'raa.' or 'tools.raa.'
        normalized_name = name
        for prefix in ("tools.raa.", "tools.", "raa.", "raa:"):
            if normalized_name.startswith(prefix):
                normalized_name = normalized_name[len(prefix) :]
                break

        if not self.registry.has(normalized_name):
            raise NotFoundError(
                f"Unknown tool: {name}",
                hint="Call tools/list or capabilities_get to discover tool names.",
                details={"tool": name},
            )
        return self.registry.get(normalized_name)

    @staticmethod
    def _check_profile(spec: ToolSpec, profile: ProfileName) -> None:
        if profile == "full":
            return
        if profile not in spec.profiles:
            raise ProfileDeniedError(
                f"Tool '{spec.name}' is not exposed by profile '{profile}'.",
                hint="Switch to the 'core' or 'full' profile, or use the matching profile.",
                details={
                    "tool": spec.name,
                    "profile": profile,
                    "available_in": sorted(spec.profiles),
                },
            )

    @staticmethod
    def _validate_arguments(spec: ToolSpec, arguments: dict[str, Any]) -> BaseModel:
        try:
            return spec.input_model.model_validate(arguments)
        except ValidationError as exc:
            errors = [
                {key: value for key, value in error.items() if key in {"type", "loc", "msg"}}
                for error in exc.errors()
            ]
            raise InvalidArgumentsError(
                f"Invalid arguments for '{spec.name}'.",
                hint="Inspect the tool input schema before retrying.",
                details={"errors": errors},
            ) from exc

    def _granted_scopes(self, project: Project | None) -> set[str]:
        if project is not None:
            return set(project.scopes)
        return {"admin"} if self.settings.admin_enabled else set()

    def _audit(
        self,
        *,
        spec: ToolSpec,
        arguments: dict[str, Any],
        project_id: str | None,
        context: ToolContext,
        outcome: str,
        duration_ms: float,
    ) -> None:
        self.audit.record(
            tool=spec.name,
            surface=context.surface,
            profile=context.profile,
            request_id=context.request_id,
            project_id=project_id,
            arguments=arguments,
            outcome=outcome,
            duration_ms=duration_ms,
        )

    def _audit_error(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        project_id: str | None,
        profile: ProfileName,
        surface: str,
        request_id: str,
        started: float,
        error_code: str,
    ) -> None:
        self.audit.record(
            tool=name,
            surface=surface,
            profile=profile,
            request_id=request_id,
            project_id=project_id,
            arguments=arguments,
            outcome="error",
            duration_ms=(time.perf_counter() - started) * 1000,
            error_code=error_code,
        )

    async def aclose(self) -> None:
        self.analysis.shutdown()


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
