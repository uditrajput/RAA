import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from raa.runtime import build_registry
from raa.version import __version__

dump_path = ROOT / "tools_dump.json"
if dump_path.exists():
    with dump_path.open(encoding="utf-8") as f:
        tools = json.load(f)
else:
    reg = build_registry()
    tools = [
        {
            "name": s.name,
            "family": s.family,
            "title": s.title,
            "description": s.description,
            "profiles": sorted(s.profiles),
            "read_only": bool(getattr(s.annotations, "read_only_hint", not s.mutates_artifact)),
        }
        for s in sorted(reg.all(), key=lambda x: x.name)
    ]

# Define scenarios mapping based on tool families & purposes
family_scenarios = {
    "platform": {
        "title": "Core System Capabilities & Multi-Platform OS Inspection",
        "scenario": "Determining system health, active profile boundaries, and inspecting cross-platform binary packages (Android APK, iOS IPA/Mach-O, HarmonyOS HAP/ArkTS, PRoot Linux).",
        "test_scenario": "Test querying `/capabilities`, switching between execution profiles (`minimal` to `full`), and inspecting non-Android package targets.",
    },
    "admin": {
        "title": "Enterprise Administration, Audit Hash-Chains & ZTNA",
        "scenario": "Managing backend decompiler engines, verifying ZTNA gateway micro-perimeters, issuing CycloneDX/SPDX SBOMs, monitoring tenant quotas, and validating tamper seals.",
        "test_scenario": "Invoke administrative status endpoints with unauthorized tokens to ensure fail-closed policy enforcement; verify SHA-256 hash-chain integrity.",
    },
    "artifacts": {
        "title": "Artifact Ingestion, File Trees & Workspace Packaging",
        "scenario": "Ingesting raw mobile package binaries, unpacking internal file hierarchies, and tracking binary artifact lineages.",
        "test_scenario": "Ingest sample APK file; verify file hierarchy indexing and duplicate artifact hash deduplication.",
    },
    "analysis": {
        "title": "Static Analysis, Manifest Parsing, Permissions & Resource Parsing",
        "scenario": "Initial automated triage of APKs, decompiling binary XML (AXML), decoding Android resource tables (`resources.arsc`), and extracting permissions.",
        "test_scenario": "Parse malicious or obfuscated AndroidManifest.xml; assert extraction of exported components, deep links, and dangerous permissions.",
    },
    "source": {
        "title": "DEX Bytecode Decompilation & Class Representation",
        "scenario": "Retrieving Java/Smali class representations from multi-DEX archives, resolving deobfuscated cross-references, and decompiling WebAssembly bytecode.",
        "test_scenario": "Query complex obfuscated package path; assert JADX fallback pipeline deobfuscation and syntax generation.",
    },
    "framework": {
        "title": "Multi-Framework Fingerprinting (Flutter, React Native, Unity, Xamarin)",
        "scenario": "Autonomous detection of hybrid, cross-platform, or native mobile runtimes within application packages.",
        "test_scenario": "Feed APK containing Flutter libapp.so or React Native index.android.bundle; assert framework detected with confidence >= 0.95.",
    },
    "native": {
        "title": "Native ELF Shared Library Reversing & 16KB Page Alignment",
        "scenario": "Disassembling native ARM64 `.so` libraries, scanning for JNI exported signatures, and checking Android 15 16KB page alignment compatibility.",
        "test_scenario": "Analyze native binary with unaligned ELF segments; verify patch recommendation and exported symbol disassembly.",
    },
    "ui": {
        "title": "UI Screen Reconstruction, Compose Parity & Design Modernization",
        "scenario": "Extracting Android view hierarchies, converting legacy XML layouts to Jetpack Compose, Apple HIG audit, Liquid Glass shaders, and Bento grids.",
        "test_scenario": "Decompile XML layout; verify generated Jetpack Compose UI code compiles with semantic parity.",
    },
    "dynamic": {
        "title": "Dynamic Instrumentation, Frida Scripting & Live Device Telemetry",
        "scenario": "Interacting with physical/emulated devices, spawning Frida scripts, intercepting cryptographic operations, dumping memory, and bypassing RASP.",
        "test_scenario": "Connect to mock ADB device; verify Frida script injection, SSL unpinning interception, and memory dump receipt generation.",
    },
    "evidence": {
        "title": "Forensic Chain-of-Custody & Evidence Capture",
        "scenario": "Cryptographically recording reverse engineering findings, evidence strings, and code snippets into an immutable audit trail.",
        "test_scenario": "Submit security finding evidence; verify sha256 checksum, timestamp, and audit trail record generation.",
    },
    "recipes": {
        "title": "Automated Macro Workflows & End-to-End Triage Pipelines",
        "scenario": "Executing one-click comprehensive triage pipelines (full decompile -> secret search -> manifest audit -> report).",
        "test_scenario": "Execute `recipe_triage_complete`; verify pipeline aggregates DEX, manifest, secrets, and summary into a unified report.",
    },
    "skills": {
        "title": "Agent Skills Discovery & Marketplace Orchestration",
        "scenario": "Extending agent capabilities with modular SKILL.md bundles (OWASP checklist, iOS triage, API discovery).",
        "test_scenario": "Query available skills; verify skill metadata, prompt triggers, and execution tool bindings.",
    },
    "api": {
        "title": "API Endpoint Extraction, Traffic Interception & OpenAPI Synthesis",
        "scenario": "Extracting hardcoded REST/GraphQL URLs from decompiled code, intercepting live HTTP traffic via MITM/VPN, and synthesizing OpenAPI 3.1 specifications.",
        "test_scenario": "Scan decompiled source strings; verify extraction of REST endpoints, query parameters, and generation of OpenAPI schema.",
    },
    "unpacking": {
        "title": "Container Unpacking & Multi-APK Bundle Splitting",
        "scenario": "Extracting APK, AAB (Android App Bundle), XAPK, and APKM split packages into unified analysis workspaces.",
        "test_scenario": "Ingest multi-split APKM; verify merge into coherent unified DEX/assets structure.",
    },
    "diff": {
        "title": "Differential Binary, Manifest & Code Analysis",
        "scenario": "Comparing two versions of an application (v1 vs v2) to detect security patches, newly introduced attack surfaces, or regressions.",
        "test_scenario": "Run differential analysis between two APKs; verify output highlights added permissions, modified native libraries, and new endpoints.",
    },
    "security": {
        "title": "Vulnerability Scanning, OWASP MASTG & Hardcoded Secrets",
        "scenario": "Automated vulnerability scanning against OWASP Mobile Application Security Verification Standard (MASVS), MobSF rules, and API key harvesting.",
        "test_scenario": "Scan APK containing simulated hardcoded AWS/Stripe keys; assert severity CRITICAL and exact line-level references.",
    },
    "rebuild": {
        "title": "Controlled Smali Patching, Re-Alignment & v2/v3 Signing",
        "scenario": "Patching application bytecode or manifest, re-aligning ZIP boundaries for 16KB pages, and re-signing with valid v2/v3 APK signing blocks.",
        "test_scenario": "Modify AndroidManifest.xml (`android:debuggable=true`); recompile, zip-align, and sign; verify APK signature verification passes.",
    },
    "swarm": {
        "title": "Multi-Agent Swarm Governance & Shared Blackboard",
        "scenario": "Coordinating autonomous agent swarms (lead coordinator, security auditor, UI designer) with real-time token budgeting and shared memory.",
        "test_scenario": "Initialize swarm with 500k token budget; post findings to shared blackboard; verify subagent state synchronization.",
    },
    "cognitive": {
        "title": "Dual-Context Adversarial Reasoning (Elephant-Goldfish) & Game Theory",
        "scenario": "Simulating real-world adversarial attacks using game-theoretic payoff models and Dual-Context LLM architecture.",
        "test_scenario": "Run adversarial simulation on payment flow; verify QuantDinger exploit payoff matrix and defense recommendations.",
    },
    "binary": {
        "title": "Next-Gen Binary Decompilers (RetDec LLVM, Kuna Rust) & GDB/MI",
        "scenario": "Deep reverse engineering of stripped native libraries, interactive GDB debugging, and Apple iOS Mach-O Swift analysis.",
        "test_scenario": "Decompile stripped ARM64 ELF using LLVM IR recovery; verify function boundary detection and symbol reconstruction.",
    },
    "canvas": {
        "title": "Living Canvas UI, Shaders & Forensic Database Extraction",
        "scenario": "Reconstructing high-fidelity screens, generating GLSL shaders, analyzing SQLite databases, and driving automated Sodu CI/CD.",
        "test_scenario": "Extract encrypted SQLite database with provided passphrase; verify schema dump and forensic WAL reconstruction.",
    },
    "enterprise": {
        "title": "Enterprise MCP Mesh, Universal 7-CLI Gateway & WASM Sandboxes",
        "scenario": "Interconnecting RAA with Postman, GitHub, Playwright, and Nacos service meshes, running sandboxed WASM plugins, and dispatching to 7 coding CLIs.",
        "test_scenario": "Dispatch task via CLI gateway to Claude Code harness; verify WASM plugin execution within isolated boundary.",
    },
    "offensive": {
        "title": "Offensive Security, Yaklang HackSkills, GUI Computer-Use & Benchmark",
        "scenario": "Running automated penetration testing playbooks, 403 bypass mutations, operating desktop reversing GUIs (Ghidra, IDA), and certifying quality gates.",
        "test_scenario": "Trigger Yaklang BOLA playbook and 403 bypass mutator; verify non-destructive proof-of-concept verification receipt generation.",
    },
    "toolchain": {
        "title": "Dynamic Toolchain & Engine Lifecycle Management",
        "scenario": "Listing, downloading, SHA-256 verifying, auto-PATH injecting, and reclaiming disk space for external reversing engines (JADX, Apktool, Platform-Tools, Ghidra, Frida).",
        "test_scenario": "Verify tool listing, SHA-256 verification, runtime PATH injection, and safe deletion.",
    },
    "channels": {
        "title": "Two-Way Mobile Agent Channels & Notification Cadence",
        "scenario": "Receiving natural language prompts from Telegram/WhatsApp, enforcing domain guards, configuring cadence intervals, and delivering rebuilt APKs directly to mobile chat.",
        "test_scenario": "Send inbound mobile prompt; verify guard enforcement, cadence configuration, and APK delivery receipt.",
    },
    "setup": {
        "title": "Interactive First-Time Setup & Onboarding Console",
        "scenario": "Launching the embedded React/Tailwind setup wizard on loopback, persisting onboarding state, and handling skip/reopen requests.",
        "test_scenario": "Invoke open_setup_ui and setup_state_get; verify skip fallback and on-demand reopen.",
    },
    "evolution": {
        "title": "Self-Evolving Procedural Memory & Dynamic Skill Patching",
        "scenario": "Saving newly discovered reversing procedures, patching outdated recipes, and persisting negative/positive lessons in MEMORY.md.",
        "test_scenario": "Execute recipe_self_evolve and skills_patch_procedure; verify persistent memory update.",
    },
    "vault_shield": {
        "title": "Zero-Knowledge Secret Vault & Untrusted Content Shielding",
        "scenario": "Storing mobile test credentials outside LLM prompt context, wrapping untrusted decompiled strings in quarantine blocks, and managing live browser OAuth handoffs.",
        "test_scenario": "Store secret in vault and wrap untrusted payload; verify redaction and quarantine markers.",
    },
    "mcp_mesh": {
        "title": "Dynamic External MCP Connectors & Bidirectional App Mesh",
        "scenario": "Connecting, inspecting, health-probing, toggling, and disconnecting external stdio/SSE/streamable-http MCP servers with vault-injected credentials.",
        "test_scenario": "Register external MCP connector; verify tool discovery, health probe, and clean disconnect.",
    },
    "wireless_tv": {
        "title": "Wireless Device Gateway & Android TV 10-Foot Living Canvas Studio",
        "scenario": "Cable-free Wi-Fi ADB pairing and resilient base64 APK push, Android TV Compose M3 redesign, screendiff parity verification, and wireless Perfetto benchmarking.",
        "test_scenario": "Test wireless pairing/push, TV UI redesign synthesis, screendiff masking, and Perfetto trace slicing.",
    },
}

