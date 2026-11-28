"""Smart Unified Orchestrator combining Tools, External MCP Mesh, Skills, and Agents."""

from __future__ import annotations

from typing import Any, Literal


class SmartOrchestratorService:
    """Plans and executes single or combined workflows across RAA tools, MCP peers, skills, and agents."""

    def build_execution_plan(
        self,
        goal: str,
        *,
        mode: Literal["auto", "single", "combined"] = "auto",
        target_path: str | None = None,
        runtime: Any | None = None,
    ) -> dict[str, Any]:
        low = goal.lower()
        ext = target_path.lower().rsplit(".", 1)[-1] if target_path and "." in target_path else ""

        steps: list[dict[str, Any]] = []
        if ext in {"apk", "aab", "xapk", "apks"} or any(
            k in low for k in ("apk", "android", "decompile", "triage")
        ):
            steps.extend(
                [
                    {
                        "kind": "tool",
                        "name": "artifact_ingest",
                        "reason": "Ingest mobile package into project",
                    },
                    {
                        "kind": "tool",
                        "name": "analysis_start",
                        "reason": "Run static DEX, manifest, and framework analysis",
                    },
                    {
                        "kind": "tool",
                        "name": "source_hybrid_search",
                        "reason": "Search decompiled code via Xerj MCP or DexIndex",
                    },
                    {
                        "kind": "skill",
                        "name": "raa-apk-triage",
                        "reason": "Apply structured APK triage checklist",
                    },
                ]
            )
        if ext in {"png", "jpg", "jpeg", "webp"} or any(
            k in low for k in ("ui", "design", "redesign", "compose", "screen")
        ):
            steps.extend(
                [
                    {
                        "kind": "tool",
                        "name": "ui_tree_screenshot_fuse",
                        "reason": "Fuse accessibility bounds with screenshot coordinates",
                    },
                    {
                        "kind": "tool",
                        "name": "ui_redesign_synthesize",
                        "reason": "Synthesize 8pt Material 3 Jetpack Compose UI",
                    },
                    {
                        "kind": "skill",
                        "name": "raa-ui-redesign",
                        "reason": "Apply Living Canvas UI modernization guidelines",
                    },
                ]
            )
        if any(k in low for k in ("ios", "iphone", "ipa")):
            steps.extend(
                [
                    {
                        "kind": "tool",
                        "name": "ios_ipa_inspect",
                        "reason": "Inspect IPA and Mach-O headers",
                    },
                    {
                        "kind": "mcp",
                        "server": "iphone-control",
                        "tool": "iphone_list_elements",
                        "reason": "Live iOS UI tree inspection",
                    },
                ]
            )
        if any(k in low for k in ("api", "osint", "recon", "endpoint", "email", "burp")):
            steps.extend(
                [
                    {
                        "kind": "tool",
                        "name": "api_backend_recon",
                        "reason": "Crawl extracted backend URLs for JS endpoints and keys",
                    },
                    {
                        "kind": "tool",
                        "name": "sec_leaked_email_intel",
                        "reason": "Check email OSINT footprint",
                    },
                    {
                        "kind": "mcp",
                        "server": "openosint",
                        "tool": "domain_recon",
                        "reason": "Passive domain/WHOIS enrichment",
                    },
                ]
            )
        if any(k in low for k in ("report", "whatsapp", "telegram", "notify")):
            steps.append(
                {
                    "kind": "tool",
                    "name": "channel_progress_report",
                    "reason": "Deliver progress report to mobile channel",
                }
            )

        if not steps:
            steps.append(
                {
                    "kind": "tool",
                    "name": "capabilities_get",
                    "reason": "Inspect active RAA capabilities",
                }
            )

        if mode == "single" and len(steps) > 1:
            steps = [steps[0]]

        matched_skills: list[str] = []
        if runtime is not None and hasattr(runtime, "skills"):
            for sk in runtime.skills.discover():
                name = str(getattr(sk, "id", getattr(sk, "name", "")))
                if any(
                    tok in name
                    for tok in ("triage", "ui", "api", "security", "android-tv")
                    if tok in low
                ):
                    matched_skills.append(name)

        return {
            "goal": goal,
            "mode": "single" if len(steps) == 1 else "combined",
            "step_count": len(steps),
            "steps": steps,
            "matched_skills": matched_skills,
            "agent_roles": ["triage-agent", "ui-architect", "api-auditor"]
            if len(steps) > 2
            else ["solo-agent"],
        }
