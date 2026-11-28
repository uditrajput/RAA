"""API Reverse-Engineering Studio MCP tools for flows, clustering, contracts, and drift."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from raa.domain.api import OpenAPISpec
from raa.policy.scopes import EXPORT_RAW, EXPORT_WRITE, NETWORK_CAPTURE, NETWORK_CRAWL, PROJECT_READ
from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import API
from raa.services.api.endpoint_crawler import (
    audit_privacy_policy,
    crawl_endpoint_documentation,
)
from raa.services.api.web_recon import crawl_backend_surface

# --- Input Models ---


class ApiCaptureStartInput(BaseModel):
    """Parameters to start an authorized API capture session."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    mode: str = Field(
        default="proxy",
        description="Capture mode: static-only, proxy, in-app, replay.",
    )
    target_hosts: list[str] | None = Field(
        default=None,
        description="Optional scope allowlist of target hostnames.",
    )


class ApiCaptureStopInput(BaseModel):
    """Parameters to stop an active API capture session."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    session_id: str = Field(min_length=1, description="Active capture session ID.")


class ApiCaptureStatusInput(BaseModel):
    """Parameters to query capture session status and flow metrics."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    session_id: str | None = Field(default=None, description="Optional specific session ID.")


class ApiListFlowsInput(BaseModel):
    """Parameters to query paginated, filtered network flow records."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    host: str | None = Field(default=None, description="Filter by hostname substring.")
    method: str | None = Field(default=None, description="Filter by HTTP method.")
    status: int | None = Field(default=None, description="Filter by HTTP status code.")
    limit: int = Field(default=50, ge=1, le=500, description="Page limit.")
    offset: int = Field(default=0, ge=0, description="Offset index.")


class ApiGetFlowInput(BaseModel):
    """Parameters to retrieve a single normalized flow record."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    flow_id: str = Field(min_length=1, description="Target flow record ID.")


class ApiClusterOperationsInput(BaseModel):
    """Parameters to cluster recorded flows into de-duplicated operations."""

    project_id: str = Field(min_length=1, description="Target project ID.")


class ApiListOperationsInput(BaseModel):
    """Parameters to list clustered operations catalogue."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    limit: int = Field(default=50, ge=1, le=500, description="Page limit.")
    offset: int = Field(default=0, ge=0, description="Offset index.")


class ApiGetOperationInput(BaseModel):
    """Parameters to retrieve a specific operation cluster."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    operation_id: str = Field(min_length=1, description="Operation ID.")


class ApiInferSchemasInput(BaseModel):
    """Parameters to infer request/response schemas from flow samples."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    operation_id: str | None = Field(default=None, description="Optional specific operation ID.")


class ApiGenerateSpecInput(BaseModel):
    """Parameters to generate an OpenAPI 3.1 specification."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    title: str = Field(default="Inferred App API", description="API title.")
    version: str = Field(default="1.0.0", description="API version.")


class ApiGenerateClientInput(BaseModel):
    """Parameters to generate and smoke-test an API client."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    language: str = Field(default="python", description="Target client language.")
    output_dir: str | None = Field(
        default=None, description="Optional directory to write client files."
    )


class ApiRunContractTestsInput(BaseModel):
    """Parameters to validate flows against the OpenAPI contract."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    operation_id: str | None = Field(default=None, description="Optional specific operation ID.")


class ApiDiffContractsInput(BaseModel):
    """Parameters to compare two OpenAPI specifications and detect drift."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    candidate_spec: dict[str, Any] = Field(
        description="Candidate OpenAPI specification dict to compare against baseline."
    )
    ignore_volatile: bool = Field(
        default=True,
        description="Ignore volatile fields (timestamps, nonces, signatures).",
    )


class ApiGetDriftInput(BaseModel):
    """Parameters to query recorded drift findings."""

    project_id: str = Field(min_length=1, description="Target project ID.")


class ApiExportHarInput(BaseModel):
    """Parameters to export redacted flows as a standard HAR 1.2 file."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    flow_ids: list[str] | None = Field(
        default=None, description="Optional specific flow IDs to include."
    )


