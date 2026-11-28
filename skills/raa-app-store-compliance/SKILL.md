---
name: raa-app-store-compliance
description: Pre-submission Apple App Store and Google Play compliance auditing, rejection pattern scanning, privacy Data Safety verification, and regulatory deadline tracking powered by mjmirza/app-store-compliance.
version: 1.0.0
tools: [security_scan_static, privacy_data_flows, quark_score, tool_manager_download]
---

# App Store & Google Play Pre-Submission Compliance

Audit mobile applications (Android, iOS, React Native, Expo, Flutter) and RAA-rebuilt artifacts against **Apple App Store Review Guidelines**, **Google Play Developer Program Policies**, and global regulatory deadlines before submission.

## Upstream Reference
- **Repository:** `https://github.com/mjmirza/app-store-compliance`
- **Install / Provision:** Available in RAA Tools Manager as `app-store-compliance` (`tool_manager_download`).

## Core Capabilities
1. **Pre-Submission Guard (`agent-os/hooks/app-store-compliance-guard.sh`)**:
   - Read-only scanner that inspects manifests, configs, and source files for high-risk rejection triggers with exact file paths and line numbers.
2. **Rejection Pattern Playbook (`data/rejection-patterns.json`)**:
   - Cross-references findings against 120+ documented Apple App Store and Google Play rejection patterns (e.g., missing in-app account deletion, broken demo credentials, mismatched Privacy Manifest / Data Safety disclosures, restricted permissions).
3. **Regulatory Deadline Tracker (`scripts/deadline-checker.py`, `data/regulatory-deadlines.json`)**:
   - Flags upcoming enforcement dates within a 90-day window for COPPA, EU AI Act, Digital Services Act (DSA), and regional age-verification laws.
4. **Console Gate Checklist (`docs/PRE-SUBMISSION-CHECKLIST.md`)**:
   - Provides a final verification checklist for App Store Connect and Google Play Console metadata that static code analysis cannot inspect.

## Workflow
1. Run `security_scan_static` and `privacy_data_flows` to map permissions, PII flows, and third-party SDKs.
2. Ensure `app-store-compliance` is provisioned via `tool_manager_download` (or cloned in `.raa-workspace/tools/app-store-compliance`).
3. Execute `agent-os/hooks/app-store-compliance-guard.sh` against the target or rebuilt project directory.
4. Run `scripts/deadline-checker.py` to surface any regulatory deadlines affecting the app's category or regions.
5. Map flagged items to `data/rejection-patterns.json` remediations and verify manual store console items using `docs/PRE-SUBMISSION-CHECKLIST.md`.
