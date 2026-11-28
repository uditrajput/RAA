"""Security, privacy, SBOM, vulnerability, and threat intelligence MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from raa.errors import PolicyDeniedError
from raa.policy.scopes import EXPORT_RAW, LLM_EXTERNAL, NETWORK_OSINT, PROJECT_READ, STATIC_READ
from raa.registry.models import (
    CapabilityRegistry,
    ToolAnnotations,
    ToolContext,
    ToolOutcome,
    ToolSpec,
)
from raa.registry.profiles import ADMIN, CORE

# --- Input Models ---


class SecurityScanStaticInput(BaseModel):
    """Parameters to run static security and MASVS compliance checks."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    categories: list[str] | None = Field(
        default=None,
        description="Optional MASVS categories (storage, crypto, auth, network, platform, code).",
    )


class SecurityGetFindingsInput(BaseModel):
    """Parameters to query normalized security findings."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    severity: Literal["info", "low", "medium", "high", "critical"] | None = Field(
        default=None, description="Optional severity filter."
    )
    masvs_category: str | None = Field(
        default=None, description="Optional MASVS category filter (e.g. 'crypto', 'storage')."
    )
    limit: int = Field(default=50, ge=1, le=500, description="Page limit.")
    offset: int = Field(default=0, ge=0, description="Page offset.")


class SecurityFindSecretsInput(BaseModel):
    """Parameters to scan container for embedded secrets, API keys, and credentials."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    include_redacted: bool = Field(
        default=True, description="Whether to include redacted secret locations."
    )


class PrivacyDataFlowsInput(BaseModel):
    """Parameters to identify PII source-to-sink transmission paths."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    pii_type: str | None = Field(
        default=None,
        description="Optional PII filter (location, contacts, camera, mic, sms).",
    )


class SdkInventoryInput(BaseModel):
    """Parameters to scan and catalog third-party SDKs and tracking libraries."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    category: str | None = Field(
        default=None,
        description="Optional category filter (analytics, ads, crashes, networking).",
    )


class SbomGenerateInput(BaseModel):
    """Parameters to generate a standard Software Bill of Materials (SBOM)."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    format: Literal["cyclonedx", "spdx"] = Field(
        default="cyclonedx", description="Output format (cyclonedx or spdx)."
    )


class VulnerabilityScanInput(BaseModel):
    """Parameters to correlate software components with known CVE security advisories."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    min_severity: Literal["info", "low", "medium", "high", "critical"] = Field(
        default="low", description="Minimum severity threshold."
    )


class YaraScanInput(BaseModel):
    """Parameters to scan application contents with YARA rules."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    rules_path: str | None = Field(default=None, description="Optional path to custom YARA rules.")
    rule_names: list[str] | None = Field(
        default=None, description="Optional specific rule names to evaluate."
    )


class CapaScanInput(BaseModel):
    """Parameters to detect offensive capabilities and behaviors with capa."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    rules_path: str | None = Field(default=None, description="Optional path to custom capa rules.")


class QuarkScoreInput(BaseModel):
    """Parameters to compute Android behavioral threat score using Quark rules."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class IocExtractInput(BaseModel):
    """Parameters to harvest Indicators of Compromise from static and dynamic evidence."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class IocExportInput(BaseModel):
    """Parameters to export IOCs in structured exchange formats."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    format: Literal["json", "csv", "stix", "stix21"] = Field(
        default="json", description="Export format (json, csv, stix, or stix21)."
    )


class SampleEnrichInput(BaseModel):
    """Parameters to query external threat intelligence feeds."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    provider: str = Field(default="internal", description="Threat intelligence provider name.")
    user_consent: bool = Field(
        default=False,
        description="Explicit user consent to transmit sample hash to external service.",
    )


