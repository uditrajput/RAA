# RAA (Reverse Android Anything) — Complete CLI Reference Guide

> **Platform:** Reverse Android Anything (RAA) v4.0.0 Production  
> **Total Available CLI Commands:** 345 commands  
> **Protocol Version:** 2026-07-28 | **Tool Equivalents:** 379 Tools

This document provides an exhaustive, production-grade reference for all 345 command-line commands across all 38 sub-apps in RAA.

Every CLI command is backed by the exact same capability registry and runtime models that power RAA's MCP, REST, and Python SDK surfaces.

## Table of Subcommand Groups

| Subcommand Group | Commands Count | Purpose & Domain |
|---|:---:|---|
| [`raa admin`](#admin-commands) | 13 | Engine catalogs, ZTNA gateways, quotas, and audit trails |
| [`raa ai`](#ai-commands) | 3 | On-device AI model extraction (TFLite, ONNX, PyTorch Mobile) |
| [`raa api`](#api-commands) | 24 | API endpoint discovery, OpenAPI schemas, and traffic capturing |
| [`raa artifact`](#artifact-commands) | 6 | Artifact ingestion, cataloguing, and binary file enumeration |
| [`raa binary`](#binary-commands) | 18 | Next-gen decompilers (RetDec LLVM, Kuna Rust), GDB/MI, and Apple Mach-O |
| [`raa canvas`](#canvas-commands) | 20 | Autonomous UI screen reconstruction, shaders, and Sodu CI/CD |
| [`raa channel`](#channel-commands) | 4 | Two-way mobile channels (Telegram, WhatsApp), cadence, and APK delivery |
| [`raa cognitive`](#cognitive-commands) | 9 | Dual-context adversarial audit and exploit payoff simulation |
| [`raa debloat`](#debloat-commands) | 3 | Subsystem commands |
| [`raa device`](#device-commands) | 8 | ADB device management, USB hardware, and screen mirrors |
| [`raa diff`](#diff-commands) | 4 | Binary, manifest, DEX, and permission differential comparison |
| [`raa dotnet`](#dotnet-commands) | 2 | Xamarin / .NET MAUI DLL assembly inspection |
| [`raa dynamic`](#dynamic-commands) | 46 | Frida hooks, memory dumps, network tracing, and dynamic fuzzer |
| [`raa enterprise`](#enterprise-commands) | 12 | Enterprise MCP mesh, universal 7-CLI dispatcher, Nacos, WASM |
| [`raa flutter`](#flutter-commands) | 7 | Flutter asset, symbol, BoringSSL pinning, and engine inspection |
| [`raa framework`](#framework-commands) | 2 | Framework detection and application capability querying |
| [`raa global`](#global-commands) | 12 | Core CLI bootstrap, status, doctor, setup wizard, report, manifest & permissions |
| [`raa graph`](#graph-commands) | 2 | AAIR dependency and cross-reference call graph querying |
| [`raa mcp-mesh`](#mcp-mesh-commands) | 7 | Dynamic external MCP server connectors, health probes, and vault injection |
| [`raa native`](#native-commands) | 4 | ELF shared library symbol extraction and ARM64 disassembly |
| [`raa offensive`](#offensive-commands) | 10 | Offensive security operations, Yaklang playbooks, and benchmarks |
| [`raa platform`](#platform-commands) | 7 | Multi-OS cross-platform target inspection (iOS, HarmonyOS, Linux) |
| [`raa project`](#project-commands) | 3 | Workspace project creation, lifecycle and scope inspection |
| [`raa react-native`](#react-native-commands) | 4 | React Native Hermes bytecode, bundle, and module inspection |
| [`raa rebuild`](#rebuild-commands) | 6 | Patching, re-alignment, and v2/v3 APK signing block synthesis |
| [`raa recipe`](#recipe-commands) | 3 | Multi-stage automated analysis and workflow macro execution |
| [`raa security`](#security-commands) | 33 | MASTG audits, Play Protect pre-flight, and vulnerability triage |
| [`raa serve`](#serve-commands) | 2 | MCP stdio / SSE and REST API daemon servers |
| [`raa skill`](#skill-commands) | 5 | Antigravity Agent Skills catalogue, install and execution |
| [`raa skills`](#skills-commands) | 5 | Self-evolving dynamic procedural skill saving, patching, and memory updates |
| [`raa source`](#source-commands) | 12 | DEX decompiler dispatch, class searching, and source recovery |
| [`raa swarm`](#swarm-commands) | 8 | Multi-agent swarm governance, token budgeting, and blackboard |
| [`raa test`](#test-commands) | 2 | Automated UI and unit testing harness runs |
| [`raa tools`](#tools-commands) | 7 | Tool discovery, schema inspection, toolchain management, and raw profile-scoped invocation |
| [`raa tv`](#tv-commands) | 3 | Android TV / Google TV 10-foot Living Canvas UI redesign and wireless Perfetto benchmarks |
| [`raa ui`](#ui-commands) | 21 | View hierarchies, Jetpack Compose, Apple HIG, and shaders |
| [`raa unity`](#unity-commands) | 3 | Unity il2cpp, metadata, and asset bundle extraction |
| [`raa unpack`](#unpack-commands) | 5 | APK/AAB/XAPK/APKM unpacking, extraction, and rebuilding |

---

## Admin Commands

**Group:** `raa admin` | **Total Commands:** 13

| Command | Description |
|---|---|
| `raa admin verify` | Verify engine pack manifest, integration mode, and binary hash integrity. |
| `raa admin audit` | Query append-only audit trail logs with filtering and pagination. |
| `raa admin engines` | List catalogued reverse engineering engines and availability. |
| `raa admin licenses` | Inventory of engines grouped by license and distribution class. |
| `raa admin coverage` | Compute reverse engineering and reconstruction coverage metrics. |
| `raa admin audit-verify` | Cryptographically verify the tamper-evident hash chain of the audit trail. |
| `raa admin sbom` | Generate standardized CycloneDX or SPDX Software Bill of Materials. |
| `raa admin backup` | Create a compressed .tar.gz backup bundle of a project. |
| `raa admin restore` | Restore an enterprise project from a backup bundle. |
| `raa admin retention` | Enforce data retention policy by pruning expired backups and temporary caches. |
| `raa admin metrics` | Display system observability metrics, database storage, and runtime telemetry. |
| `raa admin signature-verify` | Verify digital signature and cryptographic authenticity of skills, recipes, or files. |
| `raa admin ztna-config` | Generate Zero-Trust MCP Gateway configuration and agent client templates. |

## Ai Commands

**Group:** `raa ai` | **Total Commands:** 3

| Command | Description |
|---|---|
| `raa ai inspect-model` | Inspect on-device ML models (TFLite, LiteRT, ONNX) for operators and risks. |
| `raa ai extract-prompts` | Extract embedded LLM system prompts and RAG vector store configurations. |
| `raa ai appfunctions` | Discover Android 16 AppFunction declarations exposed to AI agents. |

## Api Commands

**Group:** `raa api` | **Total Commands:** 24

| Command | Description |
|---|---|
| `raa api capture-start` | Start an authorized API capture session. |
| `raa api capture-stop` | Stop an active API capture session and finalize recorded flows. |
| `raa api capture-status` | Query active or historical capture sessions. |
| `raa api flows` | List normalized, redacted API flows. |
| `raa api flow` | Retrieve a complete, normalized and redacted flow record. |
| `raa api cluster` | Cluster captured flows into stable HTTP operations. |
| `raa api operations` | List discovered API operations. |
| `raa api operation` | Get details of a clustered API operation. |
| `raa api infer` | Infer JSON/REST schemas across clustered operations. |
| `raa api generate-spec` | Generate and lint an OpenAPI 3.1 specification. |
| `raa api generate-client` | Generate typed client code and run compile/smoke tests. |
| `raa api test-contracts` | Run contract conformance tests against recorded flows or live endpoints. |
| `raa api diff` | Diff a candidate OpenAPI spec against the inferred baseline contract. |
| `raa api drift` | Get accumulated schema and contract drift findings. |
| `raa api export-har` | Export normalized and redacted flows as standard HAR 1.2 with _raa metadata. |
| `raa api synthesize` | Cluster routes and synthesize schemas into an OpenAPI 3.1 specification. |
| `raa api export-postman` | Export reverse-engineered routes to Postman Collection v2.1. |
| `raa api crawl-docs` | Harvest endpoints and schemas from API developer documentation. |
| `raa api audit-privacy` | Cross-audit remote privacy policy disclosures against APK permissions. |
| `raa api ip-intel` | Analyze backend IP addresses for ASN attribution, cloud hosting, and threat scores. |
| `raa api cti-check` | Check IP addresses and domains against CTI threat intelligence feeds. |
| `raa api semantic-waf` | Audit mobile API endpoint against SQLi, CMDi, NoSQLi, and Path Traversal via AST WAF. |
| `raa api bypass-403` | Generate 401/403 access control bypass mutations (headers, paths, verbs) via nomore403. |
| `raa api proxy-rotate` | Create a multi-region rotating cloud gateway proxy session to bypass rate limits (429). |

## Artifact Commands

**Group:** `raa artifact` | **Total Commands:** 6

| Command | Description |
|---|---|
| `raa artifact ingest` | Ingest an APK/AAB/APKS/XAPK into a project. |
| `raa artifact list` | List artifacts in a project. |
| `raa artifact files` | List archive members without extracting them. |
| `raa artifact playstore-info` | Fetch public Google Play Store metadata for an app. |
| `raa artifact playstore-download` | Download an Android app from Google Play Store via AVD Manager or fallback provider. |
| `raa artifact apkeep-download` | Download an Android app via efforg/apkeep (Google Play first priority). |

## Binary Commands

**Group:** `raa binary` | **Total Commands:** 18

| Command | Description |
|---|---|
| `raa binary kuna-decompile` | Decompile native binary via Kuna fast Rust decompiler. |
| `raa binary retdec-decompile` | Decompile native binary via RetDec LLVM decompilation backend. |
| `raa binary macho-demangle` | Demangle Swift/ObjC symbols and parse Mach-O headers via Malimite. |
| `raa binary swift-sections` | Parse Mach-O Swift reflection sections and metadata. |
| `raa binary objc-reconstruct` | Reconstruct Objective-C class interfaces and class-dump headers. |
| `raa binary gdb-session` | Automate native GDB/MI interactive debugging session. |
| `raa binary objdump-dwarf` | Inspect native disassembly and DWARF debug line numbers via llvm-objdump. |
| `raa binary rizin-bridge` | Bridge Rizin / Cutter headless for CFG graph extraction and radare2 analysis. |
| `raa binary ghidra-bridge` | Run Ghidra headless decompiler bridge with Java analysis scripts. |
| `raa binary iot-extract` | Extract embedded IoT firmware partitions, OTA blobs, and BLE keys from APK. |
| `raa binary lock-bypass` | Bypass lockscreen via ADB gesture/keyguard clearing. |
| `raa binary lock-bruteforce` | Perform dictionary/brute-force ADB lockscreen PIN test. |
| `raa binary ducky-payload` | Generate USB Rubber Ducky / BadUSB keystroke injection scripts for lockscreens. |
| `raa binary gatekeeper-clear` | Clear Android Gatekeeper/Locksettings credentials (root ADB required). |
| `raa binary xposed-hook` | Inject LSPosed / Xposed runtime hook to bypass KeyguardManager isDeviceLocked. |
| `raa binary nanobot-daemon` | Manage ultra-lightweight autonomous Nanobot background cron tasks. |
| `raa binary nanobot-notify` | Dispatch real-time chat alert notifications via Nanobot integrations. |
| `raa binary lastbook` | Query Lastbook air-gapped offline reversing cheat-sheets and specifications. |

## Canvas Commands

**Group:** `raa canvas` | **Total Commands:** 20

| Command | Description |
|---|---|
| `raa canvas stitch-modernize` | Modernize legacy Android XML layout into modern Compose/React Native via Google Stitch. |
| `raa canvas stitch-spec` | Export DESIGN.md design token and component catalog specifications. |
| `raa canvas hig-audit` | Audit mobile UI layout against Apple Human Interface Guidelines. |
| `raa canvas liquid-glass` | Synthesize modern Liquid Glass widget with authentic fragment shader blurs. |
| `raa canvas bento-grid` | Render Apple-inspired Bento Grid presentation cards for audit metrics. |
| `raa canvas clean-lint` | Refactor and lint decompiled code against Clean Architecture & DDD principles. |
| `raa canvas clean-spec` | Synthesize clean-room non-infringing functional specifications. |
| `raa canvas viewport-match` | Validate reconstructed layouts across phone, foldable, and tablet viewports. |
| `raa canvas tokens-extract` | Extract design palettes, typography scales, and spacing tokens into tokens.json. |
| `raa canvas unity-dump` | Extract Unity serialized assets, AssetBundles, and C# scripts from game APK. |
| `raa canvas godot-extract` | Unpack embedded Godot .pck archives and GDScript sources. |
| `raa canvas sqlite-forensics` | Forensically recover mobile SQLite tables, WAL journal records, and SQLCipher keys. |
| `raa canvas docmd-compile` | Compile workspace docs into single-source static portal and llms.txt context file. |
| `raa canvas skill-evolve` | Analyze session corrections to propose automated self-evolution prompt diffs. |
| `raa canvas coworker-dot` | Manage WebRTC audio/video session with persistent reversing coworker (RAA Dot). |
| `raa canvas ekko-pipeline` | Execute visual node-based reversing workflow graphs from Ekko Studio. |
| `raa canvas tui-codewhale` | Manage Codewhale high-performance terminal TUI session with subagent monitoring. |
| `raa canvas receipt-sign` | Generate SHA-256 HMAC cryptographic execution receipt for audit compliance. |
| `raa canvas sodu-cicd` | Execute closed-loop decompile-patch-build-verify pipeline with automated rollback. |
| `raa canvas gh-actions-gen` | Generate GitHub Actions CI/CD workflow YAML for Android building and v2/v3 signing. |

## Channel Commands

**Group:** `raa channel` | **Total Commands:** 4

| Command | Description |
|---|---|
| `raa channel test` | Send verification ping to configured Telegram or WhatsApp. |
| `raa channel pair` | Display terminal QR code for local WhatsApp Web pairing. |
| `raa channel intensity set` | Set cadence: start/end, 1m, 2m, 5m, 10m, or custom. |
| `raa channel intensity status` | Display active notification cadence and stats. |

## Cognitive Commands

**Group:** `raa cognitive` | **Total Commands:** 9

| Command | Description |
|---|---|
| `raa cognitive elephant-draft` | Draft full-context reversing specification using Elephant agent. |
| `raa cognitive goldfish-review` | Execute zero-context adversarial audit on proposed findings. |
| `raa cognitive adk-workflow` | Execute Google ADK Python state machine workflow with OpenTelemetry tracing. |
| `raa cognitive strategy-select` | Select optimal cognitive reasoning paradigm (Fast ReAct, Plan-Solve, Debate). |
| `raa cognitive iap-audit` | Audit In-App Purchase and monetization workflows for client-side bypasses. |
| `raa cognitive exploit-payoff` | Simulate quantitative exploit economics matrix via QuantDinger. |
| `raa cognitive exec-briefing` | Synthesize board-level executive risk summary and compliance impact. |
| `raa cognitive whitepaper` | Synthesize academic-grade vulnerability research whitepaper via Dr. Claw. |
| `raa cognitive haystack` | Query decompiled code repositories using Haystack hybrid RAG search. |

## Debloat Commands

**Group:** `raa debloat` | **Total Commands:** 3

| Command | Description |
|---|---|
| `raa debloat inspect` | Inspect Android packages and classify them with UAD safety tiers. |
| `raa debloat apply` | Preview or apply rootless ADB debloating with automatic backup and undo scripts. |
| `raa debloat restore` | Restore previously debloated packages from a JSON backup file. |

## Device Commands

**Group:** `raa device` | **Total Commands:** 8

| Command | Description |
|---|---|
| `raa device list` | List test devices and leases. |
| `raa device lease` | Lease a clean device exclusively for a project. |
| `raa device release` | Release a device and restore it to a clean baseline. |
| `raa device snapshot` | Create or restore a disposable device snapshot. |
| `raa device pair` | Pair Android device/TV over Wi-Fi (Android 11+ TLS). |
| `raa device connect` | Connect to Android device/TV over Wi-Fi (zero-binary). |
| `raa device status` | Check wireless device connection, battery and port state. |
| `raa device push-apk` | Install APK over Wi-Fi using resilient chunking. |

## Diff Commands

**Group:** `raa diff` | **Total Commands:** 4

| Command | Description |
|---|---|
| `raa diff compare` | Compare two artifacts and produce a semantic diff report. |
| `raa diff list` | List paginated changes from a diff comparison. |
| `raa diff get` | Inspect one specific change item in detail. |
| `raa diff export` | Export diff comparison as JSON, Markdown, or unified diff. |

## Dotnet Commands

**Group:** `raa dotnet` | **Total Commands:** 2

| Command | Description |
|---|---|
| `raa dotnet assemblies` | List managed .NET assemblies (DLLs) in the container. |
| `raa dotnet type` | Inspect or decompile a managed .NET type. |

## Dynamic Commands

**Group:** `raa dynamic` | **Total Commands:** 46

| Command | Description |
|---|---|
| `raa dynamic install` | Install an authorized application build APK onto a leased device. |
| `raa dynamic launch` | Launch an application package/activity on a leased device. |
| `raa dynamic stop` | Stop an application on a leased device. |
| `raa dynamic instrument-start` | Start reviewed instrumentation hooks on an application. |
| `raa dynamic instrument-stop` | Stop instrumentation and finalize session manifest. |
| `raa dynamic events` | Retrieve paginated, redacted runtime interception events. |
| `raa dynamic logcat` | Retrieve filtered and redacted logcat message stream. |
| `raa dynamic dump-dex` | Dump memory-mapped runtime DEX bytecode from process memory. |
| `raa dynamic dump-native` | Dump loaded native shared libraries from process memory. |
| `raa dynamic dump-heap` | Extract an HPROF memory dump from a running process. |
| `raa dynamic inject-gadget` | Embed Frida Gadget shared library into an APK for non-rooted dynamic instrumentation. |
| `raa dynamic dump-storage` | Extract internal SQLite databases and SharedPreferences XML from application sandbox. |
| `raa dynamic webview-cdp` | Attach to in-app WebView via Chrome DevTools Protocol. |
| `raa dynamic perfetto-record` | Record Perfetto system trace via ADB capturing thread scheduling and Binder IPC. |
| `raa dynamic perfetto-query` | Analyze Perfetto ftrace event logs to detect Binder IPC storms and ANR deadlocks. |
| `raa dynamic iot-sniffer` | Dissect and parse local multicast/broadcast IoT traffic (mDNS, SSDP, WS-Discovery). |
| `raa dynamic wireguard-start` | Establish zero-trust WireGuard capture tunnel on test device. |
| `raa dynamic wireguard-stop` | Tear down active WireGuard tunnel on device and restore routing. |
| `raa dynamic fleet-discover` | Discover wireless ADB devices across local subnets and orchestrate persistent connections. |
| `raa dynamic burp-bridge` | Configure bidirectional MCP bridge between Burp Suite and RAA. |
| `raa dynamic traffic-audit` | Passively analyze HTTP traffic flows for security flaws with PII redaction. |
| `raa dynamic p2p-tunnel` | Establish encrypted P2P NAT-traversal tunnel to remote Android device. |
| `raa dynamic virtual-display-start` | Create and start a headless Android VirtualDisplay session. |
| `raa dynamic virtual-display-stop` | Tear down and release an active headless VirtualDisplay session. |
| `raa dynamic gui-crawl` | Autonomously crawl Flutter/Canvas mobile apps using multimodal visual grounding. |
| `raa dynamic scrcpy-inject` | Inject low-latency input event via binary scrcpy control protocol. |
| `raa dynamic scrcpy-frame` | Capture low-latency video frame stream from SurfaceControl. |
| `raa dynamic state-verify` | Verify GUI agent state transitions against deterministic state schemas. |
| `raa dynamic rms-hook` | Generate pre-configured Frida hooks for Crypto, KeyStore, or SharedPreferences. |
| `raa dynamic rms-override` | Codelessly hook target Java method, logging arguments and overriding return value. |
| `raa dynamic lamda-connect` | Connect to on-device LAMDA agent daemon via WebRTC/gRPC. |
| `raa dynamic lamda-touch` | Dispatch kernel-level multi-touch gestures via LAMDA. |
| `raa dynamic docker-spawn` | Spawn ephemeral disposable containerized Android emulator sandbox. |
| `raa dynamic docker-teardown` | Tear down and purge containerized Docker Android sandbox. |
| `raa dynamic agent-control` | Dispatch protocol-driven agent actions for mobile automation. |
| `raa dynamic visual-diff` | Audit visual differences between UI screens with font and layout awareness. |
| `raa dynamic arm-translate` | Flash and configure ARM/ARM64 binary translation into x86/x86_64 emulators. |
| `raa dynamic gui-record` | Record human UI interactions or replay action graphs with boundary fuzzing. |
| `raa dynamic accessibility-agent` | Control standalone on-device Android Accessibility Service agent. |
| `raa dynamic qa-replay` | Replay QA test scenario with real-time telemetry and Perfetto trace slicing. |
| `raa dynamic appfunction-invoke` | Invoke or security-fuzz Android 16 AppFunctionDeclaration IPC endpoints. |
| `raa dynamic vpn-intercept` | Control transparent VPN interception, proxy forwarding, and CA cert injection. |
| `raa dynamic rasp-bypass` | Generate and deploy targeted Frida RASP and anti-tamper hooks. |
| `raa dynamic device-mutate` | Mutate device runtime properties (dark mode, battery, network, display) for chaos tests. |
| `raa dynamic shizuku-exec` | Execute privileged operations without root using Shizuku Binder IPC or rish. |
| `raa dynamic termux-bundle` | Deploy, list, execute, or clean standalone on-device ARM64 analysis binaries. |

## Enterprise Commands

**Group:** `raa enterprise` | **Total Commands:** 12

| Command | Description |
|---|---|
| `raa enterprise postman-run` | Execute Postman API collection and assertions via Postman MCP. |
| `raa enterprise postman-assert` | Validate API endpoint responses against expected security contracts. |
| `raa enterprise github-pr` | Manage Git repositories and open Pull Requests via GitHub MCP. |
| `raa enterprise playwright-webview` | Control in-app WebViews and intercept OAuth tokens via Playwright MCP. |
| `raa enterprise apify-scrape` | Scrape Google Play and App Store intelligence via Apify MCP. |
| `raa enterprise cli-dispatch` | Dispatch tasks to external coding CLIs via unified 7-CLI gateway. |
| `raa enterprise omnigent-enforce` | Validate and enforce fail-closed security and budget policies via Omnigent. |
| `raa enterprise nacos-register` | Register RAA MCP tool capabilities into enterprise Nacos service registries. |
| `raa enterprise n8n-sync` | Emit and synchronize n8n workflow definitions as code (n8nac). |
| `raa enterprise wasm-sandbox` | Execute third-party inspection plugins inside isolated WASM sandbox. |
| `raa enterprise simd-entropy` | Scan raw binary sections for Shannon entropy heatmaps and packing via SIMD. |
| `raa enterprise mutation-guard` | Enforce pre/post mutation verification SHA-256 guardrails. |

## Flutter Commands

**Group:** `raa flutter` | **Total Commands:** 7

| Command | Description |
|---|---|
| `raa flutter assets` | List assets declared in flutter_assets and font manifests. |
| `raa flutter symbols` | Extract Dart snapshot symbols and Flutter engine version. |
| `raa flutter patch-tls` | Patch BoringSSL TLS verification offsets for Burp/mitmproxy interception. |
| `raa flutter dump-strings` | Scrape ASCII/UTF-8 strings from libapp.so Dart snapshot. |
| `raa flutter snapshot` | Parse Dart AOT snapshot header and extract isolate strings. |
| `raa flutter ssl-bypass` | Generate targeted Frida hooks to bypass Flutter BoringSSL verification. |
| `raa flutter proxy-patch` | Patch libflutter.so ELF binary directly to reroute Dart sockets to a proxy. |

## Framework Commands

**Group:** `raa framework` | **Total Commands:** 2

| Command | Description |
|---|---|
| `raa framework capabilities` | Query supported operations and limits for frameworks. |
| `raa framework skip-inspect` | Inspect Skip Swift transpiler signatures and reconstruct Swift models. |

## Global Commands

**Group:** `raa global` | **Total Commands:** 12

| Command | Description |
|---|---|
| `raa version` | Print package and protocol versions. |
| `raa init` | Create the local workspace and database (and launch Setup UI on first run). |
| `raa doctor` | Check workspace, database, MCP SDK and engine availability. |
| `raa analyze` | Run the built-in static analysis and print the report summary. |
| `raa report` | Export a completed report to the workspace. |
| `raa manifest` | Print decoded manifest metadata from a completed analysis job. |
| `raa components` | List manifest components and their exported status. |
| `raa permissions` | List requested permissions, declared permissions and features. |
| `raa resources` | List decoded resources with type, configuration and default values. |
| `raa resource` | Show every configuration variant of one resource. |
| `raa setup-ui` | Start the RAA Setup & Tool Manager Web UI server. |
| `raa setup` | Launch interactive setup & tool manager web UI, register skip, or print MCP client config. |

## Graph Commands

**Group:** `raa graph` | **Total Commands:** 2

| Command | Description |
|---|---|
| `raa graph query` | Traverse and query the AAIR entity and relationship graph. |
| `raa graph neighborhood` | Retrieve local graph neighborhood around an AAIR entity. |

## Mcp-mesh Commands

**Group:** `raa mcp-mesh` | **Total Commands:** 7

| Command | Description |
|---|---|
| `raa mcp-mesh list` | List connected external MCP servers and tools. |
| `raa mcp-mesh connect` | Connect new external MCP server. |
| `raa mcp-mesh inspect` | Inspect tools, schemas and status of an MCP server. |
| `raa mcp-mesh test` | Test JSON-RPC handshake and latency probe. |
| `raa mcp-mesh disconnect` | Disconnect and unregister external MCP tools. |
| `raa mcp-mesh list-tools` | Query live tools/list from a connected external MCP server. |
| `raa mcp-mesh call` | Invoke a tool on a connected external MCP server through RAA. |

## Native Commands

**Group:** `raa native` | **Total Commands:** 4

| Command | Description |
|---|---|
| `raa native analyze` | Inspect ELF header, architecture, machine, bitness and endianness. |
| `raa native symbols` | Extract exported, imported, and JNI symbols from an ELF shared library. |
| `raa native jni-map` | Correlate declared Java/Kotlin native methods to native library symbols. |
| `raa native libraries` | Inventory native shared libraries (.so) across all supported ABIs. |

## Offensive Commands

**Group:** `raa offensive` | **Total Commands:** 10

| Command | Description |
|---|---|
| `raa offensive yak-run` | Execute automated penetration testing playbooks via Yaklang HackSkills. |
| `raa offensive mutate-403` | Perform deep HTTP 401/403 access control bypass mutations. |
| `raa offensive computer-use` | Operate desktop GUI reversing tools via autonomous OS computer-use. |
| `raa offensive frontier-mode` | Dynamically toggle between single-agent ReAct and multi-agent swarm paradigms. |
| `raa offensive gatekeeper-prompt` | Generate OpenMausBot human-in-the-loop impact review and diff preview. |
| `raa offensive exploit-verify` | Verify non-destructive exploit PoC chain and validate safety boundaries. |
| `raa offensive skillnet-eval` | Evaluate agent skill competencies across SkillNet benchmark gym. |
| `raa offensive skillpack` | Manage portable reverse engineering SkillPack distribution bundles. |
| `raa offensive tamper-seal` | Generate SHA-256 tamper seal and CycloneDX 1.5 SBOM manifest for audit report. |
| `raa offensive benchmark-v3` | Execute v3.0 production quality benchmark across all 322 tools. |

## Platform Commands

**Group:** `raa platform` | **Total Commands:** 7

| Command | Description |
|---|---|
| `raa platform ios-inspect` | Inspect Apple iOS .ipa container, Info.plist permissions, and Mach-O headers. |
| `raa platform macho-disassemble` | Disassemble Apple 64-bit Mach-O binary, FairPlay cryptid, and dynamic libraries. |
| `raa platform harmony-inspect` | Inspect Huawei HarmonyOS / OpenHarmony .hap package, manifests, and abilities. |
| `raa platform harmony-disassemble` | Disassemble Huawei ArkTS classes.abc bytecode into ArkUI decorators and components. |
| `raa platform proot` | Manage on-device standalone Linux PRoot container without root or PC tethering. |
| `raa platform warp-session` | Manage interactive Warp-style terminal block sessions and export audit runbooks. |
| `raa platform cross-compare` | Compare Android, iOS, and HarmonyOS apps side-by-side for permissions and parity. |

## Project Commands

**Group:** `raa project` | **Total Commands:** 3

| Command | Description |
|---|---|
| `raa project create` | Create a project. |
| `raa project list` | List projects. |
| `raa project show` | Show one project and its scopes. |

## React-native Commands

**Group:** `raa react-native` | **Total Commands:** 4

| Command | Description |
|---|---|
| `raa react-native bundle` | Inspect React Native JavaScript or Hermes bundle. |
| `raa react-native modules` | List NativeModules, TurboModules, and ReactPackages found in DEX. |
| `raa react-native hermes-extract` | Scan assets for React Native bundle and detect Hermes bytecode format. |
| `raa react-native hermes-decompile` | Decompile Hermes bytecode into JavaScript AST and scan for secrets. |

## Rebuild Commands

**Group:** `raa rebuild` | **Total Commands:** 6

| Command | Description |
|---|---|
| `raa rebuild patch` | Plan and apply controlled modifications to APK container. |
| `raa rebuild sign` | Sign an APK container with test or project credentials. |
| `raa rebuild install` | Install an APK onto a leased Android device. |
| `raa rebuild verify` | Compare behavioral divergence between baseline and patched artifacts. |
| `raa rebuild align-16kb` | Audit and patch native shared libraries for Android 15 16KB alignment. |
| `raa rebuild agents-spec` | Generate standardized repository-level AGENTS.md contract for rebuilt projects. |

## Recipe Commands

**Group:** `raa recipe` | **Total Commands:** 3

| Command | Description |
|---|---|
| `raa recipe list` | List installed recipes. |
| `raa recipe run` | Run a recipe with JSON arguments. |
| `raa recipe get-run` | Retrieve execution trace and evidence for a recipe run. |

## Security Commands

**Group:** `raa security` | **Total Commands:** 33

| Command | Description |
|---|---|
| `raa security scan` | Run static MASVS/MASTG security checks. |
| `raa security findings` | List normalized security findings. |
| `raa security secrets` | Locate embedded credentials, API keys, and tokens with redaction. |
| `raa security privacy` | Detect sensitive PII source-to-sink transmission flows. |
| `raa security sdks` | Inventory third-party SDKs and tracking libraries. |
| `raa security sbom` | Generate CycloneDX 1.5 or SPDX 2.3 Software Bill of Materials. |
| `raa security vulns` | Correlate software components with known CVE/OSV advisories. |
| `raa security yara` | Scan container with YARA rules. |
| `raa security capa` | Detect offensive capabilities with capa. |
| `raa security quark` | Calculate behavioral threat score using Quark rules. |
| `raa security ioc` | Extract and optionally export Indicators of Compromise. |
| `raa security enrich` | Query external threat intelligence (consent-gated). |
| `raa security play-protect` | Pre-flight audit against Google Play Protect and store policies. |
| `raa security dcl` | Scan for unverified Dynamic Code Loading (DCL) routines. |
| `raa security mobsf` | Evaluate MobSF static security rule catalog against manifest and code. |
| `raa security cvss` | Generate CVSS v3.1 risk scorecard and category breakdown. |
| `raa security sarif` | Export security findings in OASIS SARIF v2.1.0 format. |
| `raa security stride` | Model vulnerabilities under STRIDE mapped to MITRE ATT&CK for Mobile. |
| `raa security poc` | Generate reproducible, non-destructive Proof-of-Concept exploit commands. |
| `raa security intent-redirection` | Scan for untrusted Intent Redirection vulnerabilities. |
| `raa security pending-intent` | Scan for implicit mutable PendingIntent vulnerabilities. |
| `raa security aidl-auth` | Audit Bound Services and AIDL stubs for caller authentication flaws. |
| `raa security poc-validate` | Validate an exploit Proof-of-Concept for safety, syntax, and real exploitability. |
| `raa security masvs-audit` | Audit application security posture against the 7 OWASP MASVS v2.0 domains. |
| `raa security copilot-suggest` | Recommend next reversing tools, parameters, and Frida snippets for an analyst query. |
| `raa security bugbounty-report` | Format security finding into a submission-ready Bug Bounty report. |
| `raa security email-intel` | Check developer emails across developer platforms (GitHub, AWS, Google, Docker). |
| `raa security apkleaks-scan` | Mine Dalvik bytecode and assets for cloud credentials and API tokens. |
| `raa security taint-trace` | Trace sensitive Android privacy APIs to network and logging transmission sinks. |
| `raa security mastg-run` | Execute formal OWASP MASTG verification test procedures against MASVS controls. |
| `raa security arch-diagram` | Render interactive architecture diagram with real-time node search & taint tracing. |
| `raa security code-review` | Audit decompiled Java/Kotlin sources with hybrid AST and semantic security checks. |
| `raa security rasp-scan` | Scan Smali and native libraries for RASP, root detection, and anti-hooking checks. |

## Serve Commands

**Group:** `raa serve` | **Total Commands:** 2

| Command | Description |
|---|---|
| `raa serve mcp` | Serve the MCP surface over stdio or Streamable HTTP. |
| `raa serve api` | Serve the REST/OpenAPI surface. |

## Skill Commands

**Group:** `raa skill` | **Total Commands:** 5

| Command | Description |
|---|---|
| `raa skill list` | List available Agent Skills. |
| `raa skill show` | Print a skill's SKILL.md. |
| `raa skill install` | Copy skills into a workspace-local directory. |
| `raa skill list-evolved` | List dynamically learned recipes and patches. |
| `raa skill inspect` | View verified steps, selectors, and patch history. |

## Skills Commands

**Group:** `raa skills` | **Total Commands:** 5

| Command | Description |
|---|---|
| `raa skills list` | List available Agent Skills. |
| `raa skills show` | Print a skill's SKILL.md. |
| `raa skills install` | Copy skills into a workspace-local directory. |
| `raa skills list-evolved` | List dynamically learned recipes and patches. |
| `raa skills inspect` | View verified steps, selectors, and patch history. |

## Source Commands

**Group:** `raa source` | **Total Commands:** 12

| Command | Description |
|---|---|
| `raa source search` | Search indexed DEX classes, members and strings. |
| `raa source class` | Show one class with declared fields and methods. |
| `raa source method` | Show one method with bounded references and optional decompiled source. |
| `raa source smali` | Decode one class to Smali with Apktool. |
| `raa source refs` | Find DEX bytecode references by symbol fragment. |
| `raa source callers` | List distinct methods that call the given method. |
| `raa source callees` | List distinct methods called by the given method. |
| `raa source file` | Retrieve a decoded source, resource or archive file. |
| `raa source hierarchy` | Retrieve inheritance and interface hierarchy for a class. |
| `raa source xrefs` | Find cross-references to a symbol or entity with kind and confidence. |
| `raa source rename-symbol` | Rename an obfuscated symbol and propagate across project views. |
| `raa source wasm-decompile` | Decompile embedded WebAssembly (.wasm) modules into WebAssembly Text format (WAT). |

## Swarm Commands

**Group:** `raa swarm` | **Total Commands:** 8

| Command | Description |
|---|---|
| `raa swarm govern` | Configure multi-agent swarm hierarchy and roles. |
| `raa swarm budget` | Track token spend and enforce budget ceilings. |
| `raa swarm spawn-deerflow` | Spawn a long-horizon Deer-Flow research subagent. |
| `raa swarm sop` | Execute standardized multi-role reverse-engineering SOP. |
| `raa swarm blackboard-post` | Post hypothesis or evidence to the shared swarm blackboard. |
| `raa swarm blackboard-read` | Read findings and hypotheses from the shared swarm blackboard. |
| `raa swarm edict-gate` | Evaluate Tri-Chamber Edict review and veto gates. |
| `raa swarm loopx` | Control 24/7 long-horizon reversing goals via LoopX control plane. |

## Test Commands

**Group:** `raa test` | **Total Commands:** 2

| Command | Description |
|---|---|
| `raa test generate` | Generate automated test suites from analysis evidence. |
| `raa test run` | Execute generated test suite against authorized environment. |

## Tools Commands

**Group:** `raa tools` | **Total Commands:** 7

| Command | Description |
|---|---|
| `raa tools list` | List tools exposed by the selected profile. |
| `raa tools show` | Show a tool description and input schema. |
| `raa tools call` | Call a tool through the registry. |
| `raa tools search` | Search capability registry by semantic keywords, descriptions, and reversing goals. |
| `raa tools termux-harness` | Configure an on-device PRoot reversing and patch harness in Termux. |
| `raa tools install` | Download, verify, and auto-configure tool path. |
| `raa tools delete` | Uninstall tool and reclaim disk space. |

## Tv Commands

**Group:** `raa tv` | **Total Commands:** 3

| Command | Description |
|---|---|
| `raa tv redesign` | Redesign Android TV app into Compose for TV M3. |
| `raa tv diff` | Compare original vs redesigned TV screens with masking. |
| `raa tv bench` | Run wireless cold start and memory PSS benchmark. |

## Ui Commands

**Group:** `raa ui` | **Total Commands:** 21

| Command | Description |
|---|---|
| `raa ui screens` | List static candidate screens and observed runtime screens. |
| `raa ui screen` | Retrieve detailed screen model with regions and provenance. |
| `raa ui assets` | List UI assets (layouts, drawables, fonts, strings, themes). |
| `raa ui hierarchy` | Retrieve UIAutomator accessibility hierarchy tree. |
| `raa ui ocr` | Retrieve OCR text and bounding box regions. |
| `raa ui correlate` | Retrieve correlations linking UI components and layouts to code. |
| `raa ui coverage` | Report exploration coverage across discovered and visited screens. |
| `raa ui compare` | Compare two screens across visual IoU, OCR, and structural fidelity. |
| `raa ui to-code` | Export screen to Jetpack Compose, Flutter, React Native, or HTML. |
| `raa ui capture` | Capture running application screen screenshot and view hierarchy. |
| `raa ui webview` | Inspect embedded Android WebViews via Chrome DevTools Protocol. |
| `raa ui redesign` | Synthesize modern 8pt grid redesign with generated production code. |
| `raa ui visual-compare` | Compare original and redesigned screens pixel-by-pixel with visual diff. |
| `raa ui prune-ax-tree` | Prune and compress Android layout/accessibility hierarchy for LLM reasoning. |
| `raa ui generate-icon` | Generate complete Android 8+ Adaptive Icon suite and monochrome tint layers. |
| `raa ui generate-banner` | Generate exact 1024x500 Google Play Console compliant feature graphic banner. |
| `raa ui generate-notification-icon` | Generate Android 13+ compliant monochrome alpha-only status bar notification icon. |
| `raa ui semantic-modernize` | Execute 10-step semantic migration converting legacy XML into Material 3 Jetpack Compose. |
| `raa ui parity-diff` | Evaluate structural and semantic parity score between legacy XML and Compose. |
| `raa ui visual-navigate` | Resolve visual element query to normalized bounding box and tap coordinates. |
| `raa ui notification-audit` | Audit notification bar icon compliance, contrast ratios, and manifest metadata. |

## Unity Commands

**Group:** `raa unity` | **Total Commands:** 3

| Command | Description |
|---|---|
| `raa unity assets` | List Unity asset files, streaming assets, and data files. |
| `raa unity metadata` | Extract IL2CPP metadata summary from global-metadata.dat. |
| `raa unity dump-metadata` | Parse Il2Cpp global-metadata.dat and dump C# class prototypes. |

## Unpack Commands

**Group:** `raa unpack` | **Total Commands:** 5

| Command | Description |
|---|---|
| `raa unpack detect` | Detect packers, protectors, obfuscators, and anti-analysis mechanisms. |
| `raa unpack extract` | Statically carve and extract embedded DEX and payload containers. |
| `raa unpack verify` | Verify structural integrity, checksums, and completeness of dumped DEX. |
| `raa unpack deobfuscate` | Apply Dalvik deobfuscation transformations with strict provenance tracking. |
| `raa unpack retrace` | Parse ProGuard/R8 mapping files and translate symbols or stack traces. |

