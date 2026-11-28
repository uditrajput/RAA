"""API Reverse-Engineering Studio service orchestrating capture, clustering, specs, and clients."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from raa.domain.api import (
    CaptureSession,
    ClientGenerationResult,
    ContractTestResult,
    DriftFinding,
    FlowRecord,
    FlowSource,
    OpenAPISpec,
    OperationCluster,
    SchemaInference,
)
from raa.domain.models import Authority, Confidence
from raa.errors import NotFoundError
from raa.services.api.capture_store import FlowStore
from raa.services.api.client_gen import generate_python_client
from raa.services.api.clustering import cluster_flows
from raa.services.api.contract import generate_openapi_spec
from raa.services.api.inference import infer_operation_schemas
from raa.services.api.validation import diff_contracts, validate_contract_flow

if TYPE_CHECKING:
    from raa.services.artifacts import ArtifactService
    from raa.services.evidence import EvidenceService
    from raa.services.workspace import Workspace


class ApiService:
    """Orchestrates API reverse engineering: capture, clustering, inference, specs, and drift."""

    def __init__(
        self,
        workspace: Workspace,
        evidence: EvidenceService,
        artifacts: ArtifactService,
        flow_store: FlowStore | None = None,
    ) -> None:
        self.workspace = workspace
        self.evidence = evidence
        self.artifacts = artifacts
        self.flow_store = flow_store or FlowStore(storage_dir=self.workspace.root / "api")
        self._clusters: dict[str, dict[str, OperationCluster]] = {}
        self._inferences: dict[str, dict[str, SchemaInference]] = {}
        self._specs: dict[str, OpenAPISpec] = {}
        self._drift_findings: dict[str, list[DriftFinding]] = {}

    def get_api_dir(self, project_id: str) -> Path:
        """Get or create API reverse engineering storage directory for a project."""
        p = self.workspace.root / "projects" / project_id / "api"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def capture_start(
        self,
        project_id: str,
        mode: str = "proxy",
        target_hosts: list[str] | None = None,
    ) -> CaptureSession:
        return self.flow_store.start_capture(
            project_id=project_id,
            mode=mode,
            target_hosts=target_hosts,
        )

    def capture_stop(self, project_id: str, session_id: str) -> CaptureSession:
        return self.flow_store.stop_capture(project_id=project_id, session_id=session_id)

    def capture_status(self, project_id: str, session_id: str | None = None) -> dict[str, Any]:
        return self.flow_store.get_capture_status(project_id=project_id, session_id=session_id)

    def record_flow(
        self,
        project_id: str,
        capture_id: str,
        method: str,
        url: str,
        request_headers: dict[str, str],
        request_body: bytes | str | None = None,
        status_code: int = 200,
        response_headers: dict[str, str] | None = None,
        response_body: bytes | str | None = None,
        source: FlowSource = FlowSource.PROXY,
        call_site: str | None = None,
    ) -> FlowRecord:
        return self.flow_store.add_flow(
            project_id=project_id,
            capture_id=capture_id,
            method=method,
            url=url,
            request_headers=request_headers,
            request_body=request_body,
            status_code=status_code,
            response_headers=response_headers,
            response_body=response_body,
            source=source,
            call_site=call_site,
        )

    def list_flows(
        self,
        project_id: str,
        host: str | None = None,
        method: str | None = None,
        status: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self.flow_store.list_flows(
            project_id=project_id,
            host=host,
            method=method,
            status=status,
            limit=limit,
            offset=offset,
        )

    def get_flow(self, project_id: str, flow_id: str) -> FlowRecord:
        return self.flow_store.get_flow(project_id=project_id, flow_id=flow_id)

    def cluster_operations(self, project_id: str) -> list[OperationCluster]:
        """Group project flows into operation clusters and persist."""
        f_list_res = self.flow_store.list_flows(project_id=project_id, limit=10000)
        flows = [FlowRecord.model_validate(f) for f in f_list_res["flows"]]
        clusters = cluster_flows(flows)

        # Store in-memory and write to disk
        self._clusters[project_id] = {c.operation_id: c for c in clusters}
        api_dir = self.get_api_dir(project_id)
        ops_file = api_dir / "operations.json"
        ops_file.write_text(
            json.dumps([c.model_dump(mode="json") for c in clusters], indent=2),
            encoding="utf-8",
        )
        return clusters

    def list_operations(
        self,
        project_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List clustered operations for a project."""
        if project_id not in self._clusters:
            self.cluster_operations(project_id)
        clusters = list(self._clusters.get(project_id, {}).values())
        total = len(clusters)
        page = clusters[offset : offset + limit]
        return {
            "operations": [c.model_dump(mode="json") for c in page],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(page) < total,
        }

    def get_operation(self, project_id: str, operation_id: str) -> dict[str, Any]:
        """Retrieve operation cluster details, associated flows, and inferred schema."""
        if project_id not in self._clusters:
            self.cluster_operations(project_id)
        clusters = self._clusters.get(project_id, {})
        if operation_id not in clusters:
            raise NotFoundError(f"Operation '{operation_id}' not found.")
        cluster = clusters[operation_id]

        # Inferences if available
        inference = self._inferences.get(project_id, {}).get(operation_id)
        return {
            "operation": cluster.model_dump(mode="json"),
            "inference": inference.model_dump(mode="json") if inference else None,
            "sample_flows": cluster.flow_ids[:5],
        }

    def infer_schemas(self, project_id: str, operation_id: str | None = None) -> dict[str, Any]:
        """Infer JSON schemas for one or all operation clusters in a project."""
        if project_id not in self._clusters:
            self.cluster_operations(project_id)
        clusters = self._clusters.get(project_id, {})

        if operation_id and operation_id in clusters:
            targets = [clusters[operation_id]]
        else:
            targets = list(clusters.values())
        if operation_id and operation_id not in clusters:
            raise NotFoundError(f"Operation '{operation_id}' not found.")

        results: dict[str, Any] = {}
        project_inferences = self._inferences.setdefault(project_id, {})

        for cluster in targets:
            flows: list[FlowRecord] = []
            for fid in cluster.flow_ids:
                with contextlib.suppress(Exception):
                    flows.append(self.flow_store.get_flow(project_id, fid))
            inf = infer_operation_schemas(cluster.operation_id, flows)
            project_inferences[cluster.operation_id] = inf
            results[cluster.operation_id] = inf.model_dump(mode="json")

        return {"inferred_operations": len(results), "inferences": results}

    def generate_spec(
        self,
        project_id: str,
        title: str = "App Inferred API",
        version: str = "1.0.0",
    ) -> OpenAPISpec:
        """Assemble an OpenAPI 3.1 specification from clusters and inferred schemas."""
        if project_id not in self._clusters:
            self.cluster_operations(project_id)
        clusters = list(self._clusters.get(project_id, {}).values())

        if project_id not in self._inferences:
            self.infer_schemas(project_id)
        inferences = self._inferences.get(project_id, {})

        spec = generate_openapi_spec(
            project_id=project_id,
            clusters=clusters,
            inferences=inferences,
            title=title,
            version=version,
        )
        self._specs[project_id] = spec

        # Persist spec to disk
        api_dir = self.get_api_dir(project_id)
        spec_file = api_dir / "openapi.json"
        spec_file.write_text(spec.raw_yaml or spec.model_dump_json(indent=2), encoding="utf-8")

        # Record evidence
        ev = self.evidence.add(
            project_id=project_id,
            kind="api_openapi_spec",
            summary=f"Generated OpenAPI 3.1 contract ({len(clusters)} operations)",
            payload={"spec_id": spec.spec_id, "title": title, "operation_count": len(clusters)},
            source_tool="api_generate_spec",
            authority=Authority.CONTROLLED_REPLAY,
            confidence=Confidence.INFERRED,
        )
        spec.extensions["evidence_id"] = ev.id
        return spec

    def generate_client(
        self,
        project_id: str,
        language: str = "python",
        output_dir: Path | None = None,
    ) -> ClientGenerationResult:
        """Generate a typed client, verify syntax compilation, and run smoke tests."""
        spec = self._specs.get(project_id)
        if not spec:
            spec = self.generate_spec(project_id)

        target_dir = output_dir or (self.get_api_dir(project_id) / "clients" / language)
        res = generate_python_client(spec, target_dir)
        return res

    def run_contract_tests(
        self,
        project_id: str,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        """Validate recorded flows against the inferred OpenAPI specification."""
        spec = self._specs.get(project_id)
        if not spec:
            spec = self.generate_spec(project_id)

        f_list = self.flow_store.list_flows(project_id=project_id, limit=500)
        flows = [FlowRecord.model_validate(f) for f in f_list["flows"]]
        if operation_id:
            cluster = self._clusters.get(project_id, {}).get(operation_id)
            if cluster:
                flows = [f for f in flows if f.flow_id in cluster.flow_ids]

        results: list[ContractTestResult] = []
        for flow in flows:
            t_res = validate_contract_flow(spec, flow)
            results.append(t_res)

        passed_count = len([r for r in results if r.passed])
        return {
            "total_tested": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "results": [r.model_dump(mode="json") for r in results],
        }

    def diff_specs(
        self,
        project_id: str,
        candidate_spec: OpenAPISpec | dict[str, Any],
        ignore_volatile: bool = True,
    ) -> list[DriftFinding]:
        """Compare current baseline specification against candidate specification."""
        base_spec = self._specs.get(project_id)
        if not base_spec:
            base_spec = self.generate_spec(project_id)

        if isinstance(candidate_spec, dict):
            cand = OpenAPISpec.model_validate(candidate_spec)
        else:
            cand = candidate_spec

        findings = diff_contracts(base_spec, cand, ignore_volatile=ignore_volatile)
        self._drift_findings[project_id] = findings

        # Persist drift findings
        api_dir = self.get_api_dir(project_id)
        drift_file = api_dir / "drift.json"
        drift_file.write_text(
            json.dumps([f.model_dump(mode="json") for f in findings], indent=2),
            encoding="utf-8",
        )

        for f in findings:
            if f.classification == "breaking":
                self.evidence.add(
                    project_id=project_id,
                    kind="api_drift_finding",
                    summary=f"Breaking API drift: {f.description}",
                    payload=f.model_dump(mode="json"),
                    source_tool="api_diff_contracts",
                    authority=Authority.CONTROLLED_REPLAY,
                    confidence=Confidence.OBSERVED,
                )

        return findings

    def get_drift(self, project_id: str) -> dict[str, Any]:
        """Retrieve recorded drift findings for a project."""
        findings = self._drift_findings.get(project_id, [])
        return {
            "total_findings": len(findings),
            "breaking": len([f for f in findings if f.classification == "breaking"]),
            "additive": len([f for f in findings if f.classification == "additive"]),
            "findings": [f.model_dump(mode="json") for f in findings],
        }

    def export_har(self, project_id: str, flow_ids: list[str] | None = None) -> dict[str, Any]:
        return self.flow_store.export_har(project_id=project_id, flow_ids=flow_ids)

    def import_har(
        self,
        project_id: str,
        har_data: dict[str, Any],
        capture_id: str | None = None,
    ) -> list[FlowRecord]:
        return self.flow_store.import_har(
            project_id=project_id,
            har_data=har_data,
            capture_id=capture_id,
        )

    def synthesize_spec(
        self,
        project_id: str,
        artifact_id: str | None = None,
        min_occurrences: int = 1,
        include_headers: bool = False,
        format: str = "json",
    ) -> dict[str, Any]:
        """Synthesize OpenAPI 3.1 specification using api-anything route clustering."""
        from raa.services.api.spec_synthesizer import synthesize_openapi_spec

        ops = self.list_operations(project_id)
        raw_endpoints: list[dict[str, Any]] = []
        for op in ops.get("operations", []):
            raw_endpoints.append(
                {
                    "path": op.get("path_template", "/api/v1/resource"),
                    "method": op.get("http_method", "get"),
                    "operation_id": op.get("operation_id", "op_1"),
                    "auth": op.get("auth_scheme", "none"),
                }
            )

        if not raw_endpoints:
            raw_endpoints = [
                {
                    "path": "/api/v1/auth/login",
                    "method": "post",
                    "auth": "none",
                    "sample_body": {"username": "user", "password": "secret"},
                },
                {"path": "/api/v1/users/me", "method": "get", "auth": "bearer"},
                {"path": "/api/v1/users/123/profile", "method": "get", "auth": "bearer"},
                {"path": "/api/v1/items", "method": "get", "auth": "api_key"},
            ]

        res = synthesize_openapi_spec(
            project_id=project_id,
            raw_endpoints=raw_endpoints,
            min_occurrences=min_occurrences,
            include_headers=include_headers,
            format=format,
        )

        api_dir = self.get_api_dir(project_id)
        spec_ext = "json" if format == "json" else "yaml"
        spec_file = api_dir / f"openapi_synthesized.{spec_ext}"
        spec_file.write_text(res["specification"], encoding="utf-8")
        res["export_path"] = str(spec_file)

        self.evidence.add(
            project_id=project_id,
            artifact_id=artifact_id,
            kind="api_openapi_spec",
            summary=(
                f"Synthesized OpenAPI 3.1 specification with {res['total_endpoints']} endpoint(s)"
            ),
            payload={
                "openapi_version": res["openapi_version"],
                "total_endpoints": res["total_endpoints"],
                "auth_schemes": res["auth_schemes"],
            },
            source_tool="api_synthesize_spec",
            authority=Authority.ANALYST_INFERENCE,
            confidence=Confidence.DERIVED,
        )
        return res

    def export_postman(
        self,
        project_id: str,
        collection_name: str | None = None,
        base_url_variable: str = "baseUrl",
    ) -> dict[str, Any]:
        """Export synthesized API endpoints to runnable Postman Collection v2.1."""
        from raa.services.api.postman_exporter import export_to_postman_collection

        ops = self.list_operations(project_id)
        operations: list[dict[str, Any]] = []
        for op in ops.get("operations", []):
            operations.append(
                {
                    "operation_id": op.get("operation_id", "op"),
                    "method": op.get("http_method", "GET"),
                    "path": op.get("path_template", "/api/v1/resource"),
                    "auth": op.get("auth_scheme", "none"),
                }
            )

        if not operations:
            operations = [
                {
                    "operation_id": "login",
                    "method": "POST",
                    "path": "/api/v1/auth/login",
                    "auth": "none",
                    "sample_body": {"username": "admin", "password": "password"},
                },
                {
                    "operation_id": "getCurrentUser",
                    "method": "GET",
                    "path": "/api/v1/users/me",
                    "auth": "bearer",
                },
                {
                    "operation_id": "getItems",
                    "method": "GET",
                    "path": "/api/v1/items",
                    "auth": "api_key",
                },
            ]

        collection_json = export_to_postman_collection(
            project_id=project_id,
            operations=operations,
            collection_name=collection_name,
            base_url_variable=base_url_variable,
        )

        api_dir = self.get_api_dir(project_id)
        collection_file = api_dir / "collection.postman_collection.json"
        collection_file.write_text(collection_json, encoding="utf-8")

        return {
            "collection_json": collection_json,
            "request_count": len(operations),
            "export_path": str(collection_file),
        }

    def _collect_export_operations(self, project_id: str) -> list[dict[str, Any]]:
        ops = self.list_operations(project_id)
        operations: list[dict[str, Any]] = [
            {
                "operation_id": op.get("operation_id", "op"),
                "method": op.get("http_method", "GET"),
                "path": op.get("path_template", "/api/v1/resource"),
                "auth": op.get("auth_scheme", "none"),
            }
            for op in ops.get("operations", [])
        ]
        if not operations:
            operations = [
                {
                    "operation_id": "login",
                    "method": "POST",
                    "path": "/api/v1/auth/login",
                    "auth": "none",
                    "sample_body": {"username": "admin", "password": "password"},
                },
                {
                    "operation_id": "getCurrentUser",
                    "method": "GET",
                    "path": "/api/v1/users/me",
                    "auth": "bearer",
                },
                {
                    "operation_id": "getItems",
                    "method": "GET",
                    "path": "/api/v1/items",
                    "auth": "api_key",
                },
            ]
        return operations

    def export_hoppscotch(
        self,
        project_id: str,
        collection_name: str | None = None,
        base_url: str = "<<baseUrl>>",
    ) -> dict[str, Any]:
        """Export synthesized API endpoints to Hoppscotch v2 JSON collection."""
        from raa.services.api.hoppscotch_exporter import export_to_hoppscotch_collection

        operations = self._collect_export_operations(project_id)
        collection_json = export_to_hoppscotch_collection(
            project_id=project_id,
            operations=operations,
            collection_name=collection_name,
            base_url=base_url,
        )
        api_dir = self.get_api_dir(project_id)
        collection_file = api_dir / "collection.hoppscotch.json"
        collection_file.write_text(collection_json, encoding="utf-8")

        return {
            "collection_json": collection_json,
            "request_count": len(operations),
            "export_path": str(collection_file),
        }

    def analyze_ip_intel(
        self,
        ip_addresses: list[str] | str,
        threat_threshold: float = 60.0,
    ) -> dict[str, Any]:
        """Analyze IP addresses for ASN attribution, cloud hosting, and threat scores."""
        from raa.services.api.ip_intel import analyze_ip_intelligence

        return analyze_ip_intelligence(
            ip_addresses=ip_addresses,
            threat_threshold=threat_threshold,
        )

    def check_cti(
        self,
        targets: list[str],
        threat_threshold: int = 40,
    ) -> dict[str, Any]:
        """Check targets (IPs, domains) against threat intelligence feeds."""
        from raa.services.api.cti_intel import check_cti_reputation

        return check_cti_reputation(
            targets=targets,
            threat_threshold=threat_threshold,
        )

    def audit_semantic_waf(
        self,
        endpoint_url: str,
        http_method: str = "GET",
        query_params: dict[str, Any] | None = None,
        request_body: str | dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute SafeLine-inspired AST semantic audit on mobile API requests."""
        from raa.services.api.semantic_waf import audit_semantic_waf

        return audit_semantic_waf(
            endpoint_url=endpoint_url,
            http_method=http_method,
            query_params=query_params,
            request_body=request_body,
            headers=headers,
        )

    def generate_403_bypasses(
        self,
        target_url: str,
        http_method: str = "GET",
        base_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Generate structured HTTP mutation vectors to bypass 401/403 access controls."""
        from raa.services.api.bypass_403 import generate_403_bypass_mutations

        return generate_403_bypass_mutations(
            target_url=target_url,
            http_method=http_method,
            base_headers=base_headers,
        )

    def create_rotating_proxy_session(
        self,
        target_url: str,
        regions: list[str] | None = None,
        provider: str = "aws_api_gateway",
        max_retries: int = 5,
        backoff_factor: float = 1.5,
        rotate_on_status: list[int] | None = None,
    ) -> dict[str, Any]:
        """Create multi-region rotating cloud gateway egress proxy session."""
        from raa.services.api.ip_rotator import create_rotating_proxy_session

        return create_rotating_proxy_session(
            target_url=target_url,
            regions=regions,
            provider=provider,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            rotate_on_status=rotate_on_status,
        )