class PlayProtectAuditInput(BaseModel):
    """Parameters to run pre-flight Google Play Protect compliance audit."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class DclDetectInput(BaseModel):
    """Parameters to scan for Dynamic Code Loading (DCL) patterns."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class MobSfRuleScanInput(BaseModel):
    """Parameters to evaluate MobSF static security rules."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class CvssScorecardInput(BaseModel):
    """Parameters to generate CVSS v3.1 risk scorecard."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class SarifExportInput(BaseModel):
    """Parameters to export security findings to OASIS SARIF v2.1.0 format."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class StrideModelInput(BaseModel):
    """Parameters to model threats via STRIDE mapped to MITRE ATT&CK for Mobile."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class PocGenerateInput(BaseModel):
    """Parameters to generate non-destructive exploit PoC commands."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    finding_id: str = Field(min_length=1, description="Target finding identifier.")
    title: str = Field(default="Security Vulnerability", description="Finding title.")
    target_package: str = Field(
        default="com.example.app", description="Target application package name."
    )
    component: str | None = Field(default=None, description="Optional target component name.")
    parameter: str | None = Field(default=None, description="Optional target parameter name.")


class IntentRedirectionScanInput(BaseModel):
    """Parameters to scan for Intent Redirection vulnerabilities."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class PendingIntentAuditInput(BaseModel):
    """Parameters to scan for implicit mutable PendingIntents."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class AidlAuthAuditInput(BaseModel):
    """Parameters to audit AIDL and bound services for caller authentication flaws."""

    project_id: str = Field(min_length=1, description="Target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")


class PocValidateInput(BaseModel):
    """Parameters to validate an exploit Proof-of-Concept for safety and exploitability."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    vuln_type: str = Field(
        default="intent_redirection", description="Vulnerability type (e.g. intent_redirection)."
    )
    target_package: str = Field(
        default="com.example.app", description="Target application package name."
    )
    target_component: str | None = Field(default=None, description="Target component name.")
    poc_script: str | None = Field(default=None, description="Optional raw ADB/Frida script.")
    intent_action: str | None = Field(default=None, description="Optional Intent action.")
    intent_data: str | None = Field(default=None, description="Optional Intent URI data.")
    intent_extra: dict[str, Any] | None = Field(
        default=None, description="Optional Intent key-value extras."
    )
    manifest_xml: str | None = Field(
        default=None, description="Optional AndroidManifest.xml for permission checks."
    )


class SecMasvsAuditInput(BaseModel):
    """Parameters to evaluate app posture against OWASP MASVS v2.0."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    manifest_xml: str | None = Field(default=None, description="Optional manifest XML content.")
    is_debuggable: bool = Field(default=False, description="Whether debuggable flag is enabled.")
    uses_cleartext: bool = Field(default=False, description="Whether cleartext traffic is enabled.")
    is_minified: bool = Field(default=True, description="Whether code is R8/ProGuard minified.")
    has_root_detection: bool = Field(default=False, description="Whether root detection is active.")
    findings: list[dict[str, Any]] | None = Field(
        default=None, description="Optional security findings to map to MASVS domains."
    )


class CopilotSuggestNextInput(BaseModel):
    """Parameters to recommend next reversing tools and strategies based on analyst goal."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    user_goal: str = Field(min_length=1, description="Analyst reversing query or objective.")
    detected_frameworks: list[str] | None = Field(
        default=None, description="Optional list of detected frameworks."
    )
    manifest_summary: dict[str, Any] | None = Field(
        default=None, description="Optional manifest summary metadata."
    )
    findings_summary: dict[str, Any] | None = Field(
        default=None, description="Optional findings summary."
    )


class SecBugbountyReportFormatInput(BaseModel):
    """Parameters to format security findings into a Bug Bounty submission report."""

    title: str = Field(min_length=1, description="Vulnerability title.")
    vulnerability_type: str = Field(
        min_length=1,
        description="Vulnerability classification (e.g. IDOR, SQLi, Intent Hijacking).",
    )
    severity: str = Field(
        default="High", description="Severity (Critical, High, Medium, Low, Info)."
    )
    target: str = Field(min_length=1, description="Target application or endpoint.")
    description: str = Field(min_length=1, description="Detailed explanation of the flaw.")
    steps_to_reproduce: list[str] | str = Field(
        description="Numbered steps or bullet points to reproduce."
    )
    impact: str = Field(min_length=1, description="Business and security impact.")
    platform: str = Field(default="HackerOne", description="Target platform (HackerOne, Bugcrowd).")
    cvss_vector: str | None = Field(default=None, description="Optional CVSS v3.1 vector string.")
    remediation: str | None = Field(default=None, description="Recommended remediation advice.")
    poc_code: str | None = Field(default=None, description="Optional code or script snippet.")


class SecLeakedEmailIntelInput(BaseModel):
    """Parameters to run OSINT email reconnaissance against developer services."""

    emails: list[str] = Field(min_length=1, description="Target email addresses to analyze.")
    project_id: str | None = Field(
        default=None,
        description="Optional RAA project ID (required for live holehe/openosint modes).",
    )
    mode: Literal["offline", "holehe", "openosint"] = Field(
        default="offline",
        description="Execution mode: deterministic offline baseline, holehe CLI, or OpenOSINT MCP.",
    )


