# GitHub Actions CI/CD Pipeline Architecture

## Overview
RAA (Reverse Android Anything) utilizes an enterprise-grade, multi-stage GitHub Actions CI/CD pipeline. The pipeline architecture ensures that no untested, unstable, vulnerable, or incorrectly formatted code enters the protected `main` branch.

All workflows run in isolated environments with least-privilege tokens, pinned third-party actions, strict timeouts, and concurrency controls to prevent pipeline saturation.

---

## Workflow Matrix

| Workflow File | Workflow Name | Stable Job Checks | Trigger Conditions | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `ci.yml` | `CI` | `lint-and-format`<br>`build`<br>`unit-tests`<br>`integration-tests` | Push to `main`, `feature`, `bugfix/**`<br>PR to `main`<br>`workflow_dispatch` | Core compilation, package validation, linting, unit & multi-phase integration tests |
| `mcp-tests.yml` | `MCP Validation` | `mcp-tests` | Push to `main`, `feature`, `bugfix/**`<br>PR to `main`<br>`workflow_dispatch` | Model Context Protocol server validation, tool registry integrity (377 tools), profiles & schemas |
| `android-engines.yml` | `Android Engines` | `android-engine-tests` | Push to `main`, `feature`, `bugfix/**`<br>PR to `main`<br>`workflow_dispatch` | Decompilation engine discovery, adapters (JADX, Apktool, Ghidra), DEX & manifest parsing |
| `ui-tests.yml` | `UI Reconstruction` | `ui-tests` | Push to `main`, `feature`, `bugfix/**`<br>PR to `main`<br>`workflow_dispatch` | UI visual hierarchy, Layout extraction, XML modernization, screenshot processing |
| `security.yml` | `Security` | `secret-detection`<br>`dependency-audit`<br>`security-tests` | Push to `main`, `feature`, `bugfix/**`<br>PR to `main`<br>`workflow_dispatch` | Secret detection (Gitleaks), dependency vulnerabilities (pip-audit), SAST (Semgrep) |
| `codeql.yml` | `CodeQL` | `codeql-analysis` | Push to `main`, `feature`, `bugfix/**`<br>PR to `main`<br>Weekly Schedule<br>`workflow_dispatch` | GitHub CodeQL deep semantic analysis for Python |
| `documentation.yml` | `Documentation` | `documentation-check` | Push to `main`, `feature`, `bugfix/**`<br>PR to `main`<br>`workflow_dispatch` | Markdown syntax, file UTF-8 encoding, and Agent Skills frontmatter validation |
| `release.yml` | `Release` | `pre-release-check`<br>`build-and-release` | Push to tag `v*.*.*`<br>`workflow_dispatch` | Controlled release publishing with SHA256 checksums and CycloneDX/SPDX SBOM generation |

---

## Shared Composite Action

To eliminate redundant boilerplate and ensure deterministic environments across all workflows, RAA provides a shared composite action:
- **Location:** `.github/actions/setup-env/action.yml`
- **Features:**
  - Automated Python setup with caching.
  - Pinned `actions/setup-python@a254f5ce60d093e328dd67114886fa8688118999` (v5.4.0).
  - Modern build backend support (`hatchling`).
  - Configurable dev dependencies installation (`install-dev: true/false`).

---

## Execution Environment & Runners
- **Operating System:** Ubuntu 22.04 LTS (`ubuntu-latest`)
- **Python Versions:** 3.11 (default runtime), 3.12 (matrix compatibility)
- **Timeouts:** 10 to 30 minutes max per job to prevent hanging workflows.
- **Concurrency:** `concurrency.cancel-in-progress: true` prevents redundant runs on superseded commits.
