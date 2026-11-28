# Specialized AI Agents and Reusable Skills Architecture

<p align="center">
  <img src="../images/raa.png" width="120" alt="RAA Logo">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Current_Release-v4.0.0_Production-success?style=flat-square" alt="Current Release: v4.0.0 Production">
  <img src="https://img.shields.io/badge/Total_Tools-379_Implemented-blue?style=flat-square" alt="Total Tools: 379 Implemented">
  <img src="https://img.shields.io/badge/Tests-740+_Passing-brightgreen?style=flat-square" alt="Tests: 740+ Passing">
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Protocol-2026--07--28-informational?style=flat-square" alt="Protocol: 2026-07-28">
  <img src="https://img.shields.io/badge/License-MIT-4c1?style=flat-square" alt="License: MIT">
</p>

This document defines the specialized AI agent roles, responsibilities, input/output contracts, tool access boundaries, and reusable skill packages implemented across **RAA (Reverse Android Anything)**.

---

## 1. Multi-Agent System Architecture

Rather than relying on a single monolithic agent that suffers from context window exhaustion and tool-call confusion, RAA v4.0.0 coordinates **18 Specialized Agents** (`ALL_SPECIALIZED_AGENTS` in `src/raa/services/agents/specialized_agents.py`) orchestrated by a primary **Coordinator Agent**:

```
                       ┌────────────────────────────┐
                       │     Coordinator Agent      │
                       │   (Orchestrator / Triage)  │
                       └──────────────┬─────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
┌────────▼────────┐          ┌────────▼────────┐          ┌────────▼────────┐
│ APK Analysis    │          │ UI Engineering  │          │ Security & Code │
│ Cluster         │          │ Cluster         │          │ Quality Cluster │
└────────┬────────┘          └────────┬────────┘          └────────┬────────┘
         │                            │                            │
 ├─ Framework Agent           ├─ UI Extraction Agent       ├─ Security Agent
 ├─ Java/Kotlin Agent         ├─ UI Reconstruction Agent   ├─ API Discovery Agent
 ├─ Native Binary Agent       ├─ UI Redesign Agent         ├─ Database Agent
 ├─ Flutter Agent             └─ Architecture Agent        └─ Validation Agent
 └─ React Native Agent
```

---

## 2. Roster of 14 Specialized Agents

### 2.1 APK Analysis Agent
- **Role:** Top-level package triage, container validation, manifest decoding, and component discovery.
- **Allowed Tools:** `manifest_*`, `artifact_*`, `package_*`, `project_*`.
- **Input Contract:** `project_id`, `artifact_id`.
- **Output Contract:** Package name, version, min/target SDK, declared permissions, exported activities, services, broadcast receivers, and content providers.

### 2.2 Framework Detection Agent
- **Role:** Identifies technology stacks, embedded runtimes, and hybrid engines.
- **Allowed Tools:** `framework_detect`, `framework_capabilities`, `flutter_assets`, `react_native_bundle`, `unity_assets`, `dotnet_assemblies`.
- **Input Contract:** `project_id`, `artifact_id`.
- **Output Contract:** Detected frameworks (Native Java/Kotlin, Flutter, React Native, Unity, Xamarin/.NET), primary runtime version, and asset manifest.

### 2.3 Java/Kotlin Reverse Engineering Agent
- **Role:** Deep decompilation, identifier deobfuscation, control flow analysis, and source recovery.
- **Allowed Tools:** `source_search`, `source_get_class`, `source_get_method`, `deobfuscate_suggest_names`, `graph_call_graph`.
- **Input Contract:** `project_id`, `class_name` or `method_signature`.
- **Output Contract:** Decompiled Java/Kotlin source code, recovered control structures, deobfuscation map, and cross-reference links.

### 2.4 Flutter Reverse Engineering Agent
- **Role:** Specialized Flutter analysis, Dart AOT snapshot reversing, string pool harvesting, and TLS unpinning.
- **Allowed Tools:** `flutter_assets`, `flutter_symbols`, `flutter_patch_tls`, `flutter_dump_strings`, `apk_patch`.
- **Input Contract:** `project_id`, `artifact_id`.
- **Output Contract:** Dart class hierarchy, method names, hardcoded strings, API routes, and patched APK for HTTPS interception.

