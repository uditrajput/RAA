# RAA Documentation Hub

<p align="center">
  <img src="../images/raa.png" width="140" alt="RAA Logo">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Current_Release-v4.0.0_Production-success?style=flat-square" alt="Current Release: v4.0.0 Production">
  <img src="https://img.shields.io/badge/Total_Tools-379_Implemented-blue?style=flat-square" alt="Total Tools: 379 Implemented">
  <img src="https://img.shields.io/badge/CLI_Commands-345_Commands-orange?style=flat-square" alt="CLI Commands: 345 Commands">
  <img src="https://img.shields.io/badge/Tests-740+_Passing-brightgreen?style=flat-square" alt="Tests: 740+ Passing">
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Protocol-2026--07--28-informational?style=flat-square" alt="Protocol: 2026-07-28">
  <img src="https://img.shields.io/badge/License-MIT-4c1?style=flat-square" alt="License: MIT">
</p>

Welcome to the **RAA (Reverse Android Anything)** official documentation index. RAA is an agent-native application intelligence, decompilation, UI reconstruction, and offensive security platform covering Android (APK/AAB), Apple iOS (IPA/Mach-O), Huawei HarmonyOS (HAP/ArkTS), and on-device Linux containers (PRoot/Termux).

---

## Documentation Index

| Icon | Document | Focus & Highlights | Intended Audience |
| :---: | :--- | :--- | :--- |
| 💻 | **[`CLI_REFERENCE.md`](CLI_REFERENCE.md)** | **Exhaustive reference for all 345 CLI commands** across all 38 subcommand groups with parameter breakdowns. | Terminal Analysts, SREs, Automation Engineers |
| 🛠️ | **[`TOOLS_INTEGRATION_AND_TEST_SCENARIOS.md`](TOOLS_INTEGRATION_AND_TEST_SCENARIOS.md)** | **Complete matrix of all 379 tools**, requirements scenarios, profiles, and automated test scenarios. | Security Auditors, System Engineers, QA Engineers |
| 🏛️ | **[`ARCHITECTURE.md`](ARCHITECTURE.md)** | Subsystem topology, single-core runtime invariants, component interfaces, and multi-platform engine adapters. | Architects, Core Contributors, Integrators |
| 🎨 | **[`DESIGN.md`](DESIGN.md)** | Evidence-first truth hierarchy, domain entities, 8pt UI design system, and Model Context Protocol (MCP) contracts. | System Engineers, UI Designers, Agent Authors |
| 🤖 | **[`AGENTS_AND_SKILLS.md`](AGENTS_AND_SKILLS.md)** | Multi-agent swarm orchestration, specialized subagent fleet (18 core specialized agents), and 23 discoverable Agent Skills. | AI Researchers, Prompt Engineers, Swarm Operators |
| 🚀 | **[`ROADMAP.md`](ROADMAP.md)** | Strategic platform roadmap and capability milestones through Phase 21 (v4.0.0 Production). | Developers, Architects, Contributors |
| 🏢 | **[`DEPLOYMENT.md`](DEPLOYMENT.md)** | Enterprise production deployment, Docker sandboxing, multi-tenancy quotas, air-gapped installation, and disaster recovery. | DevOps, SREs, Enterprise System Administrators |
| 🔒 | **[`SECURITY.md`](SECURITY.md)** | STRIDE threat model, fail-closed policy engine, SHA-256 hash-chained audit trails, and OWASP MASTG compliance. | Security Auditors, Compliance Officers, Penetration Testers |
| 📦 | **[`RELEASES.md`](../RELEASES.md)** | Comprehensive release history and changelog spanning all milestones from Phase 1 to Phase 21. | All Users, Maintainers, Release Managers |
| 📋 | **[`RELEASE_v4.0.0.md`](../releases/RELEASE_v4.0.0.md)** | Official v4.0.0 production release notes and architectural overview. | All Users, Security Teams, Architects |

---

## Quick Navigation by Role