class SecApkleaksSecretScanInput(BaseModel):
    """Parameters for APKLeaks automated cloud credential harvesting."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    apk_path: str | None = Field(default=None, description="Optional filesystem path to APK.")
    content_strings: list[str] | None = Field(
        default=None, description="Optional strings to evaluate."
    )
    min_entropy: float = Field(
        default=2.5, ge=0.0, le=8.0, description="Minimum Shannon entropy threshold."
    )


class SecSensitiveApiTaintTraceInput(BaseModel):
    """Parameters for sensitive API call-graph and privacy taint flow tracing."""

    project_id: str | None = Field(default=None, description="Optional target project ID.")
    artifact_id: str | None = Field(default=None, description="Optional target artifact ID.")
    enforce_strict_gdpr: bool = Field(
        default=True, description="Strictly flag unconsented third-party data transmission."
    )


class SecMastgProcedureRunInput(BaseModel):
    """Parameters for automated OWASP MASTG verification test runner."""

    test_ids: list[str] | None = Field(
        default=None, description="Optional list of MASTG-TEST-* IDs to execute."
    )
    target_package: str | None = Field(
        default=None, description="Target package name being verified."
    )
    static_properties: dict[str, Any] | None = Field(
        default=None, description="Optional static configuration properties."
    )


class SecArchDiagramRenderInput(BaseModel):
    """Parameters to render interactive architecture & taint flow diagram."""

    project_id: str | None = Field(default=None, description="Optional project ID.")
    apk_path: str | None = Field(default=None, description="Optional path to APK file.")
    title: str = Field(
        default="APK Architecture & Data-Flow Taint Graph",
        description="Diagram title header.",
    )
    theme: str = Field(default="dark", description="Visual theme (dark, light).")
    include_taint_flows: bool = Field(
        default=True, description="Include upstream/downstream taint exfiltration paths."
    )
    output_path: str | None = Field(
        default=None, description="Optional filesystem path to save standalone HTML diagram."
    )


class SecSourceCodeReviewInput(BaseModel):
    """Parameters to execute hybrid AST & semantic security source code review."""

    source_dir: str | None = Field(
        default=None, description="Directory path containing decompiled Java/Kotlin sources."
    )
    file_paths: list[str] | None = Field(
        default=None, description="Specific Java/Kotlin source file paths to audit."
    )
    ruleset: str = Field(
        default="all", description="Rule filter (all, crypto, network, sqli, reflection)."
    )
    severity_threshold: str = Field(
        default="low", description="Minimum finding severity threshold."
    )
    max_findings: int = Field(default=50, ge=1, le=500, description="Maximum findings to report.")


class SecRaspSignatureScanInput(BaseModel):
    """Parameters to scan Smali and native libraries for RASP and anti-tamper checks."""

    target_path: str = Field(
        min_length=1, description="Path to APK file or decompiled source/smali directory."
    )
    deep_native_scan: bool = Field(
        default=True, description="Scan native .so shared libraries for symbols and strings."
    )
    frameworks: list[str] | None = Field(
        default=None,
        description="Optional filter for frameworks (freerasp, promon, dexguard, rootbeer).",
    )


# --- Tool Spec Helper ---


def _sec_spec(
    *,
    name: str,
    title: str,
    description: str,
    handler: Any,
    input_model: type[BaseModel],
    profiles: frozenset[str] = CORE,
    scopes: frozenset[str] = frozenset({PROJECT_READ, STATIC_READ}),
    read_only: bool = True,
    idempotent: bool = True,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        title=title,
        description=description,
        input_model=input_model,
        handler=handler,
        family="security",
        profiles=profiles,
        scopes=scopes,
        annotations=ToolAnnotations(read_only=read_only, idempotent=idempotent),
        cost="fast",
    )


# --- Handlers ---


async def _security_scan_static(ctx: ToolContext, args: SecurityScanStaticInput) -> ToolOutcome:
    findings = ctx.runtime.security.scan_static(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        categories=args.categories,
    )
    return ToolOutcome(
        data={"count": len(findings), "findings": [f.model_dump(mode="json") for f in findings]}
    )


async def _security_get_findings(ctx: ToolContext, args: SecurityGetFindingsInput) -> ToolOutcome:
    payload = ctx.runtime.security.get_findings(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        severity=args.severity,
        masvs_category=args.masvs_category,
        limit=args.limit,
        offset=args.offset,
    )
    return ToolOutcome(data=payload)


async def _security_find_secret_locations(
    ctx: ToolContext, args: SecurityFindSecretsInput
) -> ToolOutcome:
    secrets = ctx.runtime.security.find_secrets(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        include_redacted=args.include_redacted,
    )
    return ToolOutcome(
        data={"count": len(secrets), "secrets": [s.model_dump(mode="json") for s in secrets]}
    )


async def _privacy_data_flows(ctx: ToolContext, args: PrivacyDataFlowsInput) -> ToolOutcome:
    flows = ctx.runtime.security.analyze_privacy(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        pii_type=args.pii_type,
    )
    return ToolOutcome(
        data={"count": len(flows), "flows": [f.model_dump(mode="json") for f in flows]}
    )


async def _sdk_inventory(ctx: ToolContext, args: SdkInventoryInput) -> ToolOutcome:
    sdks = ctx.runtime.security.get_sdks(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        category=args.category,
    )
    return ToolOutcome(data={"count": len(sdks), "sdks": [s.model_dump(mode="json") for s in sdks]})


async def _sbom_generate(ctx: ToolContext, args: SbomGenerateInput) -> ToolOutcome:
    doc = ctx.runtime.security.generate_sbom_doc(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        format_type=args.format,
    )
    exported = ctx.runtime.security.export_sbom(doc)
    return ToolOutcome(
        data={"format": doc.format, "components_count": len(doc.components), "document": exported}
    )


async def _vulnerability_scan(ctx: ToolContext, args: VulnerabilityScanInput) -> ToolOutcome:
    vulns = ctx.runtime.security.scan_vulns(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        min_severity=args.min_severity,
    )
    return ToolOutcome(
        data={"count": len(vulns), "vulnerabilities": [v.model_dump(mode="json") for v in vulns]}
    )


async def _yara_scan(ctx: ToolContext, args: YaraScanInput) -> ToolOutcome:
    results = ctx.runtime.security.scan_yara_rules(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        rules_path=args.rules_path,
        rule_names=args.rule_names,
    )
    return ToolOutcome(
        data={"count": len(results), "matches": [r.model_dump(mode="json") for r in results]}
    )


async def _capa_scan(ctx: ToolContext, args: CapaScanInput) -> ToolOutcome:
    caps = ctx.runtime.security.scan_capa_capabilities(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        rules_path=args.rules_path,
    )
    return ToolOutcome(
        data={"count": len(caps), "capabilities": [c.model_dump(mode="json") for c in caps]}
    )


async def _quark_score(ctx: ToolContext, args: QuarkScoreInput) -> ToolOutcome:
    score_report = ctx.runtime.security.score_quark_risk(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data=score_report.model_dump(mode="json"))


async def _ioc_extract(ctx: ToolContext, args: IocExtractInput) -> ToolOutcome:
    iocs = ctx.runtime.security.extract_ioc_list(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data={"count": len(iocs), "iocs": [i.model_dump(mode="json") for i in iocs]})


async def _ioc_export(ctx: ToolContext, args: IocExportInput) -> ToolOutcome:
    rendered = ctx.runtime.security.export_ioc_report(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        format_type=args.format,
    )
    return ToolOutcome(data={"format": args.format, "content": rendered})


async def _sample_enrich(ctx: ToolContext, args: SampleEnrichInput) -> ToolOutcome:
    report = ctx.runtime.security.enrich(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        provider=args.provider,
        user_consent=args.user_consent,
    )
    return ToolOutcome(data=report.model_dump(mode="json"))


async def _sec_play_protect_audit(ctx: ToolContext, args: PlayProtectAuditInput) -> ToolOutcome:
    report = ctx.runtime.security.audit_play_protect(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data=report)


async def _sec_dcl_detect(ctx: ToolContext, args: DclDetectInput) -> ToolOutcome:
    report = ctx.runtime.security.detect_dcl(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data=report)


async def _sec_mobsf_rule_scan(ctx: ToolContext, args: MobSfRuleScanInput) -> ToolOutcome:
    report = ctx.runtime.security.scan_mobsf_rules(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data=report)


async def _sec_cvss_scorecard_generate(ctx: ToolContext, args: CvssScorecardInput) -> ToolOutcome:
    report = ctx.runtime.security.generate_cvss_scorecard_report(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data=report)


async def _sec_sarif_export(ctx: ToolContext, args: SarifExportInput) -> ToolOutcome:
    report = ctx.runtime.security.export_sarif_report(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data=report)


async def _sec_stride_model(ctx: ToolContext, args: StrideModelInput) -> ToolOutcome:
    report = ctx.runtime.security.model_stride(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data=report)


async def _sec_poc_generate(ctx: ToolContext, args: PocGenerateInput) -> ToolOutcome:
    poc = ctx.runtime.security.generate_poc(
        finding_id=args.finding_id,
        title=args.title,
        target_package=args.target_package,
        component=args.component,
        parameter=args.parameter,
    )
    return ToolOutcome(data=poc)


async def _sec_intent_redirection_scan(
    ctx: ToolContext, args: IntentRedirectionScanInput
) -> ToolOutcome:
    findings = ctx.runtime.security.scan_intent_redirection(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data={"count": len(findings), "findings": findings})


async def _sec_pending_intent_audit(ctx: ToolContext, args: PendingIntentAuditInput) -> ToolOutcome:
    findings = ctx.runtime.security.scan_pending_intents(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data={"count": len(findings), "findings": findings})


async def _sec_aidl_auth_audit(ctx: ToolContext, args: AidlAuthAuditInput) -> ToolOutcome:
    findings = ctx.runtime.security.audit_aidl_auth(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
    )
    return ToolOutcome(data={"count": len(findings), "findings": findings})


async def _sec_poc_validate(ctx: ToolContext, args: PocValidateInput) -> ToolOutcome:
    res = ctx.runtime.security.validate_poc(
        vuln_type=args.vuln_type,
        target_package=args.target_package,
        target_component=args.target_component,
        poc_script=args.poc_script,
        intent_action=args.intent_action,
        intent_data=args.intent_data,
        intent_extra=args.intent_extra,
        manifest_xml=args.manifest_xml,
    )
    return ToolOutcome(data=res)


async def _sec_masvs_audit(ctx: ToolContext, args: SecMasvsAuditInput) -> ToolOutcome:
    res = ctx.runtime.security.audit_masvs(
        findings=args.findings,
        manifest_xml=args.manifest_xml,
        is_debuggable=args.is_debuggable,
        uses_cleartext=args.uses_cleartext,
        is_minified=args.is_minified,
        has_root_detection=args.has_root_detection,
    )
    return ToolOutcome(data=res)


async def _copilot_suggest_next(ctx: ToolContext, args: CopilotSuggestNextInput) -> ToolOutcome:
    res = ctx.runtime.security.copilot_suggest(
        user_goal=args.user_goal,
        detected_frameworks=args.detected_frameworks,
        manifest_summary=args.manifest_summary,
        findings_summary=args.findings_summary,
    )
    return ToolOutcome(data=res)


async def _sec_bugbounty_report_format(
    ctx: ToolContext, args: SecBugbountyReportFormatInput
) -> ToolOutcome:
    res = ctx.runtime.security.format_bugbounty_report(
        title=args.title,
        vulnerability_type=args.vulnerability_type,
        severity=args.severity,
        target=args.target,
        description=args.description,
        steps_to_reproduce=args.steps_to_reproduce,
        impact=args.impact,
        platform=args.platform,
        cvss_vector=args.cvss_vector,
        remediation=args.remediation,
        poc_code=args.poc_code,
    )
    return ToolOutcome(data=res)


async def _sec_leaked_email_intel(ctx: ToolContext, args: SecLeakedEmailIntelInput) -> ToolOutcome:
    if args.mode == "offline":
        res = ctx.runtime.security.check_leaked_emails(emails=args.emails)
        return ToolOutcome(data=res)

    granted = ctx.project.scopes if ctx.project is not None else ()
    decision = ctx.runtime.policy.evaluate((NETWORK_OSINT,), granted)
    if not decision.allowed:
        raise PolicyDeniedError(
            "Live email OSINT requires the 'network.osint' project scope.",
            hint=decision.reason,
            details={"missing_scopes": sorted(decision.missing)},
        )

    if args.mode == "openosint":
        remote = await ctx.runtime.mcp_mesh.call_remote_tool(
            "openosint",
            "email_lookup",
            {"emails": args.emails},
            timeout_seconds=30.0,
        )
        return ToolOutcome(
            data={
                "status": "EMAIL_INTEL_COMPLETE",
                "mode": "openosint",
                "total_emails": len(args.emails),
                "remote_result": remote,
            }
        )

    from raa.services.api.cti_intel import check_leaked_email_intel_async

    res = await check_leaked_email_intel_async(emails=args.emails, mode="holehe")
    warnings = res.pop("warnings", []) if isinstance(res.get("warnings"), list) else []
    return ToolOutcome(data=res, warnings=warnings)


async def _sec_apkleaks_secret_scan(
    ctx: ToolContext, args: SecApkleaksSecretScanInput
) -> ToolOutcome:
    apk_file = args.apk_path
    if not apk_file and args.project_id and args.artifact_id:
        art = ctx.runtime.artifacts.get_or_raise(args.project_id, args.artifact_id)
        apk_file = str(ctx.runtime.artifacts.path_for(art))
    res = ctx.runtime.security.scan_apkleaks(
        apk_path=apk_file,
        content_strings=args.content_strings,
        min_entropy=args.min_entropy,
    )
    return ToolOutcome(data=res)


async def _sec_sensitive_api_taint_trace(
    ctx: ToolContext, args: SecSensitiveApiTaintTraceInput
) -> ToolOutcome:
    res = ctx.runtime.security.trace_privacy_taint(
        project_id=args.project_id,
        artifact_id=args.artifact_id,
        enforce_strict_gdpr=args.enforce_strict_gdpr,
    )
    return ToolOutcome(data=res)


async def _sec_mastg_procedure_run(
    ctx: ToolContext, args: SecMastgProcedureRunInput
) -> ToolOutcome:
    res = ctx.runtime.security.run_mastg(
        test_ids=args.test_ids,
        target_package=args.target_package,
        static_properties=args.static_properties,
    )
    return ToolOutcome(data=res)


async def _sec_arch_diagram_render(
    ctx: ToolContext, args: SecArchDiagramRenderInput
) -> ToolOutcome:
    res = ctx.runtime.security.render_arch_diagram(
        project_id=args.project_id,
        apk_path=args.apk_path,
        title=args.title,
        theme=args.theme,
        include_taint_flows=args.include_taint_flows,
        output_path=args.output_path,
    )
    return ToolOutcome(data=res)


async def _sec_source_code_review(ctx: ToolContext, args: SecSourceCodeReviewInput) -> ToolOutcome:
    res = ctx.runtime.security.review_source_code(
        source_dir=args.source_dir,
        file_paths=args.file_paths,
        ruleset=args.ruleset,
        severity_threshold=args.severity_threshold,
        max_findings=args.max_findings,
    )
    return ToolOutcome(data=res)


async def _sec_rasp_signature_scan(
    ctx: ToolContext, args: SecRaspSignatureScanInput
) -> ToolOutcome:
    res = ctx.runtime.security.scan_rasp_signatures(
        target_path=args.target_path,
        deep_native_scan=args.deep_native_scan,
        frameworks=args.frameworks,
    )
    return ToolOutcome(data=res)


# --- Registration ---


def register(registry: CapabilityRegistry) -> None:
    """Register all Phase 9 security, privacy, and malware intelligence tools."""
    registry.register(
        _sec_spec(
            name="security_scan_static",
            title="Scan static security",
            description="Run static MASVS/MASTG security checks across manifest and code.",
            handler=_security_scan_static,
            input_model=SecurityScanStaticInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="security_get_findings",
            title="Get security findings",
            description="Retrieve paginated security findings with severity and MASVS filters.",
            handler=_security_get_findings,
            input_model=SecurityGetFindingsInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="security_find_secret_locations",
            title="Find secret locations",
            description="Locate embedded API keys and tokens with mandatory redaction.",
            handler=_security_find_secret_locations,
            input_model=SecurityFindSecretsInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="privacy_data_flows",
            title="Analyze privacy data flows",
            description="Identify sensitive PII transmission paths from APIs to sinks.",
            handler=_privacy_data_flows,
            input_model=PrivacyDataFlowsInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sdk_inventory",
            title="Inventory SDKs and trackers",
            description="Scan and catalog third-party SDKs and tracking services.",
            handler=_sdk_inventory,
            input_model=SdkInventoryInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sbom_generate",
            title="Generate SBOM",
            description="Generate standard CycloneDX 1.5 or SPDX 2.3 Software Bill of Materials.",
            handler=_sbom_generate,
            input_model=SbomGenerateInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="vulnerability_scan",
            title="Scan vulnerabilities",
            description="Correlate identified third-party components with CVE/OSV advisories.",
            handler=_vulnerability_scan,
            input_model=VulnerabilityScanInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="yara_scan",
            title="Scan YARA rules",
            description="Evaluate YARA signature rules over application packages.",
            handler=_yara_scan,
            input_model=YaraScanInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="capa_scan",
            title="Scan capa capabilities",
            description="Detect high-level offensive capabilities and ATT&CK for Mobile behaviors.",
            handler=_capa_scan,
            input_model=CapaScanInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="quark_score",
            title="Compute Quark score",
            description="Calculate Android behavioral risk ratings according to Quark rules.",
            handler=_quark_score,
            input_model=QuarkScoreInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="ioc_extract",
            title="Extract IOCs",
            description="Harvest Indicators of Compromise (IPs, domains, URLs) from evidence.",
            handler=_ioc_extract,
            input_model=IocExtractInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="ioc_export",
            title="Export IOCs",
            description="Export Indicators of Compromise as JSON, CSV, or STIX 2.1 bundle.",
            handler=_ioc_export,
            input_model=IocExportInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ, EXPORT_RAW}),
            read_only=False,
            idempotent=False,
        )
    )
    registry.register(
        _sec_spec(
            name="sample_enrich",
            title="Enrich sample intelligence",
            description="Query external threat intelligence feeds (consent-gated).",
            handler=_sample_enrich,
            input_model=SampleEnrichInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ, LLM_EXTERNAL}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_play_protect_audit",
            title="Google Play Protect Pre-Flight Audit",
            description=(
                "Audit APK against Google Play Protect malware heuristics, "
                "permissions, and developer policies."
            ),
            handler=_sec_play_protect_audit,
            input_model=PlayProtectAuditInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_dcl_detect",
            title="Dynamic Code Loading Detection",
            description=(
                "Scan Smali bytecode and DEX strings for unverified Dynamic Code "
                "Loading (DCL) routines."
            ),
            handler=_sec_dcl_detect,
            input_model=DclDetectInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_mobsf_rule_scan",
            title="MobSF Static Security Rule Scan",
            description=(
                "Evaluate MobSF static vulnerability rule catalog against manifest "
                "and decompiled bytecode."
            ),
            handler=_sec_mobsf_rule_scan,
            input_model=MobSfRuleScanInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_cvss_scorecard_generate",
            title="CVSS v3.1 Risk Scorecard",
            description=(
                "Compute automated CVSS v3.1 risk scores and executive scorecard breakdown."
            ),
            handler=_sec_cvss_scorecard_generate,
            input_model=CvssScorecardInput,
            profiles=ADMIN,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_sarif_export",
            title="OASIS SARIF 2.1 Exporter",
            description=(
                "Export all security and compliance findings to standardized OASIS "
                "SARIF v2.1.0 format."
            ),
            handler=_sec_sarif_export,
            input_model=SarifExportInput,
            profiles=ADMIN,
            scopes=frozenset({PROJECT_READ, EXPORT_RAW}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_stride_model",
            title="Mobile STRIDE Threat Modeling",
            description=(
                "Model application vulnerabilities under STRIDE mapped to MITRE "
                "ATT&CK for Mobile technique IDs."
            ),
            handler=_sec_stride_model,
            input_model=StrideModelInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_poc_generate",
            title="Executable PoC Generator",
            description=(
                "Synthesize reproducible, non-destructive Proof-of-Concept exploit "
                "commands (ADB, Frida, HTTP)."
            ),
            handler=_sec_poc_generate,
            input_model=PocGenerateInput,
            profiles=CORE,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_intent_redirection_scan",
            title="Intent Redirection Taint Scan",
            description=(
                "Scan Smali bytecode for untrusted Intent forwarding without "
                "IntentSanitizer validation."
            ),
            handler=_sec_intent_redirection_scan,
            input_model=IntentRedirectionScanInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_pending_intent_audit",
            title="PendingIntent Mutability Audit",
            description=(
                "Detect implicit mutable PendingIntents susceptible to privilege "
                "escalation hijacking."
            ),
            handler=_sec_pending_intent_audit,
            input_model=PendingIntentAuditInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_aidl_auth_audit",
            title="AIDL & Bound Service Caller Verification",
            description=(
                "Audit Bound Services and AIDL stubs for spoofable package checks "
                "and missing caller UID verification."
            ),
            handler=_sec_aidl_auth_audit,
            input_model=AidlAuthAuditInput,
            profiles=CORE,
            scopes=frozenset({PROJECT_READ, STATIC_READ}),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_poc_validate",
            title="Autonomous Exploit PoC Validator",
            description=(
                "Validate non-destructive exploit Proof-of-Concepts (Intent injection, "
                "deep links) against exported component reachability and permissions."
            ),
            handler=_sec_poc_validate,
            input_model=PocValidateInput,
            profiles=CORE,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_masvs_audit",
            title="OWASP MASVS Compliance Audit",
            description=(
                "Evaluate application security posture against the 7 OWASP MASVS v2.0 "
                "domains and generate a prioritized remediation roadmap."
            ),
            handler=_sec_masvs_audit,
            input_model=SecMasvsAuditInput,
            profiles=CORE,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="copilot_suggest_next",
            title="Interactive Reversing Copilot",
            description=(
                "Recommend next reversing tools, parameters, and Frida hook snippets "
                "tailored to the analyst's high-level security goal."
            ),
            handler=_copilot_suggest_next,
            input_model=CopilotSuggestNextInput,
            profiles=CORE,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_bugbounty_report_format",
            title="Bug Bounty Report & VRT Formatter",
            description=(
                "Format security findings into platform-compliant Bug Bounty reports "
                "(HackerOne, Bugcrowd) with VRT mapping and CVSS scoring."
            ),
            handler=_sec_bugbounty_report_format,
            input_model=SecBugbountyReportFormatInput,
            profiles=ADMIN,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_leaked_email_intel",
            title="Developer Email OSINT Footprint",
            description=(
                "Reconnaissance check on developer emails across GitHub, Google, "
                "AWS, Atlassian, and Docker Hub."
            ),
            handler=_sec_leaked_email_intel,
            input_model=SecLeakedEmailIntelInput,
            profiles=CORE,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_apkleaks_secret_scan",
            title="APKLeaks Automated Cloud Credential Harvester",
            description=(
                "Mine Dalvik bytecode and assets for cloud credentials, API tokens, and "
                "secret URIs using Shannon entropy filtering and false-positive suppression."
            ),
            handler=_sec_apkleaks_secret_scan,
            input_model=SecApkleaksSecretScanInput,
            profiles=frozenset({"core", "dynamic", "full"}),
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_sensitive_api_taint_trace",
            title="Sensitive API Call-Graph & Privacy Taint Flow Tracer",
            description=(
                "Trace sensitive Android framework privacy APIs (IMEI, GPS, Contacts, Camera) "
                "to network/log sinks to audit GDPR and Play Store privacy policy compliance."
            ),
            handler=_sec_sensitive_api_taint_trace,
            input_model=SecSensitiveApiTaintTraceInput,
            profiles=frozenset({"core", "dynamic", "full"}),
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_mastg_procedure_run",
            title="Automated MASTG Verification Procedures & MAPT Test Runner",
            description=(
                "Execute formal OWASP MASTG verification procedures against MASVS controls, "
                "producing deterministic pass/fail compliance audit scorecards."
            ),
            handler=_sec_mastg_procedure_run,
            input_model=SecMastgProcedureRunInput,
            profiles=frozenset({"core", "dynamic", "full"}),
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_arch_diagram_render",
            title="Interactive Architecture & Taint Flow Diagram Render",
            description=(
                "Render standalone interactive HTML+SVG architecture diagrams with real-time "
                "node search, component filtering, and upstream/downstream taint tracking."
            ),
            handler=_sec_arch_diagram_render,
            input_model=SecArchDiagramRenderInput,
            profiles=ADMIN,
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_source_code_review",
            title="Hybrid AST & Semantic Decompiled Source Code Reviewer",
            description=(
                "Audit decompiled Java and Kotlin sources for subtle security flaws, insecure "
                "cryptography, TrustManagers, reflection, and SQL injection with code patches."
            ),
            handler=_sec_source_code_review,
            input_model=SecSourceCodeReviewInput,
            profiles=frozenset({"core", "full"}),
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
    registry.register(
        _sec_spec(
            name="sec_rasp_signature_scan",
            title="RASP & Tamper Detection Signature Scanner",
            description=(
                "Scan Smali, Java/Kotlin sources, and native ELF libraries for freeRASP, "
                "Promon, DexGuard, RootBeer, su binary paths, and anti-hooking traps."
            ),
            handler=_sec_rasp_signature_scan,
            input_model=SecRaspSignatureScanInput,
            profiles=frozenset({"core", "full"}),
            scopes=frozenset(),
            read_only=True,
            idempotent=True,
        )
    )