### 2.5 React Native Analysis Agent
- **Role:** JavaScript bundle extraction, Hermes bytecode disassembly, source map recovery, and native bridge inspection.
- **Allowed Tools:** `react_native_bundle`, `react_native_modules`, `artifact_extract_file`.
- **Input Contract:** `project_id`, `artifact_id`.
- **Output Contract:** Beautified JavaScript/TypeScript source code, registered React Native native modules, and UI component definitions.

### 2.6 Native Binary Analysis Agent
- **Role:** Native C/C++ shared library (`.so`) disassembly, JNI function resolution, and Ghidra decompilation.
- **Allowed Tools:** `native_symbols`, `native_disassemble`, `native_decompile`, `native_jni_map`, `native_dependencies`.
- **Input Contract:** `project_id`, `artifact_id`, `library_name`.
- **Output Contract:** Disassembled functions, C pseudocode, exported/imported symbols, JNI function mappings (`Java_...`), and binary entropy scores.

### 2.7 API Discovery Agent
- **Role:** Identifies backend endpoints, models API interactions, clusters paths, and generates OpenAPI 3.1 specifications.
- **Allowed Tools:** `api_extract_endpoints`, `api_infer_models`, `api_synthesize_spec`, `api_export_postman`, `api_test_contract`.
- **Input Contract:** `project_id`, `artifact_id`, optional traffic captures.
- **Output Contract:** Complete OpenAPI 3.1 specification, Postman collection, endpoint inventory, and authentication schema models.

### 2.8 Database & Storage Analysis Agent
- **Role:** Inspects local databases, Room entities, SharedPreferences, and file storage.
- **Allowed Tools:** `sqlite_schema`, `sqlite_query`, `dynamic_dump_storage`, `shared_prefs_inspect`.
- **Input Contract:** `project_id`, `artifact_id`.
- **Output Contract:** SQLite table schemas, entity relationships, default seed data, decoded SharedPreferences, and flagged sensitive keys.

### 2.9 UI Extraction Agent
- **Role:** Extracts raw UI assets, decoded XML layouts, Jetpack Compose composables, runtime view hierarchies, and webview DOMs.
- **Allowed Tools:** `ui_extract_layouts`, `ui_render_wireframe`, `ui_runtime_capture`, `ui_webview_inspect`, `artifact_list_files`.
- **Input Contract:** `project_id`, `artifact_id`, optional `device_id`.
- **Output Contract:** Hierarchical view trees with bounding boxes, extracted drawable/icon assets, layout XML strings, and high-res screen captures.

### 2.10 UI Reconstruction Agent
- **Role:** Synthesizes extracted visual and structural data into structured, framework-neutral screen models.
- **Allowed Tools:** `ui_render_wireframe`, `ui_code_generate`, `graph_query`.
- **Input Contract:** `project_id`, `screen_id`, extracted view hierarchy.
- **Output Contract:** Structured screen models, component trees, layout relationships, and navigation triggers.

### 2.11 UI Redesign Agent
- **Role:** Creates modern, clean-room reimplementations of original screens using the 8-point grid, 60/30/10 color rule, and thumb-zone optimization.
- **Allowed Tools:** `ui_redesign_generate`, `ui_visual_compare`, `mobile-app-ui-design` skill.
- **Input Contract:** `project_id`, `screen_id`, `target_framework` (`compose`, `react-native`, `tailwind`).
- **Output Contract:** Production-ready source code, extracted design tokens, visual similarity scores, and side-by-side comparison images.

### 2.12 Application Architecture Agent
- **Role:** Reconstructs high-level software architecture, module dependencies, state machines, and data-flow pipelines.
- **Allowed Tools:** `graph_query`, `graph_dependencies`, `graph_export`, `graph_call_graph`.
- **Input Contract:** `project_id`, `artifact_id`.
- **Output Contract:** C4 architecture diagram (Mermaid/GraphML), module dependency matrix, and activity navigation graph.

### 2.13 Security Analysis Agent
- **Role:** Audits applications against OWASP MASVS, searches for secrets, runs YARA/Quark rules, and traces PII data flows.
- **Allowed Tools:** `security_scan_static`, `security_get_findings`, `security_find_secret_locations`, `privacy_data_flows`, `quark_score`, `yara_scan`, `capa_scan`, `ioc_extract`.
- **Input Contract:** `project_id`, `artifact_id`.
- **Output Contract:** Evidence-backed MASVS compliance report, prioritized vulnerability list with severity rationale, secret locations, and extracted IOCs.