class ApiSynthesizeSpecInput(BaseModel):
    """Parameters to synthesize OpenAPI 3.1 specification using api-anything route clustering."""

    project_id: str = Field(min_length=1, description="Target project identifier.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    min_occurrences: int = Field(
        default=1, ge=1, description="Minimum times an endpoint must be observed."
    )
    include_headers: bool = Field(default=False, description="Whether to include custom headers.")
    format: str = Field(default="json", description="Output format: json, yaml.")


class ApiExportPostmanInput(BaseModel):
    """Parameters to export synthesized endpoints to Postman Collection v2.1."""

    project_id: str = Field(min_length=1, description="Target project identifier.")
    collection_name: str | None = Field(default=None, description="Optional collection name.")
    base_url_variable: str = Field(default="baseUrl", description="Base URL variable name.")


class ApiExportHoppscotchInput(BaseModel):
    """Parameters to export synthesized endpoints to Hoppscotch v2 JSON collection."""

    project_id: str = Field(min_length=1, description="Target project identifier.")
    collection_name: str | None = Field(default=None, description="Optional collection name.")
    base_url: str = Field(default="<<baseUrl>>", description="Hoppscotch environment base URL.")


class CrawlEndpointDocsInput(BaseModel):
    """Parameters to autonomously extract REST API endpoints and schemas from documentation."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    base_url: str = Field(default="https://api.example.com", description="Target API base URL.")
    doc_content: str | None = Field(
        default=None, description="Raw HTML or Markdown developer documentation text."
    )
    doc_path: str | None = Field(
        default=None, description="Optional path to local API documentation file."
    )


class CrawlPrivacyPolicyAuditInput(BaseModel):
    """Parameters to cross-audit remote privacy policy claims against APK permissions."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    policy_text: str = Field(default="", description="Full text of the privacy policy.")
    policy_path: str | None = Field(
        default=None, description="Optional path to local privacy policy text or markdown file."
    )
    declared_permissions: list[str] = Field(
        default_factory=list, description="List of permissions requested by the application."
    )


class NetIpIntelInput(BaseModel):
    """Parameters to query backend IP intelligence and ASN data."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    ip_addresses: list[str] | str = Field(
        description="List or comma/space-separated string of IP addresses."
    )
    threat_threshold: float = Field(
        default=60.0, ge=0.0, le=100.0, description="Risk threshold to flag high risk IPs."
    )


class NetCtiReputationCheckInput(BaseModel):
    """Parameters to check endpoints/IPs against CTI threat intelligence feeds."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    targets: list[str] = Field(min_length=1, description="List of IP addresses or domain names.")
    threat_threshold: int = Field(
        default=40, ge=0, le=100, description="Reputation score threshold to flag as threat."
    )


class ApiSemanticWafAuditInput(BaseModel):
    """Parameters to execute AST semantic injection vulnerability audit on mobile API requests."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    endpoint_url: str = Field(min_length=1, description="Target mobile API endpoint URL.")
    http_method: str = Field(default="GET", description="HTTP method (GET, POST, PUT, DELETE).")
    query_params: dict[str, Any] | None = Field(
        default=None, description="Optional URL query parameters."
    )
    request_body: str | dict[str, Any] | None = Field(
        default=None, description="Optional request payload body (raw text or JSON object)."
    )
    headers: dict[str, str] | None = Field(
        default=None, description="Optional HTTP request headers."
    )


class ApiBypass403TestInput(BaseModel):
    """Parameters to generate 401/403 access control bypass mutations."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    target_url: str = Field(min_length=1, description="Target API endpoint returning 401/403.")
    http_method: str = Field(default="GET", description="HTTP method (GET, POST, etc.).")
    base_headers: dict[str, str] | None = Field(
        default=None, description="Optional base request headers."
    )


class ApiBackendReconInput(BaseModel):
    """Parameters to crawl extracted mobile backend URLs for endpoints, subdomains, and secrets."""

    project_id: str = Field(min_length=1, description="Target project ID with network.crawl scope.")
    base_urls: list[str] = Field(min_length=1, description="Seed HTTP/HTTPS URLs to crawl.")
    max_depth: int = Field(default=2, ge=0, le=5, description="Maximum link traversal depth.")
    max_pages: int = Field(default=25, ge=1, le=200, description="Maximum pages to fetch.")