```mermaid
flowchart TD
    classDef start fill:#1A237E,stroke:#3F51B5,stroke-width:2px,color:#FFFFFF,font-weight:bold;
    classDef core fill:#004D40,stroke:#00897B,stroke-width:2px,color:#FFFFFF;
    classDef ref fill:#01579B,stroke:#039BE5,stroke-width:2px,color:#FFFFFF;
    classDef sec fill:#B71C1C,stroke:#E53935,stroke-width:2px,color:#FFFFFF;
    classDef ops fill:#4A148C,stroke:#8E24AA,stroke-width:2px,color:#FFFFFF;

    User["👤 Developer / Security Analyst"]:::start --> Path{"What would you like to explore?"}
    
    Path -->|Core System Architecture| Arch["🏛️ ARCHITECTURE.md"]:::core
    Path -->|Domain Entities & Design| Design["🎨 DESIGN.md"]:::core
    Path -->|Multi-Agent Swarms & Skills| Agents["🤖 AGENTS_AND_SKILLS.md"]:::core
    Path -->|Strategic Roadmap v1-v3| Road["🚀 ROADMAP.md"]:::core
    
    Path -->|Complete CLI Reference (345 Cmds)| CLI["💻 CLI_REFERENCE.md"]:::ref
    Path -->|Tool Matrix (379 Tools)| Matrix["🛠️ TOOLS_INTEGRATION.md"]:::ref
    
    Path -->|Threat Model & Audit Logs| Sec["🔒 SECURITY.md"]:::sec
    Path -->|Enterprise Deployment & Sandboxing| Deploy["🏢 DEPLOYMENT.md"]:::sec
    
    Path -->|Setup & Engine Config| Setup["🚀 SETUP_GUIDE.md"]:::ops
    Path -->|CI/CD, Security & DevOps| DevOps["⚙️ devops/CI_CD_ARCHITECTURE.md"]:::ops
```

---

## Key Platform Specifications

- **Active Version:** `v4.0.0 Production` (Phase 21 Complete)
- **Implemented Capability Tools:** `379` tools registered and tested
- **Passing Test Suite:** `740+` automated unit, integration, and E2E tests
- **MCP Protocol Baseline:** `2026-07-28`
- **Supported Application Formats:**
  - **Android:** `.apk`, `.aab`, `.apks`, `.xapk` (Dalvik `.dex`, AXML, ARSC, ELF `.so`)
  - **Apple iOS:** `.ipa` (Mach-O 64-bit, Objective-C, Swift metadata)
  - **Huawei HarmonyOS:** `.hap` (ArkTS Panda `.abc` bytecode, module.json)
  - **On-Device Linux:** PRoot/Termux standalone rootless container engine

---

## 🛠️ DevOps, CI/CD & Operations Documentation

| Icon | Document | Focus & Highlights | Intended Audience |
| :---: | :--- | :--- | :--- |
| 🚀 | **[`SETUP_GUIDE.md`](SETUP_GUIDE.md)** | Step-by-step setup guide for MCP clients (Cursor, Claude, VS Code) and analysis engines. | All Users, DevOps |
| ⚙️ | **[`devops/CI_CD_ARCHITECTURE.md`](devops/CI_CD_ARCHITECTURE.md)** | High-throughput multi-job GitHub Actions matrix, caching, and test automation. | DevOps, Release Engineers |
| 🛡️ | **[`devops/SECURITY_SCANNING.md`](devops/SECURITY_SCANNING.md)** | CodeQL, Semgrep CI/OWASP, and CycloneDX SBOM scanning architecture. | Security Engineers, DevSecOps |
| 🐙 | **[`devops/GITHUB_ACTIONS.md`](devops/GITHUB_ACTIONS.md)** | Exhaustive workflow inventory, triggers, secrets, and environment setup. | CI/CD Maintainers |
| 🌿 | **[`devops/BRANCH_PROTECTION.md`](devops/BRANCH_PROTECTION.md)** | Rulesets, mandatory status checks, and merge gate governance. | Tech Leads, Maintainers |
| 📦 | **[`devops/RELEASE_PROCESS.md`](devops/RELEASE_PROCESS.md)** | Release automation, artifact bundling, PyPI publishing, and GitHub Releases. | Release Managers |
| 🤝 | **[`devops/CONTRIBUTION_WORKFLOW.md`](devops/CONTRIBUTION_WORKFLOW.md)** | Developer environment setup, coding standards, pre-commit, and review protocol. | Contributors |