# Group tools by family
grouped_tools = {}
for t in tools:
    fam = t["family"]
    # Group micro-families into primary categories if needed
    mapped_fam = fam
    if fam in ["apple", "iot", "device"]:
        mapped_fam = "platform"
    elif fam in ["monetization", "economics"]:
        mapped_fam = "cognitive"
    elif fam in ["reporting", "documentation", "tui", "coworker", "workflow"]:
        mapped_fam = "canvas"
    elif fam in ["audit", "forensics"]:
        mapped_fam = "security"
    elif fam in ["scm", "browser", "osint", "harness", "governance", "sandbox"]:
        mapped_fam = "enterprise"
    elif fam in ["agents", "automation", "knowledge", "meta"]:
        mapped_fam = "swarm"
    elif fam in ["game"]:
        mapped_fam = "framework"
    elif fam in [
        "pentest",
        "computer_use",
        "orchestration",
        "safety",
        "exploit",
        "evaluation",
        "packaging",
        "compliance",
        "benchmark",
    ]:
        mapped_fam = "offensive"

    grouped_tools.setdefault(mapped_fam, []).append(t)

out_path = ROOT / "docs" / "TOOLS_INTEGRATION_AND_TEST_SCENARIOS.md"
with out_path.open("w", encoding="utf-8") as out:
    out.write("# RAA (Reverse Android Anything) — Tools Integration & Test Scenarios Matrix\n\n")
    out.write(f"> **System Version:** RAA v{__version__} Production  \n")
    out.write(f"> **Total Implemented Capabilities:** {len(tools)} Tools  \n")
    out.write(
        "> **Supported Profiles:** `minimal`, `core`, `dynamic`, `api`, `ui`, `admin`, `swarm`, `full`  \n\n"
    )
    out.write(
        f"This document provides an exhaustive reference of all **{len(tools)} tools integrated into RAA**, detailing:\n"
    )
    out.write(
        "1. **Tool Purpose & Requirement Case:** In which operational or security scenarios the tool is needed.\n"
    )
    out.write(
        "2. **Execution Profiles & Mutability:** Profile requirements and read-only annotations.\n"
    )
    out.write(
        "3. **End-to-End Test Case Scenarios:** Verification methodologies ensuring zero-defect production reliability.\n\n"
    )
    out.write("---\n\n")

    out.write("## Subsystem & Domain Index\n\n")
    for fam in sorted(grouped_tools.keys()):
        meta = family_scenarios.get(
            fam, {"title": fam.capitalize(), "scenario": "", "test_scenario": ""}
        )
        out.write(f"- [{meta['title']} ({len(grouped_tools[fam])} Tools)](#{fam}-tools)\n")
    out.write("\n---\n\n")

    for fam in sorted(grouped_tools.keys()):
        fam_tools = grouped_tools[fam]
        meta = family_scenarios.get(
            fam,
            {
                "title": fam.capitalize(),
                "scenario": "General analysis operations.",
                "test_scenario": "Standard input validation.",
            },
        )
        out.write(f"## {fam.capitalize()} Tools: {meta['title']}\n\n")
        out.write(f"**Total Tools:** {len(fam_tools)}  \n")
        out.write(f"**Operational Domain & Requirement:** {meta['scenario']}  \n")
        out.write(f"**Global Test Case Scenario:** {meta['test_scenario']}  \n\n")
        out.write(
            "| Tool Name | Title / Description | Profiles | Access Mode | Specific Test Scenario |\n"
        )
        out.write("|---|---|---|:---:|---|\n")

        for t in fam_tools:
            name_code = f"`{t['name']}`"
            title_desc = f"**{t['title']}**<br>{t['description']}".replace("|", "\\|")
            profs = ", ".join(t["profiles"])
            mode = "Read-Only" if t["read_only"] else "Mutating"
            test_desc = f"Verify {t['name']} handles valid and invalid inputs gracefully; assert return structure conforms to schema."
            out.write(f"| {name_code} | {title_desc} | `{profs}` | {mode} | {test_desc} |\n")
        out.write("\n")

print("Generated docs/TOOLS_INTEGRATION_AND_TEST_SCENARIOS.md successfully.")