### 2.14 Code Quality and Validation Agent
- **Role:** Generates automated regression test suites, executes verification builds, and verifies behavioral equivalence before and after rebuilds.
- **Allowed Tools:** `test_generate`, `test_run`, `verify_behavior`, `agent_coverage_get`, `admin_engine_verify`.
- **Input Contract:** `project_id`, `base_artifact_id`, `patched_artifact_id`.
- **Output Contract:** Test execution report, coverage metrics, and behavioral divergence verification report.

### 2.15 Mobile Conversational Agent (`MobileAgent`, v4.0.0)
- **Role:** Operates two-way messaging over Telegram and WhatsApp, validates inbound requests via domain guard, orchestrates analysis pipelines, and delivers rebuilt APKs in chat.
- **Allowed Tools:** `channel_prompt_receive`, `channel_message_dispatch`, `channel_apk_deliver`, `channel_whitelist_manage`.

### 2.16 Toolchain & Binary Integrity Agent (`ToolchainAgent`, v4.0.0)
- **Role:** Autonomously monitors external dependencies, verifies SHA-256 binary integrity, provisions headless reversing runtimes, and manages runtime `PATH` lifecycles.
- **Allowed Tools:** `tool_manager_list`, `tool_manager_download`, `tool_manager_verify`, `tool_manager_auto_path`, `tool_manager_delete`, `tool_manager_status`.

### 2.17 Self-Evolution Agent (`EvolutionAgent`, v4.0.0)
- **Role:** Observes task execution anomalies, formulates dynamic bypass recipes, executes `skills.save`/`skills.patch` operations, and updates `.raa-workspace/memory/MEMORY.md`.
- **Allowed Tools:** `skills_procedure_save`, `skills_procedure_read`, `skills_procedure_patch`, `recipe_self_evolve`, `memory_lesson_learn`, `memory_lesson_query`.

### 2.18 Notification Cadence Agent (`CadenceAgent`, v4.0.0)
- **Role:** Monitors task velocity and milestone events, regulates interval updates (start/end, 1m, 2m, 5m, 10m, custom), and handles emergency CVE break-in alerts.
- **Allowed Tools:** `channel_intensity_configure`, `channel_intensity_get`.

---

## 3. Reusable Skills Catalog

RAA packages its most frequently used operational workflows into **23 Reusable Skills** in `skills/` compatible with Claude Code, Cursor, Codex CLI, OpenCode, and Antigravity:

| Skill ID | Name | Core Tools Used | Output Deliverables |
|:---|:---|:---|:---|
| `android-triage` | Single-Pass Android Triage | `artifact_ingest`, `manifest_get`, `framework_detect` | Rapid initial APK triage summary. |
| `platform-check` | Host Environment & Diagnostics | `doctor`, `admin_engine_verify`, `tool_manager_status` | Host dependencies and sidecar readiness report. |
| `report-and-export` | Report & Evidence Export | `report_generate`, `export_sarif`, `admin_sbom` | Executive Markdown, JSON, SARIF, and SBOM exports. |
| `raa-apk-triage` | Fast APK Triage & Discovery | `artifact_ingest`, `manifest_*`, `framework_detect` | Executive summary, tech stack, and risk profile. |
| `raa-source-reconstruct` | Source Code Reconstruction | `source_search`, `source_get_class`, `deobfuscate_suggest_names` | Clean decompiled Java/Kotlin classes with persistent names. |
| `raa-ui-redesign` | Mobile UI Extraction & Redesign | `ui_runtime_capture`, `ui_redesign_generate`, `ui_visual_compare` | Production Jetpack Compose / React Native screen code. |
| `raa-api-discovery` | API Reverse Engineering Studio | `api_extract_endpoints`, `api_synthesize_spec`, `api_export_postman` | OpenAPI 3.1 specification & Postman collection. |
| `raa-flutter-reversing` | Flutter Deep Reverse Engineering | `flutter_assets`, `flutter_patch_tls`, `flutter_dump_strings` | Dart classes, API URLs, and proxy-patched APK. |
| `raa-native-reversing` | Native Library & JNI Audit | `native_symbols`, `native_disassemble`, `native_decompile` | C pseudocode & JNI method bridge mappings. |
| `raa-security-audit` | OWASP MASVS & Privacy Audit | `security_scan_static`, `privacy_data_flows`, `quark_score` | Formatted markdown security report & STIX 2.1 IOCs. |
| `raa-app-store-compliance` | App Store & Google Play Pre-Submission Compliance | `security_scan_static`, `privacy_data_flows`, `quark_score`, `tool_manager_download` | Store rejection risk report, Data Safety / Privacy Manifest checks, and regulatory deadline alerts (`mjmirza/app-store-compliance`). |
| `raa-controlled-rebuild` | Controlled APK Patching & Rebuild | `apk_patch`, `apk_sign`, `verify_behavior`, `test_run` | Signed patched APK & behavioral verification report. |
| `raa-android-tv-studio` | Android TV & 10-Foot Living Canvas Studio | `tv_ui_redesign`, `visual_screendiff_verify`, `wireless_perf_benchmark` | Android TV Compose M3 screens, screendiff, and Perfetto trace. |
| `raa-cadence-controller` | Mobile Notification Cadence Controller | `channel_intensity_configure`, `channel_intensity_get` | Interval & urgency break-in cadence configuration. |
| `raa-mcp-mesh-manager` | Dynamic External MCP Mesh Manager | `mcp_mesh_connect`, `mcp_mesh_list`, `mcp_mesh_inspect`, `mcp_mesh_test` | Connected external MCP server inventory & health status. |
| `raa-mobile-agent` | Two-Way Mobile Agent (Telegram/WhatsApp) | `channel_prompt_receive`, `channel_message_dispatch`, `channel_apk_deliver` | Mobile chat execution & direct APK delivery. |
| `raa-nmap-vulners` | Nmap & Vulners Backend Recon | `api_list_operations`, `osint_*` | Backend host port & CVE vulnerability mapping. |
| `raa-self-evolving-recipes` | Self-Evolving Procedural Recipes | `skills_procedure_save`, `skills_procedure_patch`, `recipe_self_evolve` | Saved/patched procedural recipes & `MEMORY.md` lessons. |
| `raa-setup-wizard` | Interactive Setup & Onboarding Wizard | `open_setup_ui`, `setup_state_get`, `setup_skip_register` | Guided onboarding state & toolchain setup. |
| `raa-smap-recon` | Smap Passive Port & Service Recon | `api_list_operations`, `osint_*` | Passive Shodan-based host & service recon report. |
| `raa-toolchain-manager` | Dynamic Toolchain & Engine Manager | `tool_manager_list`, `tool_manager_download`, `tool_manager_verify` | Verified reversing binaries & auto-PATH configuration. |
| `raa-vault-guard` | Zero-Knowledge Vault & Content Shield | `vault_*`, `untrusted_content_wrap` | Redacted secret references & quarantined untrusted blocks. |
| `raa-wireless-device-gateway` | Wireless ADB & Wi-Fi Device Gateway | `wireless_device_connect`, `wireless_device_status`, `wireless_apk_push` | Cable-free Wi-Fi pairing, base64 APK push & port checks. |

---

## 4. Multi-Agent Coordination Protocol

When executing a complex macro-workflow (e.g., "Analyze this APK, extract its API, and redesign its checkout screen"):

1. **Coordinator Agent** receives the user goal, initializes the RAA project, ingests the APK, and invokes `raa-apk-triage`.
2. **Framework Detection Agent** identifies the runtime (e.g., Flutter + Native C++).
3. Coordinator spawns two parallel subagents:
   - **Flutter Reverse Engineering Agent** to patch TLS and harvest Dart endpoints.
   - **UI Extraction Agent** to capture the checkout activity screen hierarchy and screenshot.
4. **API Discovery Agent** synthesizes captured endpoints into an OpenAPI 3.1 spec.
5. **UI Redesign Agent** takes the extracted checkout screen model and generates a modern Jetpack Compose implementation following the 8-point grid.
6. **Code Quality and Validation Agent** generates contract tests and verifies coverage via `agent_coverage_get`.
7. Coordinator synthesizes all artifacts into a unified presentation for the user.
