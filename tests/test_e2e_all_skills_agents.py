"""Comprehensive End-to-End tests for all RAA Skills and Agent/Orchestrator modules.

Covers:
1. All 23 skills in skills/ (discovery, frontmatter, references, installation, Runtime info).
2. All 18 specialized agents (14 baseline + 4 v4.0.0) and CoverageTracker (+ agent_coverage_get tool).
3. SmartOrchestratorService (+ smart_orchestrate tool).
4. SwarmService (+ all 9 swarm/SOP/blackboard/edict/LoopX tools).
5. Autonomous GUI Agent (crawl_gui_agent).
6. CognitiveAuditService (+ all 9 cognitive/ADK/economics/RAG tools).
7. SelfEvolutionService (+ all 6 procedural memory/evolution tools).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from raa.errors import InvalidArgumentsError, NotFoundError
from raa.runtime import Runtime
from raa.services.agents import (
    ALL_SPECIALIZED_AGENTS,
    CadenceAgent,
    EvolutionAgent,
    MobileAgent,
    ToolchainAgent,
    get_specialized_agents,
)
from raa.services.gui_agent import (
    COMMON_ONBOARDING_BUTTONS,
    COMMON_PERMISSION_BUTTONS,
    crawl_gui_agent,
)
from raa.services.orchestrator import SmartOrchestratorService
from raa.services.skills import SkillService

EXPECTED_SKILL_IDS = {
    "android-triage",
    "platform-check",
    "raa-android-tv-studio",
    "raa-api-discovery",
    "raa-apk-triage",
    "raa-app-store-compliance",
    "raa-cadence-controller",
    "raa-controlled-rebuild",
    "raa-flutter-reversing",
    "raa-mcp-mesh-manager",
    "raa-mobile-agent",
    "raa-native-reversing",
    "raa-nmap-vulners",
    "raa-security-audit",
    "raa-self-evolving-recipes",
    "raa-setup-wizard",
    "raa-smap-recon",
    "raa-source-reconstruct",
    "raa-toolchain-manager",
    "raa-ui-redesign",
    "raa-vault-guard",
    "raa-wireless-device-gateway",
    "report-and-export",
}


# ---------------------------------------------------------------------------
# 1. Skills E2E (all 23 skills)
# ---------------------------------------------------------------------------


def test_e2e_all_23_skills_discover_validate_and_install(
    runtime: Runtime,
    tmp_path: Path,
) -> None:
    service = SkillService()
    discovered = service.discover()
    discovered_ids = {s.id for s in discovered}

    assert len(discovered) == 23
    assert discovered_ids == EXPECTED_SKILL_IDS

    # Runtime reports matching skill count with zero errors
    runtime_skills = runtime.info()["skills"]
    assert runtime_skills["count"] == 23
    assert runtime_skills["error"] is None

    install_root = tmp_path / "installed_skills"
    for skill in discovered:
        assert skill.name
        assert skill.description
        assert skill.version
        assert len(skill.tools) >= 1
        files = skill.files()
        assert "SKILL.md" in files

        # Verify SkillService.get and summary()
        fetched = service.get(skill.id)
        assert fetched.id == skill.id
        summary = fetched.summary()
        assert summary["id"] == skill.id
        assert summary["files"] == files

        # Verify SkillService.install copies SKILL.md and any references/
        written = service.install(skill.id, install_root)
        assert len(written) == len(files)
        for rel in files:
            assert (install_root / skill.id / rel).is_file()

    # Verify reference files specifically for skills that include references/
    assert (install_root / "android-triage" / "references" / "evidence-checklist.md").is_file()
    assert (install_root / "report-and-export" / "references" / "export-formats.md").is_file()

    # Verify error handling on invalid/missing skills
    with pytest.raises(InvalidArgumentsError):
        service.get("../bad-id")
    with pytest.raises(NotFoundError):
        service.get("nonexistent-skill-id")


# ---------------------------------------------------------------------------
# 2. Specialized Agents & CoverageTracker E2E
# ---------------------------------------------------------------------------


def test_e2e_specialized_agents_roster_and_v4_agents() -> None:
    agents = get_specialized_agents()
    assert agents is ALL_SPECIALIZED_AGENTS
    assert len(agents) == 18

    agent_ids = [a["id"] for a in agents]
    assert len(set(agent_ids)) == 18
    assert {"mobile_agent", "toolchain_agent", "evolution_agent", "cadence_agent"} <= set(agent_ids)

    # MobileAgent
    mobile = MobileAgent()
    m_res = mobile.process_mobile_request("telegram", "chat-42", "Triage sample.apk")
    assert m_res["agent"] == "MobileAgent"
    assert m_res["channel"] == "telegram"
    assert m_res["status"] == "orchestrating"

    # ToolchainAgent (missing + healthy)
    toolchain = ToolchainAgent()
    t_missing = toolchain.audit_toolchain(
        [{"tool_id": "jadx", "installed": True}, {"tool_id": "ghidra", "installed": False}]
    )
    assert t_missing["healthy"] is False
    assert t_missing["installed_count"] == 1
    assert t_missing["missing_count"] == 1
    assert any("ghidra" in rec for rec in t_missing["recommendations"])

    t_healthy = toolchain.audit_toolchain([{"tool_id": "jadx", "installed": True}])
    assert t_healthy["healthy"] is True
    assert t_healthy["missing_count"] == 0

    # EvolutionAgent
    evo = EvolutionAgent()
    e_res = evo.evolve_solution("anti-frida syscall trap", {"pkg": "com.example.app"})
    assert e_res["agent"] == "EvolutionAgent"
    assert e_res["action"] == "synthesize_recipe"
    assert e_res["confidence"] > 0.5

    # CadenceAgent
    cadence = CadenceAgent()
    c_info = cadence.evaluate_dispatch("decompile_progress", severity="info")
    assert c_info["is_urgent"] is False
    assert c_info["dispatch_action"] == "cadence_buffered"

    c_crit = cadence.evaluate_dispatch("cve_detected", severity="critical")
    assert c_crit["is_urgent"] is True
    assert c_crit["dispatch_action"] == "breakin_alert"


@pytest.mark.asyncio
async def test_e2e_coverage_tracker_and_tool(runtime: Runtime) -> None:
    project = runtime.projects.create(name="CoverageE2EApp", description="com.example.cov")

    # Initial coverage should be 0% with 4 open gaps
    initial_env = await runtime.invoke(
        "agent_coverage_get",
        {"project_id": project.id},
        profile="full",
        surface="test",
    )
    assert initial_env.data["overall_coverage_pct"] == 0.0
    assert len(initial_env.data["unresolved_gaps"]) == 4

    # Populate evidence across all 4 coverage dimensions
    runtime.evidence.add(
        project_id=project.id,
        kind="android_manifest",
        summary="Manifest with 2 activities",
        payload={"components": {"activities": ["MainActivity", "SettingsActivity"]}},
        source_tool="test",
    )
    runtime.evidence.add(
        project_id=project.id,
        kind="ui_runtime_capture",
        summary="Captured MainActivity",
        payload={},
        source_tool="test",
    )
    runtime.evidence.add(
        project_id=project.id,
        kind="screen_model",
        summary="Modeled SettingsActivity",
        payload={},
        source_tool="test",
    )
    runtime.evidence.add(
        project_id=project.id,
        kind="api_endpoints",
        summary="Found 2 API endpoints",
        payload={"endpoints": ["/v1/login", "/v1/profile"]},
        source_tool="test",
    )
    runtime.evidence.add(
        project_id=project.id,
        kind="api_synthesized_spec",
        summary="Synthesized OpenAPI 3.1 spec",
        payload={},
        source_tool="test",
    )
    runtime.evidence.add(
        project_id=project.id,
        kind="native_symbols",
        summary="Extracted native symbols",
        payload={},
        source_tool="test",
    )
    runtime.evidence.add(
        project_id=project.id,
        kind="flutter_strings",
        summary="Extracted Flutter strings",
        payload={},
        source_tool="test",
    )
    runtime.evidence.add(
        project_id=project.id,
        kind="screen_redesign",
        summary="Generated M3 redesign",
        payload={},
        source_tool="test",
    )
    runtime.evidence.add(
        project_id=project.id,
        kind="visual_comparison",
        summary="Verified visual diff",
        payload={},
        source_tool="test",
    )

    full_env = await runtime.invoke(
        "agent_coverage_get",
        {"project_id": project.id},
        profile="full",
        surface="test",
    )
    assert full_env.data["overall_coverage_pct"] == 100.0
    assert full_env.data["unresolved_gaps"] == []


# ---------------------------------------------------------------------------
# 3. SmartOrchestratorService E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_smart_orchestrator_service_and_tool(runtime: Runtime) -> None:
    orchestrator = SmartOrchestratorService()

    # Combined multi-domain plan
    combined = orchestrator.build_execution_plan(
        "triage android apk, redesign compose ui, discover api endpoints, inspect ios ipa, and notify telegram",
        mode="combined",
        target_path="target.apk",
        runtime=runtime,
    )
    assert combined["mode"] == "combined"
    assert combined["step_count"] >= 10
    assert len(combined["agent_roles"]) == 3
    assert len(combined["matched_skills"]) >= 1

    # Single-step mode truncates to 1 step
    single = orchestrator.build_execution_plan(
        "triage android apk and redesign ui",
        mode="single",
        runtime=runtime,
    )
    assert single["mode"] == "single"
    assert single["step_count"] == 1
    assert single["agent_roles"] == ["solo-agent"]

    # Fallback goal
    fallback = orchestrator.build_execution_plan("just check status", runtime=runtime)
    assert fallback["steps"][0]["name"] == "capabilities_get"

    # Invoke via MCP tool with Telegram notification
    env = await runtime.invoke(
        "smart_orchestrate",
        {
            "goal": "triage apk and redesign compose ui",
            "mode": "auto",
            "target_path": "demo.apk",
            "notify_channel": "telegram",
            "notify_recipient": "chat-999",
        },
        profile="full",
        surface="test",
    )
    assert env.data["mode"] == "combined"
    assert env.data["notification"] is not None


# ---------------------------------------------------------------------------
# 4. SwarmService E2E (all 9 swarm/SOP/blackboard/edict/LoopX tools)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_swarm_service_and_all_9_tools(runtime: Runtime) -> None:
    project = runtime.projects.create(name="SwarmE2E", description="com.example.swarm")

    # 1. swarm_org_govern
    org_env = await runtime.invoke(
        "swarm_org_govern",
        {"project_id": project.id, "swarm_name": "E2E Swarm"},
        profile="full",
        surface="test",
    )
    assert org_env.data["swarm_name"] == "E2E Swarm"
    assert len(org_env.data["roles"]) == 3
    assert runtime.swarm.get_org(project.id) is not None

    # 2. swarm_budget_meter (allow -> breach)
    b_ok = await runtime.invoke(
        "swarm_budget_meter",
        {
            "project_id": project.id,
            "tokens": 500,
            "cost_usd": 0.25,
            "subagent_name": "decompiler_worker",
            "set_token_cap": 1000,
            "set_cost_cap_usd": 1.0,
        },
        profile="full",
        surface="test",
    )
    assert b_ok.data["breached"] is False
    assert b_ok.data["enforcement_action"] == "allow"

    b_breach = await runtime.invoke(
        "swarm_budget_meter",
        {"project_id": project.id, "tokens": 600, "subagent_name": "decompiler_worker"},
        profile="full",
        surface="test",
    )
    assert b_breach.data["breached"] is True
    assert b_breach.data["enforcement_action"] == "block"

    # 3. subagent_deerflow_spawn
    sub_env = await runtime.invoke(
        "subagent_deerflow_spawn",
        {
            "project_id": project.id,
            "agent_name": "crypto_researcher",
            "mission_goal": "Locate AES key schedule",
            "steps": ["scan_strings", "trace_jni"],
        },
        profile="full",
        surface="test",
    )
    assert sub_env.data["status"] == "ready"
    assert len(sub_env.data["executed_steps"]) == 2
    assert Path(sub_env.data["scratchpad_path"]).is_file()

    # 4. memory_tideline_sync
    tl_env = await runtime.invoke(
        "memory_tideline_sync",
        {
            "project_id": project.id,
            "domain": "crypto",
            "entity_key": "aes_gcm_key",
            "attributes": {"bits": 256, "source": "libnative.so"},
        },
        profile="full",
        surface="test",
    )
    assert tl_env.data["total_domain_entities"] == 1
    assert tl_env.data["current_state"]["bits"] == 256

    # 5. sop_pipeline_execute (all 3 SOP templates)
    for sop_name in ("framework_audit", "api_key_extraction", "ui_reconstruction"):
        sop_env = await runtime.invoke(
            "sop_pipeline_execute",
            {
                "project_id": project.id,
                "sop_name": sop_name,
                "target_entity": "com.example.swarm",
            },
            profile="full",
            surface="test",
        )
        assert sop_env.data["status"] == "completed"
        assert sop_env.data["total_stages"] == 3

    # 6 & 7. swarm_blackboard_post & swarm_blackboard_read
    await runtime.invoke(
        "swarm_blackboard_post",
        {
            "project_id": project.id,
            "topic": "network",
            "author": "api_agent",
            "hypothesis": "Pinning bypassed via TrustManagerImpl",
            "confidence": 0.9,
        },
        profile="full",
        surface="test",
    )
    bb_read = await runtime.invoke(
        "swarm_blackboard_read",
        {"project_id": project.id, "topic": "network", "min_confidence": 0.8},
        profile="full",
        surface="test",
    )
    assert bb_read.data["count"] == 1
    assert bb_read.data["entries"][0]["author"] == "api_agent"

    # 8. swarm_edict_gate_evaluate (approved, review veto, execution veto)
    edict_ok = await runtime.invoke(
        "swarm_edict_gate_evaluate",
        {
            "project_id": project.id,
            "action_type": "static_scan",
            "draft_summary": "Read-only manifest scan",
            "risk_level": "low",
        },
        profile="full",
        surface="test",
    )
    assert edict_ok.data["approved"] is True

    edict_review_veto = await runtime.invoke(
        "swarm_edict_gate_evaluate",
        {
            "project_id": project.id,
            "action_type": "patch_apk",
            "draft_summary": "Modify payment check",
            "risk_level": "critical",
        },
        profile="full",
        surface="test",
    )
    assert edict_review_veto.data["approved"] is False
    assert edict_review_veto.data["veto_chamber"] == "Review Chamber"

    edict_exec_veto = await runtime.invoke(
        "swarm_edict_gate_evaluate",
        {
            "project_id": project.id,
            "action_type": "patch_apk",
            "draft_summary": "Safe verified patch",
            "risk_level": "high",
            "bypass_requested": True,
        },
        profile="full",
        surface="test",
    )
    assert edict_exec_veto.data["approved"] is False
    assert edict_exec_veto.data["veto_chamber"] == "Execution Chamber"

    # 9. loopx_goal_control_plane (full lifecycle)
    created = await runtime.invoke(
        "loopx_goal_control_plane",
        {"action": "create", "project_id": project.id, "title": "Full E2E Goal"},
        profile="full",
        surface="test",
    )
    goal_id = created.data["goal"]["goal_id"]

    await runtime.invoke(
        "loopx_goal_control_plane",
        {
            "action": "enqueue_attention",
            "project_id": project.id,
            "goal_id": goal_id,
            "attention_item": "inspect_deeplinks",
        },
        profile="full",
        surface="test",
    )
    stepped = await runtime.invoke(
        "loopx_goal_control_plane",
        {"action": "step", "project_id": project.id, "goal_id": goal_id},
        profile="full",
        surface="test",
    )
    assert stepped.data["active_step"] == 1
    assert stepped.data["processed_attention"] == "inspect_deeplinks"

    cp = await runtime.invoke(
        "loopx_goal_control_plane",
        {
            "action": "checkpoint",
            "project_id": project.id,
            "goal_id": goal_id,
            "checkpoint_data": {"note": "step1_ok"},
        },
        profile="full",
        surface="test",
    )
    assert cp.data["checkpoints_count"] == 1

    listed = await runtime.invoke(
        "loopx_goal_control_plane",
        {"action": "list", "project_id": project.id},
        profile="full",
        surface="test",
    )
    assert listed.data["count"] == 1


# ---------------------------------------------------------------------------
# 5. Autonomous GUI Agent E2E
# ---------------------------------------------------------------------------


def test_e2e_gui_agent_crawler() -> None:
    assert "Allow" in COMMON_PERMISSION_BUTTONS
    assert "Skip" in COMMON_ONBOARDING_BUTTONS

    res_bypass = crawl_gui_agent(
        target_package="com.example.flutterbank",
        max_steps=5,
        allow_permission_bypass=True,
    )
    assert res_bypass["status"] == "completed"
    assert res_bypass["steps_completed"] == 5
    assert len(res_bypass["bypassed_dialogs"]) == 2
    assert res_bypass["final_screen"] == "AccountsOverviewActivity"

    res_no_bypass = crawl_gui_agent(
        target_package="com.example.flutterbank",
        max_steps=3,
        allow_permission_bypass=False,
    )
    assert res_no_bypass["steps_completed"] == 3
    assert res_no_bypass["bypassed_dialogs"] == []


# ---------------------------------------------------------------------------
# 6. CognitiveAuditService E2E (all 9 cognitive tools)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_cognitive_audit_service_and_all_9_tools(runtime: Runtime) -> None:
    project = runtime.projects.create(name="CognitiveE2E", description="com.example.cog")

    # 1. audit_elephant_draft_spec
    spec = await runtime.invoke(
        "audit_elephant_draft_spec",
        {
            "project_id": project.id,
            "target_component": "BillingManager",
            "architecture_overview": "Handles Play Billing v6 purchase callbacks",
            "codebase_context": "class BillingManager { void onPurchasesUpdated() {} }",
            "claims": [{"id": "c1", "text": "Client-side receipt validation"}],
        },
        profile="full",
        surface="test",
    )
    assert spec.data["spec_id"].startswith("spec_")

    # 2. audit_goldfish_adversarial_review (confirmed, refuted, hallucination_flagged)
    g_conf = await runtime.invoke(
        "audit_goldfish_adversarial_review",
        {
            "project_id": project.id,
            "claim_id": "c1",
            "claim_text": "Local RSA verify",
            "isolated_evidence": ["Security.verifyPurchase() uses bundled public key"],
        },
        profile="full",
        surface="test",
    )
    assert g_conf.data["adversarial_verdict"] == "confirmed"

    g_ref = await runtime.invoke(
        "audit_goldfish_adversarial_review",
        {
            "project_id": project.id,
            "claim_id": "c2",
            "claim_text": "Remote RCE",
            "isolated_evidence": ["Finding was unverified and not reproducible"],
        },
        profile="full",
        surface="test",
    )
    assert g_ref.data["adversarial_verdict"] == "refuted"

    g_hal = await runtime.invoke(
        "audit_goldfish_adversarial_review",
        {
            "project_id": project.id,
            "claim_id": "c3",
            "claim_text": "Hidden backdoor",
            "isolated_evidence": [],
        },
        profile="full",
        surface="test",
    )
    assert g_hal.data["adversarial_verdict"] == "hallucination_flagged"

    # 3. adk_workflow_run
    adk = await runtime.invoke(
        "adk_workflow_run",
        {"project_id": project.id, "workflow_name": "e2e_adk_pipeline"},
        profile="full",
        surface="test",
    )
    assert adk.data["status"] == "completed"
    assert len(adk.data["steps_executed"]) == 4
    assert len(adk.data["opentelemetry_traces"]) == 4

    # 4. reasoning_strategy_select
    s_fast = await runtime.invoke(
        "reasoning_strategy_select",
        {"target": "simple.apk", "obfuscation_level": "low"},
        profile="full",
        surface="test",
    )
    assert s_fast.data["recommended_strategy"] == "fast_react"

    s_debate = await runtime.invoke(
        "reasoning_strategy_select",
        {
            "target": "packed.apk",
            "obfuscation_level": "packed",
            "has_native_crypto": True,
            "lines_of_code": 100_000,
        },
        profile="full",
        surface="test",
    )
    assert s_debate.data["recommended_strategy"] == "multi_agent_debate"

    # 5. fin_iap_billing_audit
    iap = await runtime.invoke(
        "fin_iap_billing_audit",
        {
            "project_id": project.id,
            "declared_permissions": ["com.android.vending.BILLING"],
            "decompiled_classes": ["com.example.cog.BillingClientWrapper"],
            "string_constants": ["verifyReceiptLocally", "onPurchasesUpdated"],
        },
        profile="full",
        surface="test",
    )
    assert "Google Play Billing Library" in iap.data["sdk_detected"]
    assert iap.data["client_side_validation_found"] is True
    assert iap.data["unverified_receipt_handling"] is True
    assert iap.data["monetization_risk_score"] >= 9.0

    # 6. exploit_payoff_simulate
    payoff = await runtime.invoke(
        "exploit_payoff_simulate",
        {
            "vulnerability_id": "VULN-1",
            "vulnerability_title": "Unverified IAP Unlock",
            "severity": "critical",
            "attacker_skill_required": "script_kiddie",
            "exploit_asset_type": "payment_bypass",
        },
        profile="full",
        surface="test",
    )
    assert payoff.data["economic_viability"] == "highly_lucrative"
    assert payoff.data["blast_radius"] == "enterprise_tenant"

    # 7. exec_briefing_synthesize
    brief = await runtime.invoke(
        "exec_briefing_synthesize",
        {
            "project_id": project.id,
            "app_name": "CognitiveE2E",
            "vulnerabilities": [{"id": "V1", "severity": "critical"}],
            "total_users": 50_000,
        },
        profile="full",
        surface="test",
    )
    assert brief.data["overall_risk_level"] == "critical"
    assert brief.data["financial_exposure_usd"] > 0

    # 8. sec_research_whitepaper_synthesize
    wp = await runtime.invoke(
        "sec_research_whitepaper_synthesize",
        {
            "project_id": project.id,
            "paper_title": "Bypassing Local Play Billing Verification",
            "vulnerability_mechanisms": ["Local RSA verification hook"],
            "cve_candidate": "CVE-2026-99999",
        },
        profile="full",
        surface="test",
    )
    assert wp.data["cve_candidate_id"] == "CVE-2026-99999"
    assert len(wp.data["literature_review_citations"]) == 3

    # 9. rag_haystack_query (after indexing documents on runtime.cognitive)
    indexed = runtime.cognitive.index_code_documents(
        project.id,
        {
            "BillingManager.java": "public void verifyReceiptLocally(String sig) { /* RSA */ }",
            "MainActivity.java": "protected void onCreate(Bundle b) {}",
        },
    )
    assert indexed == 2

    rag = await runtime.invoke(
        "rag_haystack_query",
        {"project_id": project.id, "query": "verifyReceiptLocally", "top_k": 3},
        profile="full",
        surface="test",
    )
    assert rag.data["total_matches"] >= 1
    assert rag.data["results"][0]["doc_id"] == "BillingManager.java"


# ---------------------------------------------------------------------------
# 7. SelfEvolutionService E2E (all 6 evolution tools)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_self_evolution_service_and_all_6_tools(runtime: Runtime) -> None:
    # 1. skills_procedure_save
    saved = await runtime.invoke(
        "skills_procedure_save",
        {
            "name": "e2e_ssl_unpin",
            "category": "bypass",
            "steps": ["Locate TrustManager", "Hook checkServerTrusted"],
            "target_fingerprint": "okhttp3",
            "description": "E2E SSL pinning bypass recipe",
        },
        profile="full",
        surface="test",
    )
    assert saved.data["status"] == "success"
    assert saved.data["version"] == 1
    assert Path(saved.data["memory_file"]).is_file()

    # 2. skills_procedure_read
    read_res = await runtime.invoke(
        "skills_procedure_read",
        {"name": "e2e_ssl_unpin"},
        profile="full",
        surface="test",
    )
    assert read_res.data["recipe"]["category"] == "bypass"

    # 3. skills_procedure_patch
    patched = await runtime.invoke(
        "skills_procedure_patch",
        {
            "name": "e2e_ssl_unpin",
            "updated_steps": ["Locate TrustManager", "Hook checkServerTrusted", "Hook BoringSSL"],
            "patch_reason": "Added native BoringSSL fallback",
        },
        profile="full",
        surface="test",
    )
    assert patched.data["new_version"] == 2
    assert patched.data["total_steps"] == 3

    # 4. recipe_self_evolve
    evolved = await runtime.invoke(
        "recipe_self_evolve",
        {
            "problem_description": "Custom DexGuard string encryption",
            "observed_anomaly": "encrypted_const_pool",
            "target_app": "com.example.guarded",
        },
        profile="full",
        surface="test",
    )
    assert evolved.data["status"] == "success"
    assert evolved.data["strategy"] == "adaptive_hook_synthesis"
    assert len(runtime.self_evolution.list_procedures()) >= 2

    # 5 & 6. memory_lesson_learn & memory_lesson_query
    learned = await runtime.invoke(
        "memory_lesson_learn",
        {
            "rule_title": "Always backup keystore",
            "instruction": "Copy release keystore before apksigner rotation.",
            "category": "safety",
        },
        profile="full",
        surface="test",
    )
    assert learned.data["status"] == "success"

    queried = await runtime.invoke(
        "memory_lesson_query",
        {"query": "keystore"},
        profile="full",
        surface="test",
    )
    assert queried.data["total_matches"] >= 1
    assert any("keystore" in m.lower() for m in queried.data["matched_lessons"])
