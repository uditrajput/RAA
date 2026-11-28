# GitHub Actions Reference & Workflow Catalog

## Workflow Catalog

### 1. `ci.yml` – Main CI Pipeline
- **Job `lint-and-format`:** Runs Ruff format check and linter on `src` and `tests`.
- **Job `build`:** Uses `python -m build` to compile the wheel and sdist packages, verifies package validity via `twine check`, and uploads the build artifacts with a 7-day retention period.
- **Job `unit-tests`:** Runs unit tests on Python 3.11 and 3.12, exporting JUnit XML reports.
- **Job `integration-tests`:** Runs full integration test suites covering end-to-end multi-phase reverse engineering flows.

### 2. `mcp-tests.yml` – MCP Server & Tool Validation
- **Job `mcp-tests`:** Validates MCP HTTP/stdio server startup, tool registration across all 377 implemented tools, input schema correctness, profile constraints (`minimal`, `core`, `dynamic`, `ui`, `api`, `admin`, `swarm`, `full`), error envelopes, and agent skill registrations.

### 3. `android-engines.yml` – Android Engine Integration
- **Job `android-engine-tests`:** Configures Java 17 Temurin, probes native binary availability (JADX, Apktool, Ghidra, Rizin), executes engine discovery, tests engine adapters, and validates DEX/manifest/resource parsing using synthetic test fixtures.

### 4. `ui-tests.yml` – UI Reconstruction Validation
- **Job `ui-tests`:** Tests UI hierarchy parsing, layout extraction, XML semantic modernizers, and visual comparison tools without requiring external paid cloud APIs.

### 5. `security.yml` – Security & Vulnerability Scanning
- **Job `secret-detection`:** Scans commit history for accidental secrets using Gitleaks.
- **Job `dependency-audit`:** Scans Python dependencies for known CVEs using `pip-audit`.
- **Job `security-tests`:** Executes Semgrep static application security testing rules.

### 6. `codeql.yml` – CodeQL Semantic Analysis
- **Job `codeql-analysis`:** Runs GitHub CodeQL engine for Python with the `security-and-quality` query suite. Results are uploaded to GitHub Security tab.

### 7. `documentation.yml` – Documentation & Agent Skill Validation
- **Job `documentation-check`:** Verifies Markdown formatting, UTF-8 file integrity, and validates all 23 Agent Skills YAML frontmatters and required files.

### 8. `release.yml` – Production Release Pipeline
- **Job `pre-release-check`:** Verifies full production test suite passes before release.
- **Job `build-and-release`:** Builds distributable wheels, calculates SHA256 checksums, executes `raa admin sbom` to generate CycloneDX and SPDX SBOMs, and publishes a GitHub Release tagged with immutable assets.