class ApiRotatingProxySessionInput(BaseModel):
    """Parameters to create multi-region cloud gateway rotating proxy session."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    target_url: str = Field(min_length=1, description="Target base URL or API host.")
    regions: list[str] | None = Field(
        default=None, description="Cloud regions to distribute egress across."
    )
    provider: str = Field(default="aws_api_gateway", description="Cloud provider for egress proxy.")
    max_retries: int = Field(default=5, ge=1, le=20, description="Max retries per request.")
    backoff_factor: float = Field(default=1.5, ge=1.0, le=10.0, description="Backoff factor.")
    rotate_on_status: list[int] | None = Field(
        default=None, description="HTTP status codes triggering IP rotation."
    )


# --- Helper ---


def _api_spec(
    *,
    name: str,
    title: str,
    description: str,
    handler: Any,
    input_model: type[BaseModel],
    scopes: frozenset[str] = frozenset(),
    read_only: bool = True,
    idempotent: bool = True,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        title=title,
        description=description,
        input_model=input_model,
        handler=handler,
        family="api",
        profiles=API,
        scopes=scopes,
        annotations=ToolAnnotations(read_only=read_only, idempotent=idempotent),
        cost="fast",
    )


# --- Handlers ---


async def _api_capture_start(ctx: ToolContext, args: ApiCaptureStartInput) -> ToolOutcome:
    session = ctx.runtime.api.capture_start(
        project_id=args.project_id,
        mode=args.mode,
        target_hosts=args.target_hosts,
    )
    return ToolOutcome(data=session.model_dump(mode="json"))


async def _api_capture_stop(ctx: ToolContext, args: ApiCaptureStopInput) -> ToolOutcome:
    session = ctx.runtime.api.capture_stop(
        project_id=args.project_id,
        session_id=args.session_id,
    )
    return ToolOutcome(data=session.model_dump(mode="json"))


async def _api_capture_status(ctx: ToolContext, args: ApiCaptureStatusInput) -> ToolOutcome:
    res = ctx.runtime.api.capture_status(
        project_id=args.project_id,
        session_id=args.session_id,
    )
    return ToolOutcome(data=res)


async def _api_list_flows(ctx: ToolContext, args: ApiListFlowsInput) -> ToolOutcome:
    res = ctx.runtime.api.list_flows(
        project_id=args.project_id,
        host=args.host,
        method=args.method,
        status=args.status,
        limit=args.limit,
        offset=args.offset,
    )
    return ToolOutcome(data=res)


async def _api_get_flow(ctx: ToolContext, args: ApiGetFlowInput) -> ToolOutcome:
    flow = ctx.runtime.api.get_flow(
        project_id=args.project_id,
        flow_id=args.flow_id,
    )
    return ToolOutcome(data=flow.model_dump(mode="json"))


async def _api_cluster_operations(ctx: ToolContext, args: ApiClusterOperationsInput) -> ToolOutcome:
    clusters = ctx.runtime.api.cluster_operations(project_id=args.project_id)
    return ToolOutcome(
        data={
            "operations": [c.model_dump(mode="json") for c in clusters],
            "total": len(clusters),
            "total_clusters": len(clusters),
        }
    )


async def _api_list_operations(ctx: ToolContext, args: ApiListOperationsInput) -> ToolOutcome:
    res = ctx.runtime.api.list_operations(
        project_id=args.project_id,
        limit=args.limit,
        offset=args.offset,
    )
    return ToolOutcome(data=res)


async def _api_get_operation(ctx: ToolContext, args: ApiGetOperationInput) -> ToolOutcome:
    res = ctx.runtime.api.get_operation(
        project_id=args.project_id,
        operation_id=args.operation_id,
    )
    return ToolOutcome(data=res)


async def _api_infer_schemas(ctx: ToolContext, args: ApiInferSchemasInput) -> ToolOutcome:
    res = ctx.runtime.api.infer_schemas(
        project_id=args.project_id,
        operation_id=args.operation_id,
    )
    return ToolOutcome(data=res)


async def _api_generate_spec(ctx: ToolContext, args: ApiGenerateSpecInput) -> ToolOutcome:
    spec = ctx.runtime.api.generate_spec(
        project_id=args.project_id,
        title=args.title,
        version=args.version,
    )
    return ToolOutcome(data=spec.model_dump(mode="json"))


async def _api_generate_client(ctx: ToolContext, args: ApiGenerateClientInput) -> ToolOutcome:
    out_p = Path(args.output_dir) if args.output_dir else None
    res = ctx.runtime.api.generate_client(
        project_id=args.project_id,
        language=args.language,
        output_dir=out_p,
    )
    return ToolOutcome(data=res.model_dump(mode="json"))


async def _api_run_contract_tests(ctx: ToolContext, args: ApiRunContractTestsInput) -> ToolOutcome:
    res = ctx.runtime.api.run_contract_tests(
        project_id=args.project_id,
        operation_id=args.operation_id,
    )
    return ToolOutcome(data=res)


async def _api_diff_contracts(ctx: ToolContext, args: ApiDiffContractsInput) -> ToolOutcome:
    cand = OpenAPISpec.model_validate(args.candidate_spec)
    findings = ctx.runtime.api.diff_specs(
        project_id=args.project_id,
        candidate_spec=cand,
        ignore_volatile=args.ignore_volatile,
    )
    return ToolOutcome(
        data={
            "findings": [f.model_dump(mode="json") for f in findings],
            "total": len(findings),
        }
    )


async def _api_get_drift(ctx: ToolContext, args: ApiGetDriftInput) -> ToolOutcome:
    res = ctx.runtime.api.get_drift(project_id=args.project_id)
    return ToolOutcome(data=res)


async def _api_export_har(ctx: ToolContext, args: ApiExportHarInput) -> ToolOutcome:
    res = ctx.runtime.api.export_har(
        project_id=args.project_id,
        flow_ids=args.flow_ids,
    )
    return ToolOutcome(data=res)


async def _api_synthesize_spec(ctx: ToolContext, args: ApiSynthesizeSpecInput) -> ToolOutcome:
    res = ctx.runtime.api.synthesize_spec(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        min_occurrences=args.min_occurrences,
        include_headers=args.include_headers,
        format=args.format,
    )
    return ToolOutcome(data=res)


async def _api_export_postman(ctx: ToolContext, args: ApiExportPostmanInput) -> ToolOutcome:
    res = ctx.runtime.api.export_postman(
        project_id=args.project_id,
        collection_name=args.collection_name,
        base_url_variable=args.base_url_variable,
    )
    return ToolOutcome(data=res)


async def _api_export_hoppscotch(ctx: ToolContext, args: ApiExportHoppscotchInput) -> ToolOutcome:
    res = ctx.runtime.api.export_hoppscotch(
        project_id=args.project_id,
        collection_name=args.collection_name,
        base_url=args.base_url,
    )
    return ToolOutcome(data=res)


def _read_text_file(path_str: str | None) -> str | None:
    if not path_str:
        return None
    p = Path(path_str)
    if p.exists() and p.is_file():
        with contextlib.suppress(Exception):
            return p.read_text(encoding="utf-8", errors="ignore")
    return None


async def _crawl_endpoint_docs(ctx: ToolContext, args: CrawlEndpointDocsInput) -> ToolOutcome:
    content = _read_text_file(args.doc_path) or args.doc_content or ""
    res = crawl_endpoint_documentation(base_url=args.base_url, doc_content=content)
    return ToolOutcome(data=res)


async def _crawl_privacy_policy_audit(
    ctx: ToolContext, args: CrawlPrivacyPolicyAuditInput
) -> ToolOutcome:
    text = _read_text_file(args.policy_path) or args.policy_text or ""
    res = audit_privacy_policy(
        policy_text=text,
        declared_permissions=args.declared_permissions,
    )
    return ToolOutcome(data=res)


async def _net_ip_intel(ctx: ToolContext, args: NetIpIntelInput) -> ToolOutcome:
    res = ctx.runtime.api.analyze_ip_intel(
        ip_addresses=args.ip_addresses,
        threat_threshold=args.threat_threshold,
    )
    return ToolOutcome(data=res)


async def _net_cti_reputation_check(
    ctx: ToolContext, args: NetCtiReputationCheckInput
) -> ToolOutcome:
    res = ctx.runtime.api.check_cti(
        targets=args.targets,
        threat_threshold=args.threat_threshold,
    )
    return ToolOutcome(data=res)


async def _api_semantic_waf_audit(ctx: ToolContext, args: ApiSemanticWafAuditInput) -> ToolOutcome:
    res = ctx.runtime.api.audit_semantic_waf(
        endpoint_url=args.endpoint_url,
        http_method=args.http_method,
        query_params=args.query_params,
        request_body=args.request_body,
        headers=args.headers,
    )
    return ToolOutcome(data=res)


async def _api_bypass_403_test(ctx: ToolContext, args: ApiBypass403TestInput) -> ToolOutcome:
    res = ctx.runtime.api.generate_403_bypasses(
        target_url=args.target_url,
        http_method=args.http_method,
        base_headers=args.base_headers,
    )
    return ToolOutcome(data=res)


async def _api_rotating_proxy_session(
    ctx: ToolContext, args: ApiRotatingProxySessionInput
) -> ToolOutcome:
    res = ctx.runtime.api.create_rotating_proxy_session(
        target_url=args.target_url,
        regions=args.regions,
        provider=args.provider,
        max_retries=args.max_retries,
        backoff_factor=args.backoff_factor,
        rotate_on_status=args.rotate_on_status,
    )
    return ToolOutcome(data=res)


async def _api_backend_recon(ctx: ToolContext, args: ApiBackendReconInput) -> ToolOutcome:
    del ctx
    res = await crawl_backend_surface(
        base_urls=args.base_urls,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
    )
    return ToolOutcome(data=res)


# --- Register Function ---


def register(registry: CapabilityRegistry) -> None:
    """Register all Phase 7 API reverse-engineering studio tools."""
    registry.register(
        _api_spec(
            name="api_capture_start",
            title="Start API capture",
            description="Start authorized network capture session.",
            handler=_api_capture_start,
            input_model=ApiCaptureStartInput,
            scopes=frozenset({NETWORK_CAPTURE, PROJECT_READ}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _api_spec(
            name="api_capture_stop",
            title="Stop API capture",
            description="Stop and finalize network capture session.",
            handler=_api_capture_stop,
            input_model=ApiCaptureStopInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _api_spec(
            name="api_capture_status",
            title="API capture status",
            description="Query capture session and flow metrics.",
            handler=_api_capture_status,
            input_model=ApiCaptureStatusInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_list_flows",
            title="List API flows",
            description="Paginated network flows with filtering.",
            handler=_api_list_flows,
            input_model=ApiListFlowsInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_get_flow",
            title="Get API flow",
            description="Full flow record with redaction status.",
            handler=_api_get_flow,
            input_model=ApiGetFlowInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_cluster_operations",
            title="Cluster operations",
            description="Build or refresh de-duplicated operation clusters.",
            handler=_api_cluster_operations,
            input_model=ApiClusterOperationsInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _api_spec(
            name="api_list_operations",
            title="List operations",
            description="Catalogue of clustered operations.",
            handler=_api_list_operations,
            input_model=ApiListOperationsInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_get_operation",
            title="Get operation",
            description="Operation cluster details, samples, and schema.",
            handler=_api_get_operation,
            input_model=ApiGetOperationInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_infer_schemas",
            title="Infer schemas",
            description="Infer request and response schemas from observed flows.",
            handler=_api_infer_schemas,
            input_model=ApiInferSchemasInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _api_spec(
            name="api_generate_spec",
            title="Generate OpenAPI spec",
            description="Emit validated OpenAPI 3.1 specification document.",
            handler=_api_generate_spec,
            input_model=ApiGenerateSpecInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _api_spec(
            name="api_generate_client",
            title="Generate API client",
            description="Generate typed client with compilation and smoke tests.",
            handler=_api_generate_client,
            input_model=ApiGenerateClientInput,
            scopes=frozenset({PROJECT_READ, EXPORT_RAW}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _api_spec(
            name="api_run_contract_tests",
            title="Run contract tests",
            description="Validate observed behavior against OpenAPI contracts.",
            handler=_api_run_contract_tests,
            input_model=ApiRunContractTestsInput,
            scopes=frozenset({PROJECT_READ, NETWORK_CAPTURE}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _api_spec(
            name="api_diff_contracts",
            title="Diff API contracts",
            description="Compare baseline vs candidate OpenAPI specifications.",
            handler=_api_diff_contracts,
            input_model=ApiDiffContractsInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_get_drift",
            title="Get API drift",
            description="Report breaking and additive schema drift findings.",
            handler=_api_get_drift,
            input_model=ApiGetDriftInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_export_har",
            title="Export HAR",
            description="Export redacted flows as standard HAR 1.2 with RAA extensions.",
            handler=_api_export_har,
            input_model=ApiExportHarInput,
            scopes=frozenset({PROJECT_READ, EXPORT_WRITE}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_synthesize_spec",
            title="Synthesize OpenAPI 3.1 spec",
            description="Cluster endpoints, infer schemas, and synthesize OpenAPI 3.1 spec.",
            handler=_api_synthesize_spec,
            input_model=ApiSynthesizeSpecInput,
            scopes=frozenset({PROJECT_READ}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _api_spec(
            name="api_export_postman",
            title="Export Postman collection",
            description="Export synthesized endpoints as runnable Postman Collection v2.1.",
            handler=_api_export_postman,
            input_model=ApiExportPostmanInput,
            scopes=frozenset({PROJECT_READ, EXPORT_WRITE}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="crawl_endpoint_docs",
            title="Crawl API documentation",
            description=(
                "Autonomously harvest REST endpoints, parameters, and authentication "
                "schemes from remote documentation or Swagger pages."
            ),
            handler=_crawl_endpoint_docs,
            input_model=CrawlEndpointDocsInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="crawl_privacy_policy_audit",
            title="Audit remote privacy policy",
            description=(
                "Cross-audit remote privacy policy disclosures against actual APK "
                "permissions and PII flows."
            ),
            handler=_crawl_privacy_policy_audit,
            input_model=CrawlPrivacyPolicyAuditInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="net_ip_intel",
            title="Backend IP Intelligence & ASN Attribution",
            description=(
                "Analyze backend IP addresses for ASN attribution, cloud hosting detection "
                "(AWS, GCP, Azure, Cloudflare), bogon validation, and threat risk scoring."
            ),
            handler=_net_ip_intel,
            input_model=NetIpIntelInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="net_cti_reputation_check",
            title="CrowdSec CTI Threat Intelligence Check",
            description=(
                "Check backend IP addresses and domains against threat intelligence "
                "feeds, Tor exit nodes, and dynamic DNS proxies."
            ),
            handler=_net_cti_reputation_check,
            input_model=NetCtiReputationCheckInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_semantic_waf_audit",
            title="Semantic WAF & AST Injection Scanner",
            description=(
                "Audit mobile API endpoints against SQLi, CMDi, NoSQLi, and Path Traversal "
                "using SafeLine-inspired AST syntactic tokenization."
            ),
            handler=_api_semantic_waf_audit,
            input_model=ApiSemanticWafAuditInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_bypass_403_test",
            title="API 401/403 Access Control Bypass Generator",
            description=(
                "Generate structured HTTP mutations (headers, paths, verbs) inspired by "
                "nomore403 to evaluate mobile API endpoints for authorization bypasses."
            ),
            handler=_api_bypass_403_test,
            input_model=ApiBypass403TestInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_rotating_proxy_session",
            title="Cloud Rotating Proxy Session Configurator",
            description=(
                "Establish multi-region rotating cloud gateway proxy egress sessions "
                "inspired by requests-ip-rotator to prevent rate-limiting (429) during API audits."
            ),
            handler=_api_rotating_proxy_session,
            input_model=ApiRotatingProxySessionInput,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_backend_recon",
            title="Backend Web & JS Endpoint Recon Crawler",
            description=(
                "Crawl extracted mobile backend URLs using httpx to harvest JS API endpoints, "
                "query parameters, subdomains, S3 buckets, and exposed secret tokens."
            ),
            handler=_api_backend_recon,
            input_model=ApiBackendReconInput,
            scopes=frozenset({NETWORK_CRAWL}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _api_spec(
            name="api_export_hoppscotch",
            title="Export Hoppscotch v2 API Collection",
            description=(
                "Export synthesized or clustered mobile API endpoints to a Hoppscotch v2 JSON collection."
            ),
            handler=_api_export_hoppscotch,
            input_model=ApiExportHoppscotchInput,
            scopes=frozenset({PROJECT_READ, EXPORT_WRITE}),
            read_only=False,
            idempotent=True,
        )
    )
